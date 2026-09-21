# -*- coding: utf-8 -*-
"""
QI Hive — usage stats for the two non-Claude Trinity legs (2026-09-20).

Claude's usage has been measured since day one (`usage_stats.py`). The other
two thirds of the Trinity went live 2026-09-08 and were invisible on the LLM
Usage tab: ChatGPT via Codex, and Gemini via `qi_gemini_mcp.py`. This module
parses both from local evidence so all three legs appear side by side.

    today()             -> {providers: {...}, tokens, cost_usd, calls, ...}
    daily(n=30)         -> [{date, per-provider tokens/cost}, ...]
    range_stats(s, e)   -> window totals
    by_model(n)         -> [{provider, model, tokens, cost_usd, calls}, ...]
    by_provider(n)      -> [{provider, tokens, cost_usd, calls}, ...]
    by_project(n)       -> [{project, tokens, cost_usd, calls}, ...]
    quota()             -> live quota pressure, the number that actually matters

WHERE THE NUMBERS COME FROM
---------------------------
Codex  — `~/.codex/sessions/**/rollout-*.jsonl`, the CLI's own transcripts.
         Every model response writes a `token_usage_record` carrying a measured
         input / cached-input / output / reasoning split. This is ground truth
         from the vendor's own client, not an estimate. It covers BOTH the MCP
         calls Claude makes and the sessions Renne drives in Codex Desktop; the
         `originator` field separates them.

Gemini — `C:\\QIH\\data\\gemini_mcp\\tokens_YYYY-MM-DD.jsonl`, written by
         `qi_gemini_mcp.py` from Google's `usageMetadata` (added 2026-09-20).
         For calls made BEFORE that logging existed, the diagnostic log
         `C:\\QIH\\LOGS\\gemini_mcp.log` gives tool/model/prompt_chars per call;
         those are reconstructed as chars/4 and flagged `estimated`. Estimated
         and measured rows are never silently mixed — every aggregate carries an
         `estimated_calls` count so the dashboard can say which is which.

TWO LESSONS FROM THE 2026-09-16 AUDIT, APPLIED HERE
---------------------------------------------------
1. DEDUPLICATE ON THE VENDOR'S OWN ID. That audit found Claude's figures 2-5x
   too high because one logical response wrote several transcript lines. Codex
   has the same hazard from a different direction: each `token_usage_record`
   carries `usage` (this response), `turn_token_usage` and `thread_token_usage`
   (both running totals). Summing the wrong one inflates a long thread by its
   own length. We read `usage` only, and dedup on `response_id`.
2. PRICES ARE DATA, NOT CODE. They live in `config/llm_prices_external.json`
   with a source URL and a verification date. An unpriced model reports
   cost=None and `priced=False` rather than a plausible-looking wrong number.

WHAT THE COST COLUMN MEANS
--------------------------
API-EQUIVALENT, exactly as on the Claude side: what this traffic would have
cost on a metered API. Neither assistant is metered — ChatGPT Plus is $20/mo
flat and the Gemini key is free-tier. Per Renne's standing directive
(2026-09-08): "the unit of waste is quota, not dollars." `quota()` is the
number to act on; the dollar figure is for comparing the three legs' weight.
"""
from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PRICE_FILE = Path(r"C:\QIH\config\llm_prices_external.json")
GEMINI_DATA_DIR = Path(r"C:\QIH\data\gemini_mcp")
GEMINI_CALL_LOG = Path(r"C:\QIH\LOGS\gemini_mcp.log")
GEMINI_CONFIG = Path(r"C:\QIH\config\gemini_mcp.json")

PROVIDERS = ("codex", "gemini")
PROVIDER_LABEL = {"codex": "ChatGPT / Codex", "gemini": "Gemini"}

# Claude Code's own estimate ratio, reused so the two fallbacks agree.
CHARS_PER_TOKEN_EST = 4

_TTL = 30.0                      # seconds; matches usage_stats' event cache
_CACHE: dict = {"stamp": 0.0, "events": []}
_FILE_CACHE: dict = {}           # path -> {"sig": (mtime_ns, size), "events": [...]}
_PRICES: dict = {"stamp": 0.0, "data": {}}


# ── Prices ───────────────────────────────────────────────────────────────────
def prices(force: bool = False) -> dict:
    """The price table, re-read when the file changes (cached 30s).

    Editing the JSON is meant to be enough; nobody should have to restart a
    service to correct a rate they just found wrong.
    """
    now = time.time()
    if not force and now - _PRICES["stamp"] < _TTL and _PRICES["data"]:
        return _PRICES["data"]
    try:
        data = json.loads(PRICE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    _PRICES.update(stamp=now, data=data)
    return data


def pricing_version() -> str:
    return prices().get("pricing_version") or "unset"


def subscription(provider: str) -> dict:
    return (prices().get("subscriptions") or {}).get(provider) or {}


def monthly_subscription_usd() -> float:
    """Actual cash per month across both assistant plans."""
    subs = prices().get("subscriptions") or {}
    return sum(float(s.get("usd_per_month") or 0.0) for s in subs.values())


def normalize_model(provider: str, name: str | None) -> str:
    n = (name or "").strip().lower()
    if not n:
        n = (prices().get(provider, {}) or {}).get("_default_model") or "unknown"
    # 'openai/gpt-5.6-terra', 'models/gemini-3.6-flash' -> bare slug
    if "/" in n:
        n = n.rsplit("/", 1)[-1]
    return n


def price_for(provider: str, model: str) -> tuple[dict, bool]:
    """(rate record, inferred). `inferred` is True when the slug has no
    published rate and we fell back to the account's default model — the
    dashboard must show that as an assumption, not a measurement."""
    block = prices().get(provider) or {}
    models = block.get("models") or {}
    rec = models.get(model)
    if rec and rec.get("input") is not None:
        return rec, False
    alt = block.get("_price_unknown_as")
    if alt and models.get(alt, {}).get("input") is not None:
        return models[alt], True
    return {}, False


def _cost(provider: str, model: str, split: dict) -> tuple[float | None, bool, bool]:
    """(usd, priced, inferred). Cached input bills at the vendor's cached rate;
    where none is published it bills at the full input rate, which errs high and
    never understates."""
    rec, inferred = price_for(provider, model)
    if not rec or rec.get("input") is None or rec.get("output") is None:
        return None, False, inferred
    in_rate = float(rec["input"])
    out_rate = float(rec["output"])
    cached_rate = rec.get("cached_input")
    cached_rate = in_rate if cached_rate is None else float(cached_rate)
    fresh_in = max(0, split["input"] - split["cached_input"])
    usd = (
        fresh_in * in_rate / 1_000_000
        + split["cached_input"] * cached_rate / 1_000_000
        + split["output"] * out_rate / 1_000_000
        + split.get("cache_write", 0) * in_rate / 1_000_000
    )
    return usd, True, inferred


def pricing_text() -> str:
    """Dashboard footer, generated from the table so the prose cannot drift
    from the numbers (the drift that caused the 2026-09-16 overstatement)."""
    bits = []
    for provider in PROVIDERS:
        block = prices().get(provider) or {}
        models = block.get("models") or {}
        priced = [(m, r) for m, r in models.items() if r.get("input") is not None]
        priced.sort(key=lambda kv: kv[1]["input"])
        shown = " · ".join(f"{m} ${r['input']:g}/${r['output']:g}" for m, r in priced[:4])
        if shown:
            bits.append(f"{PROVIDER_LABEL[provider]}: {shown}")
    subs = prices().get("subscriptions") or {}
    sub_txt = " + ".join(
        f"{s.get('plan', k)} ${float(s.get('usd_per_month') or 0):g}/mo" for k, s in subs.items()
    )
    return (
        " · ".join(bits)
        + f" (per 1M tokens, input/output) · external price table v{pricing_version()}"
        + (f" · actual outlay: {sub_txt}" if sub_txt else "")
    )


# ── Shared helpers ───────────────────────────────────────────────────────────
def _empty_split() -> dict:
    return {"input": 0, "cached_input": 0, "cache_write": 0, "output": 0, "reasoning": 0}


def _fresh(split: dict) -> int:
    """'Fresh' tokens, matching usage_stats' ex-cache definition: everything
    that was not served from cache. Keeps the three legs comparable."""
    return (max(0, split["input"] - split["cached_input"])
            + split["output"] + split.get("cache_write", 0))


def _project_from_cwd(cwd: str | None) -> str:
    """Reuse the Claude-side registry attribution so a Codex session in
    C:\\APPS\\NAYA lands on the same project id a Claude session there would."""
    if not cwd:
        return "unknown"
    try:
        from engine.common import usage_stats as _us
    except Exception:
        try:
            import usage_stats as _us          # direct-script fallback
        except Exception:
            return "unknown"
    try:
        return _us._project_from_cwd(cwd, "")
    except Exception:
        return "unknown"


def _as_local_date(ts: datetime) -> date:
    return ts.astimezone().date()


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# ── Codex: ~/.codex/sessions/**/rollout-*.jsonl ──────────────────────────────
CONFIG_FILE = Path(r"C:\QIH\config\usage_assistants.json")


def _has_rollouts(p: Path) -> bool:
    try:
        return p.is_dir() and any(p.rglob("rollout-*.jsonl"))
    except OSError:
        return False


def _wsl_session_roots() -> list[Path]:
    """Codex homes inside WSL distributions.

    THE HALF THAT WAS NEARLY MISSED: `codex mcp-server` — the binary Claude
    delegates to — runs under WSL, so the rollouts for every MCP delegation are
    written to /home/<user>/.codex/sessions, NOT the Windows profile. Scanning
    only C:\\Users captured Codex Desktop sessions and silently dropped every
    call Claude itself made. Caught 2026-09-20 by making one luna call and
    finding no matching rollout on the Windows side.

    Reached over the \\\\wsl.localhost UNC provider so no `wsl.exe` subprocess
    is needed (the dashboard is a service and must not shell out per request).
    """
    roots: list[Path] = []
    for provider in (r"\\wsl.localhost", r"\\wsl$"):
        base = Path(provider)
        try:
            distros = list(base.iterdir())
        except OSError:
            continue                      # provider unavailable to this account
        for distro in distros:
            try:
                homes = (distro / "home").iterdir()
            except OSError:
                continue
            for home in homes:
                cand = home / ".codex" / "sessions"
                if _has_rollouts(cand):
                    roots.append(cand)
        if roots:
            break                         # one provider spelling is enough
    return roots


def _configured_roots() -> list[Path]:
    """Explicit roots from QI_CODEX_EXTRA_ROOTS or config/usage_assistants.json.

    An escape hatch for the case where UNC discovery fails — most likely when
    the dashboard runs as LocalSystem and cannot see another user's WSL share.
    """
    raw: list[str] = []
    env = os.environ.get("QI_CODEX_EXTRA_ROOTS")
    if env:
        raw += [p for p in env.split(";") if p.strip()]
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        raw += list(cfg.get("codex_extra_roots") or [])
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return [Path(p.strip()) for p in raw if p.strip()]


def codex_session_roots() -> list[Path]:
    """Every directory holding Codex rollout transcripts.

    Two independent hazards, both of which render a confident zero rather than
    an error, and both found live on 2026-09-20:
      1. QI_Dashboard runs as LocalSystem, where Path.home() is
         C:\\WINDOWS\\system32\\config\\systemprofile. Resolution order mirrors
         usage_stats._find_projects_dir for exactly that reason.
      2. The MCP server runs in WSL — see _wsl_session_roots.
    Cross-root duplicates are harmless: _dedup collapses on response_id.
    """
    roots: list[Path] = []

    def _add(p: Path) -> None:
        if _has_rollouts(p) and not any(str(p) == str(r) for r in roots):
            roots.append(p)

    for p in _configured_roots():
        _add(p)
    override = os.environ.get("CODEX_HOME")
    if override:
        _add(Path(override) / "sessions")
    env_home = os.environ.get("USERPROFILE") or str(Path.home())
    _add(Path(env_home) / ".codex" / "sessions")
    users_dir = Path(r"C:\Users")
    try:
        for user in users_dir.iterdir():
            _add(user / ".codex" / "sessions")
    except OSError:
        pass
    for p in _wsl_session_roots():
        _add(p)
    return roots


def codex_sessions_dir() -> Path:
    """The primary Windows-side root. Kept for display; scanning uses
    codex_session_roots(), which also covers WSL."""
    roots = codex_session_roots()
    return roots[0] if roots else Path(
        os.environ.get("USERPROFILE") or str(Path.home())) / ".codex" / "sessions"


def parse_codex_rollout(lines, source: str) -> list[dict]:
    """One event per model response. Reads `usage` only — `turn_token_usage`
    and `thread_token_usage` are running totals and summing them would inflate
    a long thread by its own length."""
    events: list[dict] = []
    turn_models: dict[str, str] = {}
    session_id = ""
    originator = ""
    cwd = ""
    last_model = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        kind = obj.get("type")
        payload = obj.get("payload") or {}
        if not isinstance(payload, dict):
            continue

        if kind == "session_meta":
            session_id = payload.get("session_id") or payload.get("id") or session_id
            originator = payload.get("originator") or originator
            cwd = payload.get("cwd") or cwd
            continue

        if kind == "turn_context":
            model = payload.get("model") or payload.get("model_slug")
            turn_id = payload.get("turn_id")
            if model:
                last_model = model
                if turn_id:
                    turn_models[turn_id] = model
            if payload.get("cwd"):
                cwd = payload["cwd"]
            continue

        if kind != "token_usage_record":
            continue

        usage = payload.get("usage")
        if not isinstance(usage, dict):
            continue
        ts = _parse_ts(obj.get("timestamp"))
        if ts is None:
            continue
        model = turn_models.get(payload.get("turn_id")) or last_model
        split = {
            "input":        int(usage.get("input_tokens") or 0),
            "cached_input": int(usage.get("cached_input_tokens") or 0),
            "cache_write":  int(usage.get("cache_write_input_tokens") or 0),
            "output":       int(usage.get("output_tokens") or 0),
            "reasoning":    int(usage.get("reasoning_output_tokens") or 0),
        }
        if not any(split.values()):
            continue
        events.append(_make_event(
            provider="codex",
            ts=ts,
            model=normalize_model("codex", model),
            split=split,
            session=payload.get("thread_id") or session_id or source,
            project=_project_from_cwd(cwd),
            dedup_key=payload.get("response_id"),
            estimated=False,
            originator=originator,
            tool="",
        ))
    return events


def _make_event(**kw) -> dict:
    split = kw["split"]
    usd, priced, inferred = _cost(kw["provider"], kw["model"], split)
    return {
        "provider":  kw["provider"],
        "ts":        kw["ts"],
        "model":     kw["model"],
        "session":   kw["session"],
        "project":   kw["project"] or "unknown",
        "tokens":    _fresh(split),
        "total":     split["input"] + split["output"] + split.get("cache_write", 0),
        "cache_reads": split["cached_input"],
        "cost":      usd,
        "priced":    priced,
        "inferred":  inferred,
        "estimated": kw["estimated"],
        "originator": kw.get("originator") or "",
        "tool":      kw.get("tool") or "",
        "dedup":     kw.get("dedup_key") or "",
        **split,
    }


def _parse_codex_file(path: Path) -> list[dict]:
    try:
        st = path.stat()
    except OSError:
        return []
    sig = (st.st_mtime_ns, st.st_size)
    key = str(path)
    hit = _FILE_CACHE.get(key)
    if hit and hit["sig"] == sig:
        return hit["events"]
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            events = parse_codex_rollout(fh, path.name)
    except (PermissionError, OSError):
        events = []
    _FILE_CACHE[key] = {"sig": sig, "events": events}
    return events


def codex_events() -> list[dict]:
    out: list[dict] = []
    live: set[str] = set()
    for root in codex_session_roots():
        try:
            paths = list(root.rglob("rollout-*.jsonl"))
        except OSError:
            continue                      # a WSL share can vanish mid-scan
        for path in paths:
            live.add(str(path))
            out.extend(_parse_codex_file(path))
    for gone in [k for k in _FILE_CACHE if k.endswith(".jsonl") and k not in live
                 and ".codex" in k.lower()]:
        _FILE_CACHE.pop(gone, None)
    return out


# ── Gemini: measured token log, with a flagged estimate for older calls ──────
_LOG_LINE = re.compile(
    r"^(?P<ts>\S+)\s+tool=(?P<tool>\S+)\s+model=(?P<model>\S+)\s+"
    r"prompt_chars=(?P<chars>\d+)\s+status=(?P<status>\w+)"
)


def gemini_token_files() -> list[Path]:
    if not GEMINI_DATA_DIR.exists():
        return []
    return sorted(GEMINI_DATA_DIR.glob("tokens_*.jsonl"))


def _parse_gemini_tokens(path: Path) -> list[dict]:
    """Measured rows written by qi_gemini_mcp.py from Google's usageMetadata."""
    try:
        st = path.stat()
    except OSError:
        return []
    sig = (st.st_mtime_ns, st.st_size)
    key = str(path)
    hit = _FILE_CACHE.get(key)
    if hit and hit["sig"] == sig:
        return hit["events"]

    events: list[dict] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                ts = _parse_ts(row.get("ts"))
                if ts is None:
                    continue
                # The two vendors count reasoning differently, verified against
                # their own totals on 2026-09-20:
                #   OpenAI  total = input + output,  reasoning_output_tokens is
                #           a SUBSET of output (36436+169 = 36605 with 15
                #           reasoning) - so Codex's output is already complete.
                #   Google  total = prompt + candidates + thoughts, thoughts is
                #           SEPARATE (7+0+99 = 106) and billed at the output
                #           rate - so it must be added here or a thinking-heavy
                #           call reads as nearly free.
                thoughts = int(row.get("thoughts_tokens") or 0)
                split = {
                    "input":        int(row.get("prompt_tokens") or 0),
                    "cached_input": int(row.get("cached_tokens") or 0),
                    "cache_write":  0,
                    "output":       int(row.get("output_tokens") or 0) + thoughts,
                    "reasoning":    thoughts,
                }
                events.append(_make_event(
                    provider="gemini",
                    ts=ts,
                    model=normalize_model("gemini", row.get("model")),
                    split=split,
                    session=row.get("session") or "gemini-mcp",
                    project=row.get("project") or "trinity",
                    dedup_key=row.get("id") or f"{row.get('ts')}|{row.get('tool')}",
                    estimated=False,
                    originator="qi-gemini-mcp",
                    tool=row.get("tool") or "",
                ))
    except (PermissionError, OSError):
        events = []
    _FILE_CACHE[key] = {"sig": sig, "events": events}
    return events


def _parse_gemini_call_log(measured_days: set[date]) -> list[dict]:
    """Reconstruct calls from the diagnostic log for days with no measured
    token file. prompt_chars/4 is a real estimate, not a measurement, and every
    row it produces carries estimated=True all the way to the dashboard."""
    if not GEMINI_CALL_LOG.exists():
        return []
    events: list[dict] = []
    try:
        with GEMINI_CALL_LOG.open("r", encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh):
                m = _LOG_LINE.match(line.strip())
                if not m:
                    continue
                ts = _parse_ts(m.group("ts"))
                if ts is None:
                    continue
                if _as_local_date(ts) in measured_days:
                    continue          # measured data wins for that day
                if m.group("status") != "ok":
                    continue          # a failed call burned quota, not tokens
                chars = int(m.group("chars"))
                split = _empty_split()
                split["input"] = round(chars / CHARS_PER_TOKEN_EST)
                events.append(_make_event(
                    provider="gemini",
                    ts=ts,
                    model=normalize_model("gemini", m.group("model")),
                    split=split,
                    session="gemini-mcp",
                    project="trinity",
                    dedup_key=f"log:{n}",
                    estimated=True,
                    originator="qi-gemini-mcp",
                    tool=m.group("tool"),
                ))
    except (PermissionError, OSError):
        return []
    return events


def gemini_events() -> list[dict]:
    measured: list[dict] = []
    for path in gemini_token_files():
        measured.extend(_parse_gemini_tokens(path))
    measured_days = {_as_local_date(e["ts"]) for e in measured}
    return measured + _parse_gemini_call_log(measured_days)


# ── Event stream ─────────────────────────────────────────────────────────────
def _dedup(events: list[dict]) -> list[dict]:
    """One row per vendor response id. Codex can replay a response into more
    than one rollout file (a resumed thread re-writes its history); without
    this the resumed portion would be counted twice."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for e in events:
        key = (e["provider"], e["dedup"])
        if e["dedup"] and key in seen:
            continue
        if e["dedup"]:
            seen.add(key)
        out.append(e)
    return out


def _iter_events(force: bool = False) -> list[dict]:
    now = time.time()
    if not force and now - _CACHE["stamp"] < _TTL and _CACHE["events"]:
        return _CACHE["events"]
    events = codex_events() + gemini_events()
    events.sort(key=lambda e: e["ts"])
    events = _dedup(events)
    _CACHE.update(stamp=now, events=events)
    return events


WSL_MIRROR_ROOT = Path(r"C:\QIH\data\codex_wsl\sessions")
WSL_MIRROR_STATE = Path(r"C:\QIH\data\codex_wsl\_sync_state.json")
WSL_MIRROR_STALE_HOURS = 24


def _is_wsl_root(p: Path) -> bool:
    """A root holding Linux-side Codex transcripts: the mirror, or a live UNC
    share if one is ever reachable."""
    s = str(p).lower()
    return s.startswith(str(WSL_MIRROR_ROOT).lower()) or s.startswith("\\\\wsl")


def wsl_mirror_status() -> dict:
    """Age and last result of the WSL→Windows rollout mirror.

    The mirror is the only way the dashboard sees Claude's own Codex
    delegations, and a mirror that quietly stops does not raise anything — the
    ChatGPT column simply stops growing, which looks exactly like a quiet week.
    So its age is reported and the page renders a warning past
    WSL_MIRROR_STALE_HOURS. Freshness of the artifact, not an exit code
    (CLAUDE.md, "Unattended jobs lie").
    """
    try:
        state = json.loads(WSL_MIRROR_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"configured": False, "note": "mirror has never run on this machine"}
    ran = _parse_ts(state.get("finished") or state.get("started"))
    age_h = None
    if ran is not None:
        age_h = round((datetime.now(timezone.utc) - ran).total_seconds() / 3600, 1)
    return {
        "configured": True,
        "last_run": (ran.isoformat(timespec="seconds") if ran else None),
        "age_hours": age_h,
        "stale": (age_h is None or age_h > WSL_MIRROR_STALE_HOURS),
        "files": state.get("remote_files", 0),
        "copied": state.get("copied", 0),
        "failed": state.get("failed", 0),
        "error": state.get("error"),
    }


def available() -> dict:
    """Which legs actually have evidence on this machine. Lets the dashboard
    say 'no Codex transcripts found' instead of silently rendering zeros."""
    evs = _iter_events()
    have = {p: any(e["provider"] == p for e in evs) for p in PROVIDERS}
    roots = codex_session_roots()
    return {
        "codex_wsl_mirror": wsl_mirror_status(),
        "codex_dir":   str(roots[0]) if roots else str(codex_sessions_dir()),
        "codex_roots": [str(r) for r in roots],
        # The MCP server runs in WSL while Codex Desktop writes to the Windows
        # profile. Seeing only one of the two is a half-blind ChatGPT column,
        # so say which kinds of root were actually reached. The WSL side is
        # identified by the mirror/UNC path rather than by sniffing for the
        # substring "wsl", which a user directory could contain by accident.
        "codex_windows_root": any(not _is_wsl_root(r) for r in roots),
        "codex_wsl_root": any(_is_wsl_root(r) for r in roots),
        "codex_found": have["codex"],
        "gemini_measured": bool(gemini_token_files()),
        "gemini_found": have["gemini"],
        "events": len(evs),
    }


# ── Aggregation ──────────────────────────────────────────────────────────────
def _bucket() -> dict:
    return {"tokens": 0, "total": 0, "cache_reads": 0, "cost": 0.0, "calls": 0,
            "input": 0, "output": 0, "reasoning": 0, "sessions": set(),
            "estimated_calls": 0, "inferred_calls": 0, "unpriced_calls": 0}


def _add(b: dict, e: dict) -> None:
    b["tokens"] += e["tokens"]
    b["total"] += e["total"]
    b["cache_reads"] += e["cache_reads"]
    b["cost"] += e["cost"] or 0.0
    b["calls"] += 1
    b["input"] += e["input"]
    b["output"] += e["output"]
    b["reasoning"] += e["reasoning"]
    b["sessions"].add(e["session"])
    if e["estimated"]:
        b["estimated_calls"] += 1
    if e["inferred"]:
        b["inferred_calls"] += 1
    if not e["priced"]:
        b["unpriced_calls"] += 1


def _finish(b: dict, **extra) -> dict:
    out = {k: v for k, v in b.items() if k != "sessions"}
    out["cost_usd"] = round(b["cost"], 2)
    out.pop("cost", None)
    out["sessions"] = len(b["sessions"])
    out.update(extra)
    return out


def _window(days: int) -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=days - 1), today


def range_stats(start: date, end: date) -> dict:
    """Totals for an inclusive [start, end] local-date window, per provider and
    combined."""
    per = {p: _bucket() for p in PROVIDERS}
    for e in _iter_events():
        d = _as_local_date(e["ts"])
        if start <= d <= end:
            _add(per[e["provider"]], e)
    combined = _bucket()
    for p in PROVIDERS:
        for k in ("tokens", "total", "cache_reads", "cost", "calls", "input",
                  "output", "reasoning", "estimated_calls", "inferred_calls",
                  "unpriced_calls"):
            combined[k] += per[p][k]
        combined["sessions"] |= per[p]["sessions"]
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "providers": {p: _finish(per[p], provider=p, label=PROVIDER_LABEL[p]) for p in PROVIDERS},
        **_finish(combined),
    }


def totals(days: int = 30) -> dict:
    r = range_stats(*_window(days))
    r["days"] = days
    return r


def totals_since(start: date) -> dict:
    return range_stats(start, date.today())


def today() -> dict:
    t = date.today()
    return range_stats(t, t)


def daily(days: int = 30) -> list[dict]:
    """One row per local day, with a per-provider split for the stacked chart."""
    start, end = _window(days)
    buckets: dict[date, dict] = defaultdict(lambda: {p: _bucket() for p in PROVIDERS})
    for e in _iter_events():
        d = _as_local_date(e["ts"])
        if start <= d <= end:
            _add(buckets[d][e["provider"]], e)
    rows = []
    for i in range(days):
        d = start + timedelta(days=i)
        per = buckets.get(d) or {p: _bucket() for p in PROVIDERS}
        row = {"date": d.isoformat(), "tokens": 0, "cost_usd": 0.0, "calls": 0}
        for p in PROVIDERS:
            f = _finish(per[p])
            row[f"{p}_tokens"] = f["tokens"]
            row[f"{p}_cost_usd"] = f["cost_usd"]
            row[f"{p}_calls"] = f["calls"]
            row["tokens"] += f["tokens"]
            row["cost_usd"] += f["cost_usd"]
            row["calls"] += f["calls"]
        row["cost_usd"] = round(row["cost_usd"], 2)
        rows.append(row)
    return rows


def _group(days: int, key) -> list[dict]:
    start, end = _window(days)
    buckets: dict = defaultdict(_bucket)
    meta: dict = {}
    for e in _iter_events():
        d = _as_local_date(e["ts"])
        if not (start <= d <= end):
            continue
        k = key(e)
        _add(buckets[k], e)
        meta.setdefault(k, e["provider"])
    rows = [_finish(b, key=k, provider=meta.get(k, "")) for k, b in buckets.items()]
    rows.sort(key=lambda r: (-r["cost_usd"], -r["tokens"]))
    return rows


def by_model(days: int = 30) -> list[dict]:
    rows = _group(days, lambda e: (e["provider"], e["model"]))
    for r in rows:
        r["provider"], r["model"] = r.pop("key")
        r["label"] = PROVIDER_LABEL[r["provider"]]
    return rows


def by_provider(days: int = 30) -> list[dict]:
    rows = _group(days, lambda e: e["provider"])
    for r in rows:
        r["provider"] = r.pop("key")
        r["label"] = PROVIDER_LABEL.get(r["provider"], r["provider"])
        sub = subscription(r["provider"])
        r["plan"] = sub.get("plan", "")
        r["plan_usd_per_month"] = sub.get("usd_per_month", 0.0)
    return rows


def by_project(days: int = 30) -> list[dict]:
    rows = _group(days, lambda e: e["project"])
    for r in rows:
        r["project"] = r.pop("key")
    return rows


def by_originator(days: int = 30) -> list[dict]:
    """Who drove the call. Separates Claude's MCP delegations from the sessions
    Renne runs himself in Codex Desktop — the two spend the same quota but mean
    very different things when the weekly cap gets tight."""
    rows = _group(days, lambda e: (e["provider"], e["originator"] or "unknown"))
    for r in rows:
        r["provider"], r["originator"] = r.pop("key")
    return rows


# ── Quota — the number Renne actually acts on ────────────────────────────────
def _gemini_daily_cap() -> int:
    try:
        cfg = json.loads(GEMINI_CONFIG.read_text(encoding="utf-8"))
        return int(cfg.get("daily_cap") or 200)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 200


def _gemini_calls_today() -> int:
    """The MCP's own counter — the one that actually enforces the cap. Every
    ladder attempt counts, including the failures, so it can exceed the number
    of successful calls in the token log. Trust this one for 'how close am I'."""
    path = GEMINI_DATA_DIR / f"usage_{date.today().isoformat()}.json"
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("count", 0))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 0


def quota() -> dict:
    """Live quota pressure per leg.

    Codex's Plus allowance is published as a MESSAGE range per model per
    rolling 5-hour window, metered by tokens — OpenAI does not expose the
    remaining balance, so this reports consumption (messages + tokens in the
    window) against the published range rather than inventing a percentage.
    """
    evs = _iter_events()
    now = datetime.now(timezone.utc)
    win5 = now - timedelta(hours=5)
    win7 = now - timedelta(days=7)

    codex_5h: dict = defaultdict(lambda: {"calls": 0, "tokens": 0})
    codex_week = {"calls": 0, "tokens": 0}
    for e in evs:
        if e["provider"] != "codex":
            continue
        ts = e["ts"] if e["ts"].tzinfo else e["ts"].replace(tzinfo=timezone.utc)
        if ts >= win7:
            codex_week["calls"] += 1
            codex_week["tokens"] += e["tokens"]
        if ts >= win5:
            b = codex_5h[e["model"]]
            b["calls"] += 1
            b["tokens"] += e["tokens"]

    cap = _gemini_daily_cap()
    used = _gemini_calls_today()
    return {
        "codex": {
            "window_hours": 5,
            "by_model": [{"model": m, **v} for m, v in sorted(
                codex_5h.items(), key=lambda kv: -kv[1]["tokens"])],
            "window_calls": sum(v["calls"] for v in codex_5h.values()),
            "window_tokens": sum(v["tokens"] for v in codex_5h.values()),
            "week_calls": codex_week["calls"],
            "week_tokens": codex_week["tokens"],
            "note": "ChatGPT Plus meters a rolling 5-hour window and a weekly cap by "
                    "token volume. OpenAI publishes no remaining-balance API, so this is "
                    "consumption, not headroom.",
        },
        "gemini": {
            "calls_today": used,
            "daily_cap": cap,
            "pct": round(used / cap * 100, 1) if cap else 0.0,
            "note": "Self-imposed cap enforced by qi_gemini_mcp.py. Every ladder attempt "
                    "counts, successes and failures alike.",
        },
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
def _main() -> None:
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"sources: {json.dumps(available(), indent=2)}")
    print(f"\nprices v{pricing_version()}\n{pricing_text()}\n")
    t = totals(days)
    print(f"── last {days} days ──")
    for p in PROVIDERS:
        r = t["providers"][p]
        print(f"  {r['label']:<16} {r['calls']:>6} calls  {r['tokens']:>12,} fresh tok  "
              f"{r['cache_reads']:>12,} cached  ${r['cost_usd']:>10,.2f} api-equiv"
              + (f"  ({r['estimated_calls']} estimated)" if r["estimated_calls"] else ""))
    print(f"  {'TOTAL':<16} {t['calls']:>6} calls  {t['tokens']:>12,} fresh tok  "
          f"{t['cache_reads']:>12,} cached  ${t['cost_usd']:>10,.2f}")
    print("\n── by model ──")
    for r in by_model(days):
        flag = " [inferred price]" if r["inferred_calls"] else ""
        flag += " [UNPRICED]" if r["unpriced_calls"] else ""
        print(f"  {r['model']:<24} {r['calls']:>5} calls  {r['tokens']:>12,} tok  "
              f"${r['cost_usd']:>9,.2f}{flag}")
    print("\n── quota ──")
    print(json.dumps(quota(), indent=2))


if __name__ == "__main__":
    _main()
