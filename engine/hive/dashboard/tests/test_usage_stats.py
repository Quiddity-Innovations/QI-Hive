# -*- coding: utf-8 -*-
"""Unit tests for engine/common/usage_stats.py v2 (audit 2026-09-16).

Run:  python -m pytest C:\\QIH\\engine\\hive\\dashboard\\tests\\test_usage_stats.py -q
No dashboard needed; nothing is read from ~/.claude.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\QIH")
from engine.common import usage_stats as us  # noqa: E402

USAGE = {"input_tokens": 100, "output_tokens": 50, "cache_read_input_tokens": 1000,
         "cache_creation_input_tokens": 200,
         "cache_creation": {"ephemeral_5m_input_tokens": 200, "ephemeral_1h_input_tokens": 0}}


def _line(mid, model="claude-opus-5", ts="2026-09-16T12:00:00Z", cwd=r"C:\QIH", usage=USAGE):
    return json.dumps({"type": "assistant", "timestamp": ts, "cwd": cwd, "sessionId": "s1",
                       "requestId": "req_" + mid,
                       "message": {"id": mid, "model": model, "usage": usage}})


def test_same_message_counted_once():
    # Claude Code writes one line per content block; all three carry the same id.
    lines = [_line("m1"), _line("m1"), _line("m1"), _line("m2")]
    evs = us.dedup(us.parse_lines(lines, "C--QIH"))
    assert len(evs) == 2
    assert sorted(e["mid"] for e in evs) == ["m1", "m2"]


def test_events_without_id_are_kept():
    d = json.loads(_line("x")); d["message"].pop("id"); d.pop("requestId")
    lines = [json.dumps(d), json.dumps(d)]
    assert len(us.dedup(us.parse_lines(lines, "C--QIH"))) == 2


def test_opus5_price_is_5_25():
    assert us.price_for("claude-opus-5") == (5.0, 25.0, 0.10)
    assert us.price_for("claude-opus-5-20260401")[0] == 5.0


def test_fable51_cache_read_is_2_5_percent():
    assert us.price_for("claude-fable-5-1") == (10.0, 50.0, 0.025)
    assert us.price_for("claude-fable-5")[2] == 0.10


def test_legacy_ids_keep_legacy_prices():
    assert us.price_for("claude-opus-4-1-20250805") == (15.0, 75.0, 0.10)
    assert us.price_for("claude-sonnet-4-6")[0] == 3.0
    assert us.price_for("claude-haiku-4-5-20251001") == (1.0, 5.0, 0.10)


def test_unknown_model_uses_family_fallback():
    assert us.price_for("claude-sonnet-9")[:2] == us.MODEL_PRICING["sonnet"]
    assert us.price_for("gpt-x")[:2] == us.MODEL_PRICING["other"]


def test_cost_formula():
    # opus-5: 100 in @5 + 50 out @25 + 1000 cache-read @0.5 + 200 cw5 @6.25  (per 1M)
    expected = (100 * 5 + 50 * 25 + 1000 * 0.5 + 200 * 6.25) / 1e6
    assert abs(us._cost(USAGE, "claude-opus-5") - expected) < 1e-12


def test_tokens_exclude_cache_reads():
    assert us._tokens(USAGE) == 100 + 50 + 200
    assert us._cache_reads(USAGE) == 1000


def test_project_attribution():
    assert us._project_from_cwd(r"C:\QIH\engine\hive", "C--QIH") == "qi_hive"
    assert us._project_from_cwd(r"C:\CLAUDE", "subagents") == "claude_manager"
    assert us._project_from_cwd(r"C:\Retirement Analyzer\.claude\worktrees\quizzical-zhukovsky-cb1be1",
                                "C--Retirement-Analyzer") == "retirementanalyzer"
    assert us._project_from_cwd(r"D:\Dev\MediaStudio", "D--Dev-MediaStudio") == "mediastudio"
    assert us._project_from_cwd(None, "C--APPS-MapSnap") == "mapsnap"
    assert us._project_from_cwd(r"C:\Nowhere\Special", "C--Nowhere-Special") == "unknown"


def test_pricing_text_matches_table():
    txt = us.pricing_text()
    assert "opus-5 $5/$25" in txt and "fable-5-1 $10/$50" in txt and us.PRICING_VERSION in txt
