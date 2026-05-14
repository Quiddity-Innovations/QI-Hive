# -*- coding: utf-8 -*-
"""
Deterministic verdict engine for QI_HiveInspectorDrain.

No LLM. Reads mechanical check results from an envelope and returns a
(verdict, confidence, reasons) triple.

verdict is one of:
  "pass"     — auto-approved; will POST to Brain API
  "fail"     — auto-rejected; will POST to Brain API
  "escalate" — ambiguous; envelope left in place for human review

The Brain API only accepts pass/fail on the inspector_verdict endpoint,
so escalate is handled by the dispatcher (leave envelope, do not POST).
"""

# Critical checks whose failure causes an immediate fail verdict.
_CRITICAL_CHECKS = {"size_limits", "git_diff_check"}


def compute_verdict(envelope: dict) -> tuple[str, float, list[str]]:
    """Return (verdict, confidence, reasons) from a pending_review envelope.

    Args:
        envelope: JSON-decoded envelope dict from C:/QIH/inbox/hive_inspector/

    Returns:
        verdict:    "pass" | "fail" | "escalate"
        confidence: float in [0.0, 1.0]
        reasons:    list of human-readable strings explaining the decision
    """
    # The runner writes the key as "mechanical_checks" (not "checks").
    checks = envelope.get("mechanical_checks") or envelope.get("checks") or []

    if not checks:
        return ("escalate", 0.5, ["no mechanical checks present in envelope"])

    passed = [c for c in checks if c.get("pass")]
    failed = [c for c in checks if not c.get("pass")]

    # Any critical check failure → immediate fail, confidence 0.
    critical_failed = [c for c in failed if c.get("check") in _CRITICAL_CHECKS]
    if critical_failed:
        reasons = [
            f"critical check failed: {c['check']} — {c.get('error')}"
            for c in critical_failed
        ]
        return ("fail", 0.0, reasons)

    # All checks passed → confident pass.
    if not failed:
        return ("pass", 1.0, ["all mechanical checks passed"])

    # Non-critical failures (e.g. md_links warnings) — score by ratio.
    confidence = len(passed) / max(1, len(checks))
    warning_details = [f"{c['check']}: {c.get('error')}" for c in failed]

    if confidence >= 0.95:
        return (
            "pass",
            confidence,
            ["mechanical pass with minor warnings", *warning_details],
        )
    elif confidence <= 0.40:
        return ("fail", confidence, warning_details)
    else:
        return (
            "escalate",
            confidence,
            ["mixed checks — human review required", *warning_details],
        )
