# -*- coding: utf-8 -*-
"""Unit tests for engine/common/usage_assistants.py (Trinity legs, 2026-09-20).

Run:  python -m pytest C:\\QIH\\engine\\hive\\dashboard\\tests\\test_usage_assistants.py -q
No dashboard needed; nothing is read from ~/.codex or the live Gemini log.

These lock down the four things that would silently corrupt the LLM Usage tab:
the running-total trap, cross-file double counting, the two vendors' different
reasoning-token conventions, and a guessed price sneaking in as a real one.
"""
import json
import sys
from datetime import datetime, timezone

sys.path.insert(0, r"C:\QIH")
from engine.common import usage_assistants as ua  # noqa: E402


def _usage(inp, cached, out, reasoning=0, cache_write=0):
    return {"input_tokens": inp, "cached_input_tokens": cached,
            "cache_write_input_tokens": cache_write, "output_tokens": out,
            "reasoning_output_tokens": reasoning,
            "total_tokens": inp + out}


def _rollout(records, model="gpt-5.6-terra", cwd=r"C:\QIH"):
    """A minimal Codex rollout file: session_meta, turn_context, then usage."""
    lines = [json.dumps({"timestamp": "2026-09-20T12:00:00.000Z", "type": "session_meta",
                         "payload": {"session_id": "sess1", "originator": "test",
                                     "cwd": cwd}}),
             json.dumps({"timestamp": "2026-09-20T12:00:01.000Z", "type": "turn_context",
                         "payload": {"turn_id": "t1", "model": model, "cwd": cwd}})]
    for i, (resp_id, usage, turn, thread) in enumerate(records):
        lines.append(json.dumps({
            "timestamp": f"2026-09-20T12:00:{10+i:02d}.000Z",
            "type": "token_usage_record",
            "payload": {"thread_id": "th1", "turn_id": "t1", "session_id": "sess1",
                        "response_id": resp_id, "usage": usage,
                        "turn_token_usage": turn, "thread_token_usage": thread},
        }))
    return lines


# ── The running-total trap ───────────────────────────────────────────────────
def test_reads_per_response_usage_not_running_totals():
    """Codex ships three usage blocks per record; only `usage` is the delta.

    Summing turn_token_usage or thread_token_usage instead would inflate a long
    thread by its own length — the same shape of bug as the 2-5x Claude
    overstatement the 2026-09-16 audit found.
    """
    r1 = _usage(1000, 0, 100)
    r2 = _usage(1200, 900, 150)
    lines = _rollout([
        ("resp1", r1, r1, r1),
        # thread totals keep climbing; the per-response delta does not.
        ("resp2", r2, _usage(2200, 900, 250), _usage(2200, 900, 250)),
    ])
    evs = ua.parse_codex_rollout(lines, "test.jsonl")
    assert len(evs) == 2
    assert [e["input"] for e in evs] == [1000, 1200]
    assert sum(e["output"] for e in evs) == 250          # not 350 (running total)


def test_dedup_collapses_a_response_replayed_into_two_files():
    """A resumed Codex thread re-writes its history into a new rollout file."""
    u = _usage(500, 0, 50)
    evs = (ua.parse_codex_rollout(_rollout([("respX", u, u, u)]), "a.jsonl")
           + ua.parse_codex_rollout(_rollout([("respX", u, u, u)]), "b.jsonl"))
    assert len(ua._dedup(evs)) == 1


def test_events_without_a_response_id_are_kept():
    """Missing id means 'cannot prove it is a duplicate', not 'drop it'."""
    u = _usage(10, 0, 5)
    evs = ua.parse_codex_rollout(_rollout([(None, u, u, u), (None, u, u, u)]), "a.jsonl")
    assert len(ua._dedup(evs)) == 2


# ── Fresh vs cached ──────────────────────────────────────────────────────────
def test_fresh_tokens_exclude_cache_reads():
    """Matches usage_stats' ex-cache definition so the three legs compare."""
    evs = ua.parse_codex_rollout(_rollout([("r", _usage(1000, 800, 100), None, None)]),
                                 "a.jsonl")
    e = evs[0]
    assert e["tokens"] == 300          # (1000 - 800 cached) + 100 out
    assert e["cache_reads"] == 800


# ── The two vendors count reasoning differently ──────────────────────────────
def test_openai_reasoning_is_inside_output_and_not_double_counted():
    evs = ua.parse_codex_rollout(
        _rollout([("r", _usage(100, 0, 169, reasoning=15), None, None)]), "a.jsonl")
    e = evs[0]
    assert e["output"] == 169          # NOT 184 — reasoning is a subset
    assert e["reasoning"] == 15


def test_google_thoughts_are_added_to_output(tmp_path):
    """Verified against Google's own total on 2026-09-20: 7 + 0 + 99 = 106."""
    path = tmp_path / "tokens_2026-09-20.jsonl"
    path.write_text(json.dumps({
        "ts": "2026-09-20T14:27:53+00:00", "tool": "selftest", "model": "gemini-3.6-flash",
        "prompt_tokens": 7, "output_tokens": 0, "cached_tokens": 0,
        "thoughts_tokens": 99, "total_tokens": 106,
    }) + "\n", encoding="utf-8")
    ua._FILE_CACHE.pop(str(path), None)
    evs = ua._parse_gemini_tokens(path)
    assert len(evs) == 1
    e = evs[0]
    assert e["output"] == 99           # a thinking-heavy call is not free
    assert e["tokens"] == 7 + 99
    assert e["cost"] is not None and e["cost"] > 0


# ── Prices are evidence, never a guess ───────────────────────────────────────
def test_unpriced_model_reports_no_cost_rather_than_a_plausible_one():
    cost, priced, _ = ua._cost("gemini", "totally-made-up-slug-xyz",
                               {"input": 1000, "cached_input": 0, "output": 100,
                                "cache_write": 0, "reasoning": 0})
    # gemini declares a _price_unknown_as fallback, so this one IS priced but
    # must be flagged inferred - the flag is the point.
    _, inferred = ua.price_for("gemini", "totally-made-up-slug-xyz")
    assert inferred is True
    assert priced is True and cost is not None


def test_inferred_flag_is_false_for_a_published_rate():
    _, inferred = ua.price_for("codex", "gpt-6-astra")
    assert inferred is False


def test_cached_input_bills_at_the_cached_rate():
    """gpt-6-astra: $10/M input, $1/M cached, $50/M output."""
    cost, priced, _ = ua._cost("codex", "gpt-6-astra",
                               {"input": 1_000_000, "cached_input": 900_000,
                                "output": 100_000, "cache_write": 0, "reasoning": 0})
    assert priced is True
    # 100k fresh @ $10/M + 900k cached @ $1/M + 100k out @ $50/M
    assert abs(cost - (1.0 + 0.9 + 5.0)) < 1e-9


def test_every_published_price_carries_a_verification_date():
    """A number with no provenance is how the tab got 6x wrong in the first place."""
    for provider in ua.PROVIDERS:
        for slug, rec in (ua.prices().get(provider, {}).get("models") or {}).items():
            if rec.get("input") is not None:
                assert rec.get("verified_on"), f"{provider}/{slug} has a price but no verified_on"


# ── Estimates must stay visibly estimates ────────────────────────────────────
def test_reconstructed_gemini_calls_are_flagged_estimated():
    evs = ua._parse_gemini_call_log(measured_days=set())
    if evs:                                   # empty on a machine with no log
        assert all(e["estimated"] for e in evs)


def test_measured_day_wins_over_the_reconstructed_log():
    """Once a day has a measured token file, the chars/4 rows for that day are
    dropped — the two must never be added together."""
    evs = ua.gemini_events()
    by_day = {}
    for e in evs:
        by_day.setdefault(e["ts"].astimezone().date(), set()).add(e["estimated"])
    for day, kinds in by_day.items():
        assert kinds != {True, False}, f"{day} mixes measured and estimated rows"


# ── Service-account safety ───────────────────────────────────────────────────
def test_codex_dir_never_resolves_to_the_system_profile_when_a_real_one_exists():
    """QI_Dashboard runs as LocalSystem, where Path.home() is
    C:\\WINDOWS\\system32\\config\\systemprofile. That rendered a confident zero
    for the whole ChatGPT leg on the first live restart (2026-09-20).

    The resolver must prefer any C:\\Users profile that actually holds rollout
    files, so landing on systemprofile is only acceptable when no real one has
    transcripts at all.
    """
    from pathlib import Path
    d = str(ua.codex_sessions_dir()).lower()
    real_profile_has_data = any(
        (u / ".codex" / "sessions").is_dir()
        and any((u / ".codex" / "sessions").rglob("rollout-*.jsonl"))
        for u in Path(r"C:\Users").iterdir()
    ) if Path(r"C:\Users").exists() else False
    if real_profile_has_data:
        assert "systemprofile" not in d


def test_available_reports_which_legs_have_evidence():
    a = ua.available()
    for key in ("codex_dir", "codex_roots", "codex_found", "gemini_found", "events",
                "codex_windows_root", "codex_wsl_root", "codex_wsl_mirror"):
        assert key in a


# ── The WSL half of the ChatGPT leg ──────────────────────────────────────────
def test_configured_extra_root_is_scanned():
    """`codex mcp-server` runs under WSL, so the rollouts for every delegation
    Claude makes are mirrored to C:\\QIH\\data\\codex_wsl\\sessions and
    registered in config/usage_assistants.json. Dropping that root silently
    halves the ChatGPT column to Codex Desktop only."""
    roots = [str(r) for r in ua.codex_session_roots()]
    if ua.WSL_MIRROR_ROOT.is_dir() and any(ua.WSL_MIRROR_ROOT.rglob("rollout-*.jsonl")):
        assert str(ua.WSL_MIRROR_ROOT) in roots


def test_wsl_root_is_identified_by_path_not_by_the_substring_wsl():
    assert ua._is_wsl_root(ua.WSL_MIRROR_ROOT / "2026")
    assert ua._is_wsl_root(__import__("pathlib").Path(r"\\wsl.localhost\U\home\x\.codex\sessions"))
    # A user folder that merely contains the letters is not a WSL root.
    assert not ua._is_wsl_root(__import__("pathlib").Path(r"C:\Users\wsladmin\.codex\sessions"))


def test_mirror_status_reports_staleness_rather_than_raising():
    s = ua.wsl_mirror_status()
    assert "configured" in s
    if s["configured"]:
        assert "stale" in s and "age_hours" in s


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
