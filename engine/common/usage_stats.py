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
Anthropic public pricing (Jan 2026). If a model is unknown, it's billed
at the Sonnet rate (conservative middle-ground) and flagged.

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
}

# Anthropic Batch API: 50% discount for tasks that can tolerate async execution
# within a 24h window. Batching only makes sense for work that doesn't need
# real-time response — here we model "could have been batched" as everything
# outside the defined live-work window.
BATCH_DISCOUNT = 0.50
BATCH_WINDOW_START_HOUR = 0   # midnight
BATCH_WINDOW_END_HOUR   = 6   # 06:00

import os as _os

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
        return "sonnet"
    n = name.lower()
    if "opus" in n:   return "opus"
    if "haiku" in n:  return "haiku"
    if "sonnet" in n: return "sonnet"
    return "sonnet"


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
    return (
        (usage.get("input_tokens", 0) or 0)
        + (usage.get("output_tokens", 0) or 0)
        + (usage.get("cache_read_input_tokens", 0) or 0)
        + (usage.get("cache_creation_input_tokens", 0) or 0)
    )


_PROJECT_RE = re.compile(r"[A-Z]-{2,}([^\\/-]+)")


def _project_from_cwd(cwd: str | None, folder_name: str) -> str:
    """Best-effort project label.
    Priority:
      1. cwd path: C:\QIH → 'QI_Hive', C:\QI → 'Maia', etc.
      2. Folder name prefix
      3. 'unknown'
    """
    if cwd:
        c = cwd.replace("/", "\\").upper()
        if   c.startswith("C:\\QIH"):      return "QI_Hive"
        elif c.startswith("C:\\QI\\")  or c == "C:\\QI": return "Maia"
        elif c.startswith("C:\\NAYA"):     return "Naya"
        elif c.startswith("C:\\NEXUS"):    return "NEXUS"
        elif c.startswith("C:\\OC") or c.startswith("C:\\OPENCLAW"): return "OpenClaw"
        elif c.startswith("C:\\EASYFLOW"): return "EasyFlow"
        elif c.startswith("C:\\FILEHQ"):   return "FileHQ"
        elif c.startswith("C:\\CLAUDE"):   return "Claude_Manager"
        elif c.startswith("C:\\MQ"):       return "MQ"
        elif c.startswith("C:\\UNIVERSAL"):return "QI_Universal"
        elif c.startswith("C:\\GMAIL"):    return "Gmail_Beyond"
        elif "LINE BOTS" in c or "\\MAIA" in c or "\\RENNE\\DOWNLOADS" in c: return "Maia"
        # Any leftover user-profile path → best-effort from cwd
        elif c.startswith("C:\\USERS\\"):
            # E.g. C:\Users\renne\projects\foo → "foo"
            parts = [p for p in c.split("\\") if p and p.upper() != "USERS"]
            # parts[0] = drive (C:), parts[1] = renne, parts[2] = first meaningful folder
            if len(parts) >= 3:
                return parts[2].replace(" ", "_")
    # fallback — try to extract from folder name (e.g. C--CLAUDE-... → CLAUDE)
    parts = folder_name.split("--")
    if len(parts) >= 2:
        return parts[1].split("-")[0] or "unknown"
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
                        "ts":      ts,
                        "model":   model or "unknown",
                        "family":  _model_family(model),
                        "project": _project_from_cwd(d.get("cwd"), folder),
                        "session": d.get("sessionId") or folder,
                        "tokens":  _tokens(usage),
                        "cost":    _cost(usage, model),
                    })
        except (PermissionError, OSError):
            continue

    events.sort(key=lambda e: e["ts"])
    _CACHE.update(stamp=now, events=events)
    return events


def today() -> dict:
    evs = _iter_events()
    today_utc = datetime.now(timezone.utc).date()
    today_local = date.today()
    sessions = set()
    turns = 0
    tokens = 0
    cost = 0.0
    for e in evs:
        d_local = e["ts"].astimezone().date()
        if d_local == today_local:
            sessions.add(e["session"])
            turns += 1
            tokens += e["tokens"]
            cost += e["cost"]
    return {
        "tokens":           tokens,
        "cost_usd":         round(cost, 2),
        "sessions":         len(sessions),
        "assistant_turns":  turns,
        "date":             today_local.isoformat(),
    }


def daily(days: int = 30) -> list[dict]:
    evs = _iter_events()
    cutoff = date.today() - timedelta(days=days - 1)
    buckets: dict[date, dict] = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "turns": 0, "sessions": set()})
    for e in evs:
        d = e["ts"].astimezone().date()
        if d < cutoff:
            continue
        b = buckets[d]
        b["tokens"]  += e["tokens"]
        b["cost"]    += e["cost"]
        b["turns"]   += 1
        b["sessions"].add(e["session"])
    out = []
    for i in range(days):
        d = cutoff + timedelta(days=i)
        b = buckets.get(d, {"tokens": 0, "cost": 0.0, "turns": 0, "sessions": set()})
        out.append({
            "date":     d.isoformat(),
            "tokens":   b["tokens"],
            "cost_usd": round(b["cost"], 2),
            "turns":    b["turns"],
            "sessions": len(b["sessions"]),
        })
    return out


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
    cost = 0.0
    turns = 0
    sessions = set()
    for e in evs:
        if e["ts"].astimezone().date() < cutoff:
            continue
        tokens += e["tokens"]
        cost += e["cost"]
        turns += 1
        sessions.add(e["session"])
    return {
        "days":     days,
        "tokens":   tokens,
        "cost_usd": round(cost, 2),
        "turns":    turns,
        "sessions": len(sessions),
    }


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print("today:", today())
    print("30d totals:", totals(30))
    print("top projects (30d):", by_project(30)[:5])
    print("top models (30d):", by_model(30)[:5])
