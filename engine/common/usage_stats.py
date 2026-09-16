"""
QI Hive — Claude Code usage stats (v2, 2026-09-16).

Parses ~/.claude/projects/**/*.jsonl locally to produce token + cost
aggregates. No API calls, no keys. Shapes:

    today()         -> {tokens, cache_reads, cost_usd, sessions, assistant_turns}
    daily(n=30)     -> [{date, tokens, cache_reads, cost_usd, turns, sessions,
                         input_tokens, output_tokens, cache_write_5m, cache_write_1h, ...}]
    by_project(n)   -> [{project, tokens, cost_usd, turns}, ...]
    by_model(n)     -> [{model, tokens, cost_usd, turns}, ...]

What changed in v2 (audit 2026-09-16, QIHive_Feature_Audit_2026-09-16.docx)
---------------------------------------------------------------------------
1. DEDUPLICATION. Claude Code writes one JSONL line per content block (text,
   thinking, tool_use) and every line repeats the same `message.id` and the
   same `usage` block. v1 counted each line as a turn, inflating turns, tokens
   and cost 2-5x per day. v2 keeps the first line per message id (fallback:
   requestId) — the same rule ccusage applies.
2. PER-MODEL PRICING. v1 priced by family with Opus-4-era numbers (opus
   $15/$75). Prices are now per model id from Anthropic's public pricing page
   (fetched 2026-09-16), with a family fallback for models not yet listed.
   Cache read is 10% of input (2.5% on Fable 5.1 / Mythos 5.1); cache write is
   125% (5m) / 200% (1h).
3. INCREMENTAL PARSING. Files are parsed once and re-parsed only when their
   (mtime, size) changes, so a cold call no longer re-reads every transcript.
4. ATTRIBUTION. Sub-agent transcripts (`<session>/subagents/agent-*.jsonl`)
   resolve through their top-level project folder; cwd components and the
   Claude-Code folder encoding are matched against registry paths, so legacy
   roots (C:\\CLAUDE, C:\\Retirement Analyzer, D:\\Dev\\MediaStudio ...) map to
   their project instead of "unknown".

Combined effect measured on 2026-09-16 (30-day window): $28,528 -> $4,690.
"""
from __future__ import annotations
import json
import os as _os
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

PRICING_VERSION = "2026-09-16"
PRICING_SOURCE = "https://platform.claude.com/docs/en/about-claude/pricing"

# ── Pricing ($ per 1M tokens): model id -> (input, output, cache_read_multiplier)
# Keys are matched longest-prefix against the normalised model id, so a dated
# id like claude-haiku-4-5-20251001 resolves to claude-haiku-4-5.
MODEL_PRICES: dict[str, tuple[float, float, float]] = {
    "claude-fable-5-1":  (10.00, 50.00, 0.025),
    "claude-mythos-5-1": (10.00, 50.00, 0.025),
    "claude-fable-5":    (10.00, 50.00, 0.10),
    "claude-mythos-5":   (10.00, 50.00, 0.10),
    "claude-opus-5":     ( 5.00, 25.00, 0.10),
    "claude-opus-4-8":   ( 5.00, 25.00, 0.10),
    "claude-opus-4-7":   ( 5.00, 25.00, 0.10),
    "claude-opus-4-6":   ( 5.00, 25.00, 0.10),
    "claude-opus-4-5":   ( 5.00, 25.00, 0.10),
    "claude-opus-4-1":   (15.00, 75.00, 0.10),
    "claude-opus-4":     (15.00, 75.00, 0.10),
    "claude-sonnet-5":   ( 2.00, 10.00, 0.10),
    "claude-sonnet-4-6": ( 3.00, 15.00, 0.10),
    "claude-sonnet-4-5": ( 3.00, 15.00, 0.10),
    "claude-sonnet-4":   ( 3.00, 15.00, 0.10),
    "claude-haiku-4-5":  ( 1.00,  5.00, 0.10),
    "claude-haiku-3-5":  ( 0.80,  4.00, 0.10),
}
# Family fallback for ids not in the table (current-generation prices).
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "opus":   ( 5.00, 25.00),
    "fable":  (10.00, 50.00),
    "sonnet": ( 2.00, 10.00),
    "haiku":  ( 1.00,  5.00),
    "other":  ( 2.00, 10.00),
}
CACHE_READ_MULT     = 0.10   # default; per-model override in MODEL_PRICES
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00

_PRICE_KEYS = sorted(MODEL_PRICES, key=len, reverse=True)
_DATE_SUFFIX = re.compile(r"-20\d{6}$")


def normalize_model(name: str | None) -> str:
    """'us.anthropic.claude-opus-4-1-20250805@v1' -> 'claude-opus-4-1'."""
    n = (name or "").strip().lower()
    if "claude-" in n:
        n = n[n.index("claude-"):]
    n = n.split("@", 1)[0]
    n = _DATE_SUFFIX.sub("", n)
    return n


def price_for(model: str | None) -> tuple[float, float, float]:
    """(input $/M, output $/M, cache-read multiplier) for a model id."""
    n = normalize_model(model)
    for key in _PRICE_KEYS:
        if n == key or n.startswith(key + "-"):
            return MODEL_PRICES[key]
    i, o = MODEL_PRICING[_model_family(model)]
    return (i, o, CACHE_READ_MULT)


def pricing_text() -> str:
    """One-line footer for the dashboard, generated from the table so the
    prose can never drift from the numbers again."""
    parts = []
    for key in ("claude-fable-5-1", "claude-fable-5", "claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"):
        i, o, cr = MODEL_PRICES[key]
        parts.append(f"{key.replace('claude-', '')} ${i:g}/${o:g}")
    return (" · ".join(parts)
            + " (per 1M tokens, input/output) · cache-read 10% (2.5% on Fable 5.1) · "
              f"cache-write 125%/200% (5m/1h) · pricing table v{PRICING_VERSION}")


# ── What-if optimization heuristics ─────────────────────────────────────
LOCAL_OFFLOAD_BY_FAMILY = {
    "haiku":  1.00,
    "sonnet": 0.40,
    "opus":   0.00,
    "fable":  0.00,
    "other":  0.40,
}
BATCH_DISCOUNT = 0.50
BATCH_WINDOW_START_HOUR = 0
BATCH_WINDOW_END_HOUR   = 6


def _find_projects_dir() -> Path:
    """Locate ~/.claude/projects regardless of the user running the service."""
    candidates = []
    env_home = _os.environ.get("USERPROFILE") or str(Path.home())
    candidates.append(Path(env_home) / ".claude" / "projects")
    users_dir = Path(r"C:\Users")
    if users_dir.exists():
        for user in users_dir.iterdir():
            cand = user / ".claude" / "projects"
            if cand.is_dir():
                candidates.append(cand)
    for c in candidates:
        if c.is_dir() and any(c.rglob("*.jsonl")):
            return c
    return candidates[0] if candidates else Path.home() / ".claude" / "projects"


PROJECTS_DIR = _find_projects_dir()
_CACHE: dict = {"stamp": 0.0, "events": []}
_TTL = 30.0
# path -> {"sig": (mtime_ns, size), "events": [raw events with 'mid']}
_FILE_CACHE: dict[str, dict] = {}


def _model_family(name: str | None) -> str:
    if not name:
        return "other"
    n = name.lower()
    if "opus" in n:   return "opus"
    if "fable" in n:  return "fable"
    if "mythos" in n: return "fable"
    if "sonnet" in n: return "sonnet"
    if "haiku" in n:  return "haiku"
    return "other"


def _split(usage: dict) -> dict:
    """Token split of one usage block. Older transcripts only carry the flat
    cache_creation_input_tokens; treat that as a 5-minute write."""
    cc = usage.get("cache_creation") or {}
    cw5 = cc.get("ephemeral_5m_input_tokens", 0) or 0
    cw1 = cc.get("ephemeral_1h_input_tokens", 0) or 0
    if not cc:
        cw5 = usage.get("cache_creation_input_tokens", 0) or 0
    return {
        "input":      usage.get("input_tokens", 0) or 0,
        "output":     usage.get("output_tokens", 0) or 0,
        "cache_read": usage.get("cache_read_input_tokens", 0) or 0,
        "cw5":        cw5,
        "cw1":        cw1,
    }


def _cost(usage: dict, model: str | None) -> float:
    in_rate, out_rate, cr_mult = price_for(model)
    s = _split(usage)
    return (
        s["input"]      * in_rate / 1_000_000
        + s["output"]   * out_rate / 1_000_000
        + s["cache_read"] * in_rate * cr_mult / 1_000_000
        + s["cw5"]      * in_rate * CACHE_WRITE_5M_MULT / 1_000_000
        + s["cw1"]      * in_rate * CACHE_WRITE_1H_MULT / 1_000_000
    )


def _tokens(usage: dict) -> int:
    """'Fresh' tokens: input + output + cache writes. Excludes cache re-reads."""
    s = _split(usage)
    return s["input"] + s["output"] + s["cw5"] + s["cw1"]


def _cache_reads(usage: dict) -> int:
    return usage.get("cache_read_input_tokens", 0) or 0


# ── Project attribution ─────────────────────────────────────────────────
_REGISTRY_PATH = r"C:\QIH\ecosystem\qi_registry.json"

# Manual aliases for roots that are not (or no longer) in the registry.
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
    "RETIREMENT ANALYZER": "retirementanalyzer",
    "RETIREMENTANALYZER":  "retirementanalyzer",
    "PLAYDECK":       "playdeck",
    "GAMEZ":          "gamez",
    "GODSEYE":        "godseye",
    "MEDIASTUDIO":    "mediastudio",
    "FILMFORGE":      "filmforge",
    "VOICESTUDIO":    "voice_studio",
    "SYNVOX":         "synvox",
    "NOOSORBIS":      "noosorbis",
    "BAGUAPP":        "baguapp",
    "BAGUAPP_PROD":   "baguapp_prod",
    "MAILBRAIN":      "mailbrain",
    "MYTHOLOGIES":    "mythologies",
    "HINDU MYTHOLOGY - VERITABLE HOKUM": "mythologies",
    "NOTE DISCOVERY": "onbase_dna",
    "DIGITIZATION COSTS": "digitization",
    "MILKWISE":       "milkwise",
    "TRINITY":        "trinity",
    "CONNECTOR":      "connector",
    "AKIYASCOUT":     "akiyascout",
    "VLCDAEMON":      "vlcdaemon",
}
# Components that are never a project name on their own.
_SKIP_COMPONENTS = {"", "C:", "D:", "USERS", "RENNE", "DOWNLOADS", "APPS", "DEV", "AI",
                    "SUBAGENTS", "WORKTREES", ".CLAUDE", "SITE", "DOCS", "TOOLS", "SRC"}


def _encode_folder(path: str) -> str:
    """Claude Code's transcript folder name for a cwd: every non-alnum char -> '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def _load_registry_path_map() -> tuple[list[tuple[str, str]], dict[str, str], list[tuple[str, str]]]:
    """(prefix rows, basename aliases, encoded-folder rows) from the registry."""
    _TIE_PRIORITY = {"qi_brain": 10, "qi_hive": 5}
    rows: list[tuple[str, str]] = []
    aliases: dict[str, str] = {}
    encoded: list[tuple[str, str]] = []
    try:
        with open(_REGISTRY_PATH, encoding="utf-8") as f:
            reg = json.load(f)
        for proj in reg.get("projects", []):
            pid = (proj.get("id") or "").strip()
            if not pid:
                continue
            for key in ("path", "original_path", "path_standard"):
                raw = proj.get(key)
                if raw and isinstance(raw, str) and re.match(r"^[A-Za-z]:\\", raw):
                    norm = raw.replace("/", "\\").rstrip("\\").upper()
                    rows.append((norm, pid))
                    base = norm.rsplit("\\", 1)[-1]
                    if base and base not in _SKIP_COMPONENTS:
                        aliases.setdefault(base, pid)
                    encoded.append((_encode_folder(raw.rstrip("\\")).upper(), pid))
        rows.sort(key=lambda t: (len(t[0]), _TIE_PRIORITY.get(t[1], 0)), reverse=True)
        encoded.sort(key=lambda t: len(t[0]), reverse=True)
    except Exception:
        pass
    return rows, aliases, encoded


_REG_PATH_MAP, _REG_ALIASES, _REG_ENCODED = _load_registry_path_map()
_ALIASES: dict[str, str] = {**_REG_ALIASES, **_FOLDER_ALIASES}   # manual wins
_WORKTREE_HASH = re.compile(r"-[0-9A-F]{4,}$", re.IGNORECASE)


def _project_from_cwd(cwd: str | None, folder_name: str) -> str:
    """Canonical project id for an event.

    1. longest registry-path prefix on cwd
    2. cwd components, deepest first, against registry basenames + aliases
    3. the transcript folder name against Claude Code's encoding of registry paths
    4. folder-name segments against aliases (legacy C--NAME forms)
    5. 'unknown'
    """
    if cwd:
        c = cwd.replace("/", "\\").rstrip("\\").upper()
        for reg_path, pid in _REG_PATH_MAP:
            if c == reg_path or c.startswith(reg_path + "\\"):
                return pid
        for part in reversed(c.split("\\")):
            stem = _WORKTREE_HASH.sub("", part.strip())
            if stem in _SKIP_COMPONENTS:
                continue
            if stem in _ALIASES:
                return _ALIASES[stem]
            if part in _ALIASES:
                return _ALIASES[part]
    fn_upper = (folder_name or "").upper()
    for enc, pid in _REG_ENCODED:
        if fn_upper == enc or fn_upper.startswith(enc + "-"):
            return pid
    parts = [p for p in fn_upper.replace("--", "\x00").split("\x00") if p]
    for part in reversed(parts):
        stem = _WORKTREE_HASH.sub("", part)
        if stem in _ALIASES:
            return _ALIASES[stem]
        if part in _ALIASES:
            return _ALIASES[part]
    return "unknown"


# ── Parsing ─────────────────────────────────────────────────────────────
def _top_folder(jsonl: Path) -> str:
    """The project folder directly under PROJECTS_DIR (sub-agent files live in
    <session>/subagents/, whose own parent name is meaningless)."""
    try:
        return jsonl.relative_to(PROJECTS_DIR).parts[0]
    except Exception:
        return jsonl.parent.name


def parse_lines(lines, folder: str) -> list[dict]:
    """Raw usage events from JSONL text lines (no dedup — see _assemble)."""
    out: list[dict] = []
    for line in lines:
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
        s = _split(usage)
        out.append({
            "ts":          ts,
            "mid":         msg.get("id") or d.get("requestId") or None,
            "model":       model or "unknown",
            "family":      _model_family(model),
            "project":     _project_from_cwd(d.get("cwd"), folder),
            "session":     d.get("sessionId") or folder,
            "tokens":      s["input"] + s["output"] + s["cw5"] + s["cw1"],
            "cache_reads": s["cache_read"],
            "input":       s["input"],
            "output":      s["output"],
            "cw5":         s["cw5"],
            "cw1":         s["cw1"],
            "cost":        _cost(usage, model),
        })
    return out


def _parse_file(jsonl: Path) -> list[dict]:
    try:
        st = jsonl.stat()
    except OSError:
        return []
    sig = (st.st_mtime_ns, st.st_size)
    key = str(jsonl)
    hit = _FILE_CACHE.get(key)
    if hit and hit["sig"] == sig:
        return hit["events"]
    folder = _top_folder(jsonl)
    try:
        with jsonl.open("r", encoding="utf-8") as f:
            events = parse_lines(f, folder)
    except (PermissionError, OSError):
        events = []
    _FILE_CACHE[key] = {"sig": sig, "events": events}
    return events


def dedup(events: list[dict]) -> list[dict]:
    """Keep the first event per message id; events without an id are kept."""
    seen: set = set()
    out = []
    for e in events:
        mid = e.get("mid")
        if mid:
            if mid in seen:
                continue
            seen.add(mid)
        out.append(e)
    return out


def _iter_events(force: bool = False):
    """Deduplicated usage events across all transcripts, cached 30s; files are
    re-parsed only when their mtime/size changes."""
    now = time.time()
    if not force and now - _CACHE["stamp"] < _TTL and _CACHE["events"]:
        return _CACHE["events"]

    events: list[dict] = []
    if not PROJECTS_DIR.exists():
        _CACHE.update(stamp=now, events=events)
        return events

    live: set[str] = set()
    for jsonl in PROJECTS_DIR.rglob("*.jsonl"):
        live.add(str(jsonl))
        events.extend(_parse_file(jsonl))
    for gone in [k for k in _FILE_CACHE if k not in live]:
        _FILE_CACHE.pop(gone, None)

    events.sort(key=lambda e: e["ts"])
    events = dedup(events)
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


def _new_bucket():
    return {"tokens": 0, "cache_reads": 0, "cost": 0.0, "turns": 0, "sessions": set(),
            "input": 0, "output": 0, "cw5": 0, "cw1": 0}


def daily(days: int = 30) -> list[dict]:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    buckets: dict[date, dict] = defaultdict(_new_bucket)
    whatif: dict[date, dict] = defaultdict(lambda: {"local": 0.0, "batch": 0.0, "combined": 0.0})
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
        b["input"] += e.get("input", 0); b["output"] += e.get("output", 0)
        b["cw5"] += e.get("cw5", 0);     b["cw1"] += e.get("cw1", 0)
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
        b = buckets.get(d) or _new_bucket()
        w = whatif.get(d, {"local": 0.0, "batch": 0.0, "combined": 0.0})
        out.append({
            "date":              d.isoformat(),
            "tokens":            b["tokens"],
            "cache_reads":       b["cache_reads"],
            "cost_usd":          round(b["cost"], 2),
            "local_cost_usd":    round(w["local"], 2),
            "batch_cost_usd":    round(w["batch"], 2),
            "combined_cost_usd": round(w["combined"], 2),
            "turns":             b["turns"],
            "sessions":          len(b["sessions"]),
            "input_tokens":      b["input"],
            "output_tokens":     b["output"],
            "cache_write_5m":    b["cw5"],
            "cache_write_1h":    b["cw1"],
        })
    return out


def _whatif_agg(evs, cutoff, key):
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
        a = agg[e[key]]
        a["family"] = fam
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
    for k, a in agg.items():
        actual = a["actual"]
        row = {
            key:             k,
            "tokens":        a["tokens"],
            "turns":         a["turns"],
            "actual_usd":    round(actual, 2),
            "local_opt_usd": round(a["local_opt"], 2),
            "batch_opt_usd": round(a["batch_opt"], 2),
            "combined_usd":  round(a["combined"], 2),
            "total_savings_usd": round(actual - a["combined"], 2),
            "total_savings_pct": round(((actual - a["combined"]) / actual) * 100, 1) if actual > 0 else 0.0,
        }
        if key == "model":
            row["family"] = a["family"]
        rows.append(row)
    rows.sort(key=lambda r: r["actual_usd"], reverse=True)
    return rows


def savings_by_project(days: int = 30) -> list[dict]:
    return _whatif_agg(_iter_events(), date.today() - timedelta(days=days - 1), "project")


def savings_by_model(days: int = 30) -> list[dict]:
    return _whatif_agg(_iter_events(), date.today() - timedelta(days=days - 1), "model")


def _simple_agg(evs, cutoff, key):
    agg: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "turns": 0, "family": "?"})
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        a = agg[e[key]]
        a["tokens"] += e["tokens"]
        a["cost"]   += e["cost"]
        a["turns"]  += 1
        a["family"] = e["family"]
    rows = []
    for k, v in agg.items():
        row = {key: k, "tokens": v["tokens"], "cost_usd": round(v["cost"], 2), "turns": v["turns"]}
        if key == "model":
            row["family"] = v["family"]
        rows.append(row)
    rows.sort(key=lambda r: r["cost_usd"], reverse=True)
    return rows


def by_project(days: int = 30) -> list[dict]:
    return _simple_agg(_iter_events(), date.today() - timedelta(days=days - 1), "project")


def by_model(days: int = 30) -> list[dict]:
    return _simple_agg(_iter_events(), date.today() - timedelta(days=days - 1), "model")


def _savings_window(evs, start: date, end: date) -> dict:
    actual_cost = local_savings = batchable_cost = combined_cost = 0.0
    actual_tokens = offloaded_tokens = batchable_turns = 0
    offloaded_turns = 0.0
    for e in evs:
        d = e["ts"].astimezone().date()
        if d < start or d > end:
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


def savings_today() -> dict:
    t = date.today()
    return _savings_window(_iter_events(), t, t)


def savings(days: int = 30, include_today: bool = True) -> dict:
    end = date.today() if include_today else date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    r = _savings_window(_iter_events(), start, end)
    r["days"] = days
    return r


def sessions_log(days: int = 7, limit: int = 200) -> list[dict]:
    """Per-session summaries derived from JSONL. Each session = one sessionId."""
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


def totals(days: int = 30) -> dict:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    tokens = cache_reads = turns = 0
    cost = 0.0
    sessions = set()
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        tokens += e["tokens"]
        cache_reads += e.get("cache_reads", 0)
        cost += e["cost"]
        turns += 1
        sessions.add(e["session"])
    return {"days": days, "tokens": tokens, "cache_reads": cache_reads,
            "cost_usd": round(cost, 2), "turns": turns, "sessions": len(sessions)}


def totals_since(start: date) -> dict:
    """Cumulative totals from `start` (inclusive, local date) through today."""
    evs = _iter_events()
    tokens = cache_reads = turns = 0
    cost = 0.0
    sessions = set()
    for e in evs:
        if e["ts"].astimezone().date() < start:
            continue
        tokens += e["tokens"]
        cache_reads += e.get("cache_reads", 0)
        cost += e["cost"]
        turns += 1
        sessions.add(e["session"])
    return {"since": start.isoformat(), "tokens": tokens, "cache_reads": cache_reads,
            "cost_usd": round(cost, 2), "turns": turns, "sessions": len(sessions)}


def range_stats(start: date, end: date) -> dict:
    """All metrics for an inclusive [start, end] local-date window."""
    if end < start:
        start, end = end, start
    evs = _iter_events()
    tokens = cache_reads = turns = 0
    cost = 0.0
    sessions: set = set()
    for e in evs:
        d = e["ts"].astimezone().date()
        if d < start or d > end:
            continue
        tokens += e["tokens"]; cache_reads += e.get("cache_reads", 0)
        cost += e["cost"]; turns += 1; sessions.add(e["session"])
    r = {
        "start":       start.isoformat(),
        "end":         end.isoformat(),
        "days":        (end - start).days + 1,
        "tokens":      tokens,
        "cache_reads": cache_reads,
        "cost_usd":    round(cost, 2),
        "turns":       turns,
        "sessions":    len(sessions),
    }
    r.update(_savings_window(evs, start, end))
    return r


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("pricing:", pricing_text())
    print("today:", today())
    print("30d totals:", totals(30))
    print("top projects (30d):", by_project(30)[:8])
    print("top models (30d):", by_model(30)[:5])
