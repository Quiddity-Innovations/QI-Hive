# -*- coding: utf-8 -*-
"""
QI Brain — Feature Propagation Engine.

When a feature is logged in any project, this engine:
1. Fetches all active projects except the source
2. For each target, calls qwen3:8b (via Ollama) to evaluate relevance
3. Stores evaluation results in feature_evaluations table
4. Marks the feature as propagated

Evaluation prompt contract per Supplement A I-03.
Historical pattern injection per Supplement A I-09.
"""
from __future__ import annotations
import asyncio
import json
import re
import time
from typing import Optional

from core.db import open_brain_db
from core.providers.factory import ProviderFactory

# ── Constants ─────────────────────────────────────────────────────────────────
EVAL_AGENT_ID = "system"
MAX_HISTORY   = 5      # I-09: last N evaluations fed into prompt
MAX_RETRIES   = 1      # one retry on bad JSON

# ── Prompt template (I-03) ────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are evaluating whether a software feature from one project is relevant to another. "
    "Output MUST be valid JSON matching this schema exactly:\n"
    '{"relevance_score": float 0.0-1.0, "recommendation": "adopt"|"adapt"|"skip"|"discuss", '
    '"reasoning": "string max 200 chars", "confidence": float 0.0-1.0}\n'
    "Return ONLY the JSON object, no prose, no markdown, no code block."
)


def _build_eval_prompt(
    source_id: str, source_tagline: str,
    target_id: str, target_tagline: str,
    feature_name: str, feature_desc: str, feature_domain: str,
    history: list[dict],
) -> str:
    lines = [
        f"Source project: {source_id} — {source_tagline}",
        f"Target project: {target_id} — {target_tagline}",
        f"Feature: {feature_name}",
        f"Feature description: {feature_desc}",
        f"Feature domain: {feature_domain}",
    ]
    if history:
        lines.append(f"\nHISTORICAL PATTERN for {target_id} (last {len(history)} evaluations):")
        for h in history:
            short_reason = (h.get("reasoning") or "")[:80]
            lines.append(f'  - Feature "{h["feature_name"]}" ({h["domain"]}) → {h["recommendation"]} ({short_reason})')
        lines.append("Use this pattern only as soft context; do not let it override the current feature's merits.")
    lines.append("\nDecide if the target project should adopt, adapt, skip, or discuss this feature.")
    lines.append("Return ONLY the JSON object.")
    return "\n".join(lines)


def _parse_eval_response(raw: str) -> Optional[dict]:
    """Parse and validate LLM response. Returns None if invalid."""
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    # Validate required fields
    score = data.get("relevance_score")
    rec   = data.get("recommendation")
    if not isinstance(score, (int, float)) or rec not in ("adopt", "adapt", "skip", "discuss"):
        return None
    data["relevance_score"] = float(score)
    data["confidence"]      = float(data.get("confidence", 1.0))
    data["reasoning"]       = str(data.get("reasoning", ""))[:200]
    return data


async def _evaluate_one(
    feature: dict,
    source_project: dict,
    target_project: dict,
    eval_model: str,
    history: list[dict],
) -> dict:
    """Evaluate one feature for one target project. Returns evaluation dict."""
    provider = ProviderFactory.from_db(f"ollama_{eval_model.replace(':', '_').replace('.', '_')}")

    prompt = _build_eval_prompt(
        source_id=source_project["project_id"],
        source_tagline=source_project.get("tagline") or "",
        target_id=target_project["project_id"],
        target_tagline=target_project.get("tagline") or "",
        feature_name=feature["name"],
        feature_desc=feature["description"],
        feature_domain=feature["domain"],
        history=history,
    )

    result = await provider.generate(prompt, system_prompt=_SYSTEM_PROMPT)

    parsed = _parse_eval_response(result.text) if result.ok else None

    # One retry on parse failure (I-03)
    if parsed is None and result.ok:
        retry_prompt = (
            "Your last response was not valid JSON. "
            "Return ONLY the JSON object with fields: relevance_score, recommendation, reasoning, confidence.\n\n"
            + prompt
        )
        result2 = await provider.generate(retry_prompt, system_prompt=_SYSTEM_PROMPT)
        parsed = _parse_eval_response(result2.text) if result2.ok else None

    if parsed is None:
        # Fallback: store discuss/low confidence
        parsed = {
            "relevance_score": 0.0,
            "recommendation":  "discuss",
            "reasoning":       "LLM evaluation failed — review manually",
            "confidence":      0.0,
        }

    return {
        "feature_id":      feature["feature_id"],
        "target_project":  target_project["project_id"],
        "agent_id":        EVAL_AGENT_ID,
        "relevance_score": parsed["relevance_score"],
        "recommendation":  parsed["recommendation"],
        "reasoning":       parsed["reasoning"],
        "confidence":      parsed["confidence"],
        "eval_model":      eval_model,
    }


async def propagate_feature(feature_id: int) -> list[dict]:
    """
    Run the propagation engine for a single feature.

    Args:
        feature_id: ID in the features table.

    Returns:
        List of evaluation dicts stored (one per target project).
    """
    with open_brain_db() as conn:
        feature = conn.execute(
            "SELECT * FROM features WHERE feature_id = ?", (feature_id,)
        ).fetchone()
        if not feature:
            return []

        feature = dict(feature)

        source_project = conn.execute(
            "SELECT * FROM projects WHERE project_id = ?", (feature["source_project"],)
        ).fetchone()
        if not source_project:
            return []
        source_project = dict(source_project)

        target_projects = conn.execute(
            "SELECT * FROM projects WHERE active = 1 AND project_id != ?",
            (feature["source_project"],)
        ).fetchall()
        target_projects = [dict(r) for r in target_projects]

        eval_model_row = conn.execute(
            "SELECT value FROM brain_config WHERE key = 'eval_model'"
        ).fetchone()
        eval_model = eval_model_row["value"] if eval_model_row else "qwen3:8b"

    if not target_projects:
        return []

    # Gather history per target (I-09)
    results = []
    for target in target_projects:
        with open_brain_db() as conn:
            history_rows = conn.execute(
                """
                SELECT fe.recommendation, fe.reasoning, f.name as feature_name, f.domain
                FROM feature_evaluations fe
                JOIN features f ON f.feature_id = fe.feature_id
                WHERE fe.target_project = ?
                ORDER BY fe.evaluated_at DESC
                LIMIT ?
                """,
                (target["project_id"], MAX_HISTORY)
            ).fetchall()
        history = [dict(r) for r in history_rows]

        eval_dict = await _evaluate_one(feature, source_project, target, eval_model, history)
        results.append(eval_dict)

    # Store all results
    with open_brain_db() as conn:
        for ev in results:
            conn.execute(
                """
                INSERT INTO feature_evaluations
                    (feature_id, target_project, agent_id, relevance_score,
                     recommendation, reasoning, confidence, eval_model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ev["feature_id"], ev["target_project"], ev["agent_id"],
                 ev["relevance_score"], ev["recommendation"], ev["reasoning"],
                 ev["confidence"], ev["eval_model"])
            )
        conn.execute(
            "UPDATE features SET propagated = 1 WHERE feature_id = ?", (feature_id,)
        )
        conn.commit()

    return results


async def propagate_all_pending() -> dict:
    """Run propagation for all features not yet propagated. Returns summary."""
    with open_brain_db() as conn:
        pending = conn.execute(
            "SELECT feature_id FROM features WHERE propagated = 0"
        ).fetchall()

    feature_ids = [r["feature_id"] for r in pending]
    if not feature_ids:
        return {"propagated": 0, "evaluations": 0}

    total_evals = 0
    for fid in feature_ids:
        evals = await propagate_feature(fid)
        total_evals += len(evals)

    return {"propagated": len(feature_ids), "evaluations": total_evals}
