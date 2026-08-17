"""
QI Hive — Claude Code usage stats.

Parses ~/.claude/projects/**/*.jsonl locally to produce token + cost
aggregates. No API calls, no keys. Shapes:

    today()         -> {tokens, cost_usd, sessions, assistant_turns}
    daily(n=30)     -> [{date, tokens, cost_usd, sessions, turns}, ...]
    by_project(n)   -> [{project, tokens, cost_usd, turns}, ...]
    by_model(n)     -> [{model, tokens, cost_usd, turns}, ...]

Pricing is per 1M tokens. Cache-read billed at 10% of input, cache-write
(ephemeral_5m) at 125%, cache-write (ephemeral_1h) at 200%. Sourced from
Anthropic public pricing (Jan 2026). Unknown models are bucketed as family
"other" (billed at sonnet rate, surfaced separately in the model breakdown)
rather than silently merged into the sonnet family.

Results are cached in-memory for 30s to keep the dashboard cheap.
"""
from __future__ import annotations
import json
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ── Pricing ($ per 1M tokens) ────────────────────────────────────────────
# Input / Output
MODEL_PRICING = {
    "opus":   (15.00, 75.00),
    "sonnet": ( 3.00, 15.00),
    "haiku":  ( 0.80,  4.00),
    # Fable 5: frontier reasoning tier — mirrored from opus until Anthropic
    # publishes official Fable pricing. Update when pricing is confirmed.
    "fable":  (15.00, 75.00),
    # Catch-all: priced at sonnet so unknowns don't go free, but they are
    # tracked under their own "other" family to make the gap visible.
    "other":  ( 3.00, 15.00),
}
CACHE_READ_MULT  = 0.10   # read-back of cached prefix
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00

# ── What-if optimization heuristics ─────────────────────────────────────
# Fraction of each model family's work that could plausibly be handled by
# free local LLMs (Ollama: gemma4:31b, gpt-oss-20b, qwen3:8b, etc.) without
# meaningful quality loss. Intentionally conservative.
LOCAL_OFFLOAD_BY_FAMILY = {
    "haiku":  1.00,   # trivial ops — gemma4:9.6b or qwen3:8b handles these fine
    "sonnet": 0.40,   # ~40% of sonnet work is routine enough for gpt-oss-20b / gemma4:31b
    "opus":   0.00,   # deep reasoning / architecture — keep on Opus
    "fable":  0.00,   # frontier reasoning — keep on Fable
    "other":  0.40,   # unknown models treated conservatively like sonnet
}

# Anthropic Batch API: 50% discount for tasks that can tolerate async execution
# within a 24h window. Batching only makes sense for work that doesn't need
# real-time response — here we model "could have been batched" as everything
# outside the defined live-work window.
BATCH_DISCOUNT = 0.50
BATCH_WINDOW_START_HOUR = 0   # midnight
BATCH_WINDOW_END_HOUR   = 6   # 06:00

import os as _os
import os.path as _osp

def _find_projects_dir() -> Path:
    """Locate ~/.claude/projects regardless of the user running the service.
    LocalSystem's Path.home() is C:\\Windows\\system32\\config\\systemprofile,
    which has no .claude folder. Try known user paths."""
    candidates = []
    env_home = _os.environ.get("USERPROFILE") or str(Path.home())
    candidates.append(Path(env_home) / ".claude" / "projects")
    users_dir = Path(r"C:\Users")
    if users_dir.exists():
        for user in users_dir.iterdir():
            cand = user / ".claude" / "projects"
            if cand.is_dir():
                candidates.append(cand)
    # return first existing with jsonl files, else first candidate
    for c in candidates:
        if c.is_dir() and any(c.rglob("*.jsonl")):
            return c
    return candidates[0] if candidates else Path.home() / ".claude" / "projects"

PROJECTS_DIR = _find_projects_dir()
_CACHE: dict = {"stamp": 0.0, "events": []}
_TTL = 30.0


def _model_family(name: str | None) -> str:
    if not name:
        return "other"
    n = name.lower()
    if "opus" in n:   return "opus"
    if "fable" in n:  return "fable"
    if "sonnet" in n: return "sonnet"
    if "haiku" in n:  return "haiku"
    # Unknown model: explicit "other" so it doesn't silently masquerade as sonnet
    # and the dashboard can surface it in the model breakdown.
    return "other"


def _cost(usage: dict, model: str) -> float:
    fam = _model_family(model)
    in_rate, out_rate = MODEL_PRICING[fam]
    inp = usage.get("input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    cache_read = usage.get("cache_read_input_tokens", 0) or 0
    cache_create = usage.get("cache_creation", {}) or {}
    cw_5m = cache_create.get("ephemeral_5m_input_tokens", 0) or 0
    cw_1h = cache_create.get("ephemeral_1h_input_tokens", 0) or 0

    return (
        inp        * in_rate         / 1_000_000
        + out      * out_rate        / 1_000_000
        + cache_read * in_rate * CACHE_READ_MULT     / 1_000_000
        + cw_5m    * in_rate * CACHE_WRITE_5M_MULT   / 1_000_000
        + cw_1h    * in_rate * CACHE_WRITE_1H_MULT   / 1_000_000
    )


def _tokens(usage: dict) -> int:
    """'Fresh' tokens — what was actually generated or written into cache this
    turn. Excludes cache_read_input_tokens because those are re-reads of the
    same cached prefix and inflate the headline by 5–20× without representing
    new consumption. Use _cache_reads() to surface the re-read volume separately."""
    return (
        (usage.get("input_tokens", 0) or 0)
        + (usage.get("output_tokens", 0) or 0)
        + (usage.get("cache_creation_input_tokens", 0) or 0)
    )


def _cache_reads(usage: dict) -> int:
    """Tokens read back from the prompt cache (billed at 10% of input rate).
    Tracked separately from _tokens so the headline 'Tokens Today' reflects
    fresh consumption, not the same prefix being re-read N times."""
    return usage.get("cache_read_input_tokens", 0) or 0


_PROJECT_RE = re.compile(r"[A-Z]-{2,}([^\\/-]+)")

_REGISTRY_PATH = r"C:\QIH\ecosystem\qi_registry.json"

# Aliases for paths/folder-names not in the registry or that appear in
# worktree folder names (e.g. C--CLAUDE-worktree-abc → claude_manager).
_FOLDER_ALIASES: dict[str, str] = {
    "CLAUDE":         "claude_manager",
    "QIH":            "qi_hive",
    "QI":             "maia",
    "NAYA":           "naya",
    "NEXUS":          "nexus",
    "OC":             "openclaw",
    "OPENCLAW":       "openclaw",
    "EASYFLOW":       "easyflow",
    "FILEHQ":         "filehq",
    "MQ":             "mq",
    "UNIVERSAL":      "universal",
    "AUTOPDF":        "autopdf",
    "COGNIBASE":      "cognibase",
    "MAPSNAP":        "mapsnap",
    "M2V":            "m2v",
    "PERSONALSONG":   "personalsong",
    "CYPHERMINER":    "cypherminer",
    "LOTTERYWIZ":     "lotterywiz",
    "LOTTERY WIZ":    "lotterywiz",
    "TUBESCOUT":      "tubescout",
    "FIDELITYANALYZER": "fidelityanalyzer",
    "AVATARSTUDIO":   "avatarstudio",
}


def _load_registry_path_map() -> list[tuple[str, str]]:
    """Build a normalized (upper-case, no trailing slash) path → project-id list,
    sorted longest-first so the most-specific prefix wins in matching.

    When two projects share the same path (e.g. qi_hive and universal both live
    at C:\\QIH), qi_hive wins because it is the actively developed project;
    universal is the legacy label for the same directory before migration.
    Similarly, qi_brain wins over qi_hive for C:\\QIH\\engine\\brain because
    it has a longer (more-specific) path.
    """
    # Projects that should win tie-breaks when multiple entries share a path.
    # Higher value = higher priority (wins over lower-value entries at same path).
    _TIE_PRIORITY = {
        "qi_brain": 10,   # sub-path of qi_hive — longer path anyway, so this rarely fires
        "qi_hive":  5,    # wins over "universal" which shares C:\QIH
    }
    try:
        with open(_REGISTRY_PATH, encoding="utf-8") as f:
            reg = json.load(f)
        rows: list[tuple[str, str]] = []
        for proj in reg.get("projects", []):
            pid = proj.get("id", "").strip()
            if not pid:
                continue
            for key in ("path", "original_path", "path_standard"):
                raw = proj.get(key)
                if raw and isinstance(raw, str):
                    norm = raw.replace("/", "\\").rstrip("\\").upper()
                    rows.append((norm, pid))
        # Sort: longest path first (most-specific wins), then higher tie-priority
        # first for same-length paths.
        rows.sort(
            key=lambda t: (len(t[0]), _TIE_PRIORITY.get(t[1], 0)),
            reverse=True,
        )
        return rows
    except Exception:
        return []


_REG_PATH_MAP: list[tuple[str, str]] = _load_registry_path_map()


def _project_from_cwd(cwd: str | None, folder_name: str) -> str:
    """Best-effort canonical project id (lowercase, matches qi_registry.json id field).

    Priority:
      1. Longest-prefix match of cwd against registry project paths.
      2. Alias map check on the worktree folder name (handles C--CLAUDE-... forms
         and bare single-segment folder names).
      3. 'unknown'

    Falls back to the old heuristic list if the registry failed to load, so the
    dashboard keeps working even if qi_registry.json is temporarily unreadable.
    """
    if cwd:
        c = cwd.replace("/", "\\").rstrip("\\").upper()
        # Registry-driven: longest-matching prefix wins
        if _REG_PATH_MAP:
            for reg_path, pid in _REG_PATH_MAP:
                if c == reg_path or c.startswith(reg_path + "\\"):
                    return pid
        else:
            # Fallback to hardcoded list when registry is unreadable
            if   c.startswith("C:\\QIH\\ENGINE\\BRAIN"): return "qi_brain"
            elif c.startswith("C:\\QIH"):                return "qi_hive"
            elif c.startswith("C:\\APPS\\QI\\") or c == "C:\\APPS\\QI": return "maia"
            elif c.startswith("C:\\APPS\\NAYA"):               return "naya"
            elif c.startswith("C:\\APPS\\NEXUS"):              return "nexus"
            elif c.startswith("C:\\APPS\\OC") or c.startswith("C:\\OPENCLAW"): return "openclaw"
            elif c.startswith("C:\\EASYFLOW"):           return "easyflow"
            elif c.startswith("C:\\FILEHQ"):             return "filehq"
            elif c.startswith("C:\\APPS\\CLAUDE"):             return "claude_manager"
            elif c.startswith("C:\\APPS\\MQ"):                 return "mq"
            elif c.startswith("C:\\UNIVERSAL"):          return "universal"
            elif "LINE BOTS" in c or "\\MAIA" in c:     return "maia"

    # Alias map against the worktree folder name.
    # Handles forms like:
    #   "C--CLAUDE-worktree-abc123"  → segment after C-- → "CLAUDE"
    #   "C--CLAUDE"                  → segment after C-- → "CLAUDE"
    #   "C--1-AI--APPS--AVATARSTUDIO-xyz" → walk segments looking for alias hit
    fn_upper = folder_name.upper()
    # Strip leading drive+separator segment (C-- or C--USERS-- etc.)
    parts = [p for p in fn_upper.replace("--", "\x00").split("\x00") if p]
    # Try progressively from the back (deepest folder) to the front
    for part in reversed(parts):
        # Strip trailing worktree hash (alphanumeric suffix after last "-")
        stem = re.sub(r"-[0-9A-F]{4,}$", "", part, flags=re.IGNORECASE)
        if stem in _FOLDER_ALIASES:
            return _FOLDER_ALIASES[stem]
        if part in _FOLDER_ALIASES:
            return _FOLDER_ALIASES[part]

    return "unknown"


def _iter_events(force: bool = False):
    """Stream usage-bearing events across all jsonl files, cached 30s."""
    now = time.time()
    if not force and now - _CACHE["stamp"] < _TTL and _CACHE["events"]:
        return _CACHE["events"]

    events: list[dict] = []
    if not PROJECTS_DIR.exists():
        _CACHE.update(stamp=now, events=events)
        return events

    for jsonl in PROJECTS_DIR.rglob("*.jsonl"):
        folder = jsonl.parent.name
        try:
            with jsonl.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    msg = d.get("message") or {}
                    usage = msg.get("usage") or d.get("usage")
                    if not usage or not isinstance(usage, dict):
                        continue
                    model = msg.get("model") or d.get("model")
                    ts_raw = d.get("timestamp")
                    if not ts_raw:
                        continue
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    except Exception:
                        continue
                    events.append({
                        "ts":          ts,
                        "model":       model or "unknown",
                        "family":      _model_family(model),
                        "project":     _project_from_cwd(d.get("cwd"), folder),
                        "session":     d.get("sessionId") or folder,
                        "tokens":      _tokens(usage),
                        "cache_reads": _cache_reads(usage),
                        "cost":        _cost(usage, model),
                    })
        except (PermissionError, OSError):
            continue

    events.sort(key=lambda e: e["ts"])
    _CACHE.update(stamp=now, events=events)
    return events


def today() -> dict:
    evs = _iter_events()
    today_local = date.today()
    sessions = set()
    turns = 0
    tokens = 0
    cache_reads = 0
    cost = 0.0
    for e in evs:
        d_local = e["ts"].astimezone().date()
        if d_local == today_local:
            sessions.add(e["session"])
            turns += 1
            tokens += e["tokens"]
            cache_reads += e.get("cache_reads", 0)
            cost += e["cost"]
    return {
        "tokens":           tokens,
        "cache_reads":      cache_reads,
        "cost_usd":         round(cost, 2),
        "sessions":         len(sessions),
        "assistant_turns":  turns,
        "date":             today_local.isoformat(),
    }


def daily(days: int = 30) -> list[dict]:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    buckets: dict[date, dict] = defaultdict(
        lambda: {"tokens": 0, "cache_reads": 0, "cost": 0.0, "turns": 0, "sessions": set()})
    for e in evs:
        d = e["ts"].astimezone().date()
        if d < cutoff:
            continue
        b = buckets[d]
        b["tokens"]  += e["tokens"]
        b["cache_reads"] += e.get("cache_reads", 0)
        b["cost"]    += e["cost"]
        b["turns"]   += 1
        b["sessions"].add(e["session"])
    # Separately compute per-day what-if costs (local / batch / combined)
    whatif: dict[date, dict] = defaultdict(lambda: {"local": 0.0, "batch": 0.0, "combined": 0.0})
    for e in evs:
        d = e["ts"].astimezone().date()
        if d < cutoff:
            continue
        fam = e["family"]
        frac = LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
        hour_local = e["ts"].astimezone().hour
        in_night = BATCH_WINDOW_START_HOUR <= hour_local < BATCH_WINDOW_END_HOUR
        c = e["cost"]
        w = whatif[d]
        w["local"]    += c * (1 - frac)
        w["batch"]    += c * ((1 - BATCH_DISCOUNT) if not in_night else 1.0)
        remaining = c * (1 - frac)
        if not in_night:
            remaining *= (1 - BATCH_DISCOUNT)
        w["combined"] += remaining

    out = []
    for i in range(days):
        d = cutoff + timedelta(days=i)
        b = buckets.get(d, {"tokens": 0, "cache_reads": 0, "cost": 0.0, "turns": 0, "sessions": set()})
        w = whatif.get(d, {"local": 0.0, "batch": 0.0, "combined": 0.0})
        out.append({
            "date":              d.isoformat(),
            "tokens":            b["tokens"],
            # Cache re-reads are billed at 10% of input rate and excluded from
            # `tokens` (see _tokens). Surfaced per-day so the ledger can store
            # them alongside fresh consumption instead of recording zero.
            "cache_reads":       b["cache_reads"],
            "cost_usd":          round(b["cost"], 2),
            "local_cost_usd":    round(w["local"], 2),
            "batch_cost_usd":    round(w["batch"], 2),
            "combined_cost_usd": round(w["combined"], 2),
            "turns":             b["turns"],
            "sessions":          len(b["sessions"]),
        })
    return out


def savings_by_project(days: int = 30) -> list[dict]:
    """Per-project what-if breakdown (same shape idea as savings_by_model)."""
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    agg: dict[str, dict] = defaultdict(lambda: {
        "tokens": 0, "turns": 0,
        "actual": 0.0, "local_opt": 0.0, "batch_opt": 0.0, "combined": 0.0,
    })
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        fam = e["family"]
        frac = LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
        hour_local = e["ts"].astimezone().hour
        in_night = BATCH_WINDOW_START_HOUR <= hour_local < BATCH_WINDOW_END_HOUR
        c = e["cost"]
        a = agg[e["project"]]
        a["tokens"] += e["tokens"]
        a["turns"]  += 1
        a["actual"] += c
        a["local_opt"] += c * (1 - frac)
        a["batch_opt"] += c * ((1 - BATCH_DISCOUNT) if not in_night else 1.0)
        remaining = c * (1 - frac)
        if not in_night:
            remaining *= (1 - BATCH_DISCOUNT)
        a["combined"] += remaining

    rows = []
    for proj, a in agg.items():
        actual = a["actual"]
        rows.append({
            "project":       proj,
            "tokens":        a["tokens"],
            "turns":         a["turns"],
            "actual_usd":    round(actual, 2),
            "local_opt_usd": round(a["local_opt"], 2),
            "batch_opt_usd": round(a["batch_opt"], 2),
            "combined_usd":  round(a["combined"], 2),
            "total_savings_usd": round(actual - a["combined"], 2),
            "total_savings_pct": round(((actual - a["combined"]) / actual) * 100, 1) if actual > 0 else 0.0,
        })
    rows.sort(key=lambda r: r["actual_usd"], reverse=True)
    return rows


def by_project(days: int = 30) -> list[dict]:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    agg: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "turns": 0})
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        a = agg[e["project"]]
        a["tokens"] += e["tokens"]
        a["cost"]   += e["cost"]
        a["turns"]  += 1
    rows = [{"project": k, "tokens": v["tokens"], "cost_usd": round(v["cost"], 2), "turns": v["turns"]}
            for k, v in agg.items()]
    rows.sort(key=lambda r: r["cost_usd"], reverse=True)
    return rows


def by_model(days: int = 30) -> list[dict]:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    agg: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "turns": 0})
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        a = agg[e["model"]]
        a["tokens"] += e["tokens"]
        a["cost"]   += e["cost"]
        a["turns"]  += 1
    rows = [{"model": k, "tokens": v["tokens"], "cost_usd": round(v["cost"], 2), "turns": v["turns"]}
            for k, v in agg.items()]
    rows.sort(key=lambda r: r["cost_usd"], reverse=True)
    return rows


def savings_today() -> dict:
    """Same shape as savings() but scoped to today only (local date)."""
    evs = _iter_events()
    today_local = date.today()
    actual_cost = local_savings = batchable_cost = combined_cost = 0.0
    actual_tokens = offloaded_tokens = batchable_turns = 0
    offloaded_turns = 0.0
    for e in evs:
        if e["ts"].astimezone().date() != today_local:
            continue
        fam = e["family"]
        c = e["cost"]; tok = e["tokens"]
        actual_cost += c; actual_tokens += tok
        frac = LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
        local_savings += c * frac
        offloaded_tokens += int(tok * frac)
        offloaded_turns += frac
        hour_local = e["ts"].astimezone().hour
        in_night = BATCH_WINDOW_START_HOUR <= hour_local < BATCH_WINDOW_END_HOUR
        if not in_night:
            batchable_cost += c
            batchable_turns += 1
        remaining = c * (1 - frac)
        if not in_night:
            remaining *= (1 - BATCH_DISCOUNT)
        combined_cost += remaining

    batch_savings = batchable_cost * BATCH_DISCOUNT
    combined_savings = actual_cost - combined_cost
    def pct(p, w): return round((p / w) * 100, 1) if w > 0 else 0.0
    return {
        "actual_cost_usd":   round(actual_cost, 2),
        "local_savings_usd": round(local_savings, 2),
        "local_optimized_cost_usd": round(actual_cost - local_savings, 2),
        "offloaded_turns":   int(offloaded_turns),
        "local_savings_pct": pct(local_savings, actual_cost),
        "batch_savings_usd": round(batch_savings, 2),
        "batch_optimized_cost_usd": round(actual_cost - batch_savings, 2),
        "batchable_turns":   batchable_turns,
        "batch_savings_pct": pct(batch_savings, actual_cost),
        "combined_cost_usd": round(combined_cost, 2),
        "combined_savings_usd": round(combined_savings, 2),
        "combined_savings_pct": pct(combined_savings, actual_cost),
    }


def savings(days: int = 30, include_today: bool = True) -> dict:
    """What-if cost reductions on the same workload.

    Returns:
      actual_cost      — what you paid
      local_offload_*  — if offloadable work had gone to free local LLMs
      batch_*          — if ALL work had been scheduled into batch window
      combined_*       — local offload first, then batch-discount the rest

    All cost values in USD, tokens in raw count.
    """
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1) if include_today else date.today() - timedelta(days=days)

    actual_cost = 0.0
    actual_tokens = 0
    # Local offload buckets
    local_savings = 0.0
    offloaded_tokens = 0
    offloaded_turns = 0
    # Batch buckets
    batchable_cost = 0.0  # cost of turns run OUTSIDE the night window (could have been deferred)
    batchable_turns = 0
    # Combined
    combined_cost = 0.0

    for e in evs:
        d = e["ts"].astimezone().date()
        if d < cutoff:
            continue
        fam = e["family"]
        c = e["cost"]
        tok = e["tokens"]
        actual_cost += c
        actual_tokens += tok

        # Local offload: fraction of this family's work goes to free local LLM
        offload_frac = LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
        local_savings += c * offload_frac
        offloaded_tokens += int(tok * offload_frac)
        if offload_frac >= 1.0:
            offloaded_turns += 1
        elif offload_frac > 0:
            offloaded_turns += offload_frac  # fractional contribution

        # Batch window: turns NOT in [00:00, 06:00) local time could have been deferred
        hour_local = e["ts"].astimezone().hour
        in_night = BATCH_WINDOW_START_HOUR <= hour_local < BATCH_WINDOW_END_HOUR
        if not in_night:
            batchable_cost += c
            batchable_turns += 1

        # Combined: route offloadable work to local (free), then batch-discount remainder
        remaining_cost = c * (1 - offload_frac)
        if not in_night:
            remaining_cost *= (1 - BATCH_DISCOUNT)
        combined_cost += remaining_cost

    batch_savings = batchable_cost * BATCH_DISCOUNT
    combined_savings = actual_cost - combined_cost

    def pct(part: float, whole: float) -> float:
        return round((part / whole) * 100, 1) if whole > 0 else 0.0

    return {
        "days":              days,
        "actual_cost_usd":   round(actual_cost, 2),
        "actual_tokens":     actual_tokens,

        "local_savings_usd": round(local_savings, 2),
        "local_optimized_cost_usd": round(actual_cost - local_savings, 2),
        "offloaded_tokens":  offloaded_tokens,
        "offloaded_turns":   int(offloaded_turns),
        "local_savings_pct": pct(local_savings, actual_cost),

        "batch_savings_usd": round(batch_savings, 2),
        "batch_optimized_cost_usd": round(actual_cost - batch_savings, 2),
        "batchable_turns":   batchable_turns,
        "batch_savings_pct": pct(batch_savings, actual_cost),

        "combined_cost_usd":    round(combined_cost, 2),
        "combined_savings_usd": round(combined_savings, 2),
        "combined_savings_pct": pct(combined_savings, actual_cost),
    }


def sessions_log(days: int = 7, limit: int = 200) -> list[dict]:
    """Per-session summaries derived from JSONL. Each session = one sessionId.
    Returns: [{session, project, started, ended, duration_min, turns, tokens, cost, models, primary_model}]"""
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    buckets: dict[str, dict] = defaultdict(lambda: {
        "start": None, "end": None, "project": "unknown",
        "turns": 0, "tokens": 0, "cost": 0.0, "models": defaultdict(int),
    })
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        b = buckets[e["session"]]
        if b["start"] is None or e["ts"] < b["start"]:
            b["start"] = e["ts"]
        if b["end"] is None or e["ts"] > b["end"]:
            b["end"] = e["ts"]
        if b["project"] == "unknown":
            b["project"] = e["project"]
        b["turns"] += 1
        b["tokens"] += e["tokens"]
        b["cost"] += e["cost"]
        b["models"][e["model"]] += 1

    rows = []
    for sid, b in buckets.items():
        if b["start"] is None:
            continue
        dur_min = round((b["end"] - b["start"]).total_seconds() / 60, 1)
        primary = max(b["models"].items(), key=lambda kv: kv[1])[0] if b["models"] else "—"
        rows.append({
            "session":       sid,
            "project":       b["project"],
            "started":       b["start"].astimezone().isoformat(timespec="seconds"),
            "ended":         b["end"].astimezone().isoformat(timespec="seconds"),
            "duration_min":  dur_min,
            "turns":         b["turns"],
            "tokens":        b["tokens"],
            "cost_usd":      round(b["cost"], 2),
            "primary_model": primary,
        })
    rows.sort(key=lambda r: r["started"], reverse=True)
    return rows[:limit]


def savings_by_model(days: int = 30) -> list[dict]:
    """Per-model what-if breakdown. For each model used in the window, return
    actual + local-optimized + batch-optimized + combined costs."""
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    agg: dict[str, dict] = defaultdict(lambda: {
        "tokens": 0, "turns": 0, "family": "?",
        "actual": 0.0, "local_opt": 0.0, "batch_opt": 0.0, "combined": 0.0,
    })
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        fam = e["family"]
        frac = LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
        hour_local = e["ts"].astimezone().hour
        in_night = BATCH_WINDOW_START_HOUR <= hour_local < BATCH_WINDOW_END_HOUR
        c = e["cost"]
        a = agg[e["model"]]
        a["family"] = fam
        a["tokens"] += e["tokens"]
        a["turns"]  += 1
        a["actual"] += c
        a["local_opt"] += c * (1 - frac)
        a["batch_opt"] += c * ((1 - BATCH_DISCOUNT) if not in_night else 1.0)
        # combined: local offload first, then batch the rest
        remaining = c * (1 - frac)
        if not in_night:
            remaining *= (1 - BATCH_DISCOUNT)
        a["combined"] += remaining

    rows = []
    for model, a in agg.items():
        actual = a["actual"]
        rows.append({
            "model":    model,
            "family":   a["family"],
            "tokens":   a["tokens"],
            "turns":    a["turns"],
            "actual_usd":    round(actual, 2),
            "local_opt_usd": round(a["local_opt"], 2),
            "batch_opt_usd": round(a["batch_opt"], 2),
            "combined_usd":  round(a["combined"], 2),
            "total_savings_usd": round(actual - a["combined"], 2),
            "total_savings_pct": round(((actual - a["combined"]) / actual) * 100, 1) if actual > 0 else 0.0,
        })
    rows.sort(key=lambda r: r["actual_usd"], reverse=True)
    return rows


def totals(days: int = 30) -> dict:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    tokens = 0
    cache_reads = 0
    cost = 0.0
    turns = 0
    sessions = set()
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        tokens += e["tokens"]
        cache_reads += e.get("cache_reads", 0)
        cost += e["cost"]
        turns += 1
        sessions.add(e["session"])
    return {
        "days":        days,
        "tokens":      tokens,
        "cache_reads": cache_reads,
        "cost_usd":    round(cost, 2),
        "turns":       turns,
        "sessions":    len(sessions),
    }


def totals_since(start: date) -> dict:
    """Cumulative totals from `start` (inclusive, local date) through today.
    Used for calendar-aligned windows like quarter-to-date and year-to-date,
    which a rolling N-day `totals()` can't express. Note the floor is the
    earliest JSONL event on disk — if logs began after `start`, the figure is
    cumulative over the data that exists, not back-filled."""
    evs = _iter_events()
    tokens = 0
    cache_reads = 0
    cost = 0.0
    turns = 0
    sessions = set()
    for e in evs:
        if e["ts"].astimezone().date() < start:
            continue
        tokens += e["tokens"]
        cache_reads += e.get("cache_reads", 0)
        cost += e["cost"]
        turns += 1
        sessions.add(e["session"])
    return {
        "since":       start.isoformat(),
        "tokens":      tokens,
        "cache_reads": cache_reads,
        "cost_usd":    round(cost, 2),
        "turns":       turns,
        "sessions":    len(sessions),
    }


def range_stats(start: date, end: date) -> dict:
    """All metrics for an inclusive [start, end] local-date window: raw totals
    (tokens / cache-reads / cost / turns / sessions) PLUS the what-if savings
    breakdown (local offload / batch / combined).

    Powers the LLM-Usage tab's interactive date-range picker and the
    click-a-bar drilldown — selecting a day or range recomputes every headline
    field for exactly that window. If end < start the two are swapped so the UI
    never has to care which input the user touched first."""
    if end < start:
        start, end = end, start
    evs = _iter_events()
    tokens = cache_reads = turns = 0
    cost = 0.0
    sessions: set = set()
    actual_cost = local_savings = batchable_cost = combined_cost = 0.0
    offloaded_turns = 0.0
    offloaded_tokens = 0
    batchable_turns = 0
    for e in evs:
        d = e["ts"].astimezone().date()
        if d < start or d > end:
            continue
        c = e["cost"]; tok = e["tokens"]; fam = e["family"]
        tokens += tok
        cache_reads += e.get("cache_reads", 0)
        cost += c
        turns += 1
        sessions.add(e["session"])
        actual_cost += c
        frac = LOCAL_OFFLOAD_BY_FAMILY.get(fam, 0.0)
        local_savings += c * frac
        offloaded_tokens += int(tok * frac)
        offloaded_turns += frac
        hour_local = e["ts"].astimezone().hour
        in_night = BATCH_WINDOW_START_HOUR <= hour_local < BATCH_WINDOW_END_HOUR
        if not in_night:
            batchable_cost += c
            batchable_turns += 1
        remaining = c * (1 - frac)
        if not in_night:
            remaining *= (1 - BATCH_DISCOUNT)
        combined_cost += remaining

    batch_savings = batchable_cost * BATCH_DISCOUNT
    combined_savings = actual_cost - combined_cost
    def pct(p, w): return round((p / w) * 100, 1) if w > 0 else 0.0
    return {
        "start":             start.isoformat(),
        "end":               end.isoformat(),
        "days":              (end - start).days + 1,
        "tokens":            tokens,
        "cache_reads":       cache_reads,
        "cost_usd":          round(cost, 2),
        "turns":             turns,
        "sessions":          len(sessions),
        "local_savings_usd": round(local_savings, 2),
        "local_savings_pct": pct(local_savings, actual_cost),
        "local_optimized_cost_usd": round(actual_cost - local_savings, 2),
        "offloaded_turns":   int(offloaded_turns),
        "offloaded_tokens":  offloaded_tokens,
        "batch_savings_usd": round(batch_savings, 2),
        "batch_savings_pct": pct(batch_savings, actual_cost),
        "batch_optimized_cost_usd": round(actual_cost - batch_savings, 2),
        "batchable_turns":   batchable_turns,
        "combined_cost_usd":    round(combined_cost, 2),
        "combined_savings_usd": round(combined_savings, 2),
        "combined_savings_pct": pct(combined_savings, actual_cost),
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("today:", today())
    print("30d totals:", totals(30))
    print("top projects (30d):", by_project(30)[:5])
    print("top models (30d):", by_model(30)[:5])
