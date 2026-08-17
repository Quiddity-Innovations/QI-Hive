# -*- coding: utf-8 -*-
"""Fill the gaps in project_readiness.json for projects the dashboard showed as "—".

project_readiness.json is owner-set ("Edit freely; dashboard reads this live"),
so this does NOT overwrite anything the owner already set. It only adds entries
for projects that had none, and marks each as derived so it is obvious which
figures are a starting point rather than an owner judgement.

Derivation: from the project's own status_features_dev.json —
    pct = round(100 * (live + 0.5*partial) / total_features)

Two honesty guards:
  * A project whose INTRO carries only a placeholder feature (e.g. a single
    "Source tree" entry) would score 100%. Those are flagged as stubs and given
    a low pct with an explicit label, because an unwritten inventory is not
    evidence of completeness.
  * A project with no INTRO at all gets no invented number; it gets an
    explicit not-applicable note explaining why.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

import project_status as PS

READINESS = Path(r"C:\QIH\data\project_readiness.json")
STUB_THRESHOLD = 3          # fewer real features than this => treat as a stub
THIN_INVENTORY = 6          # below this, a high pct reflects sparse docs, not delivery

# Projects where a delivery-readiness percentage is genuinely not applicable.
NOT_APPLICABLE = {
    "headroom": (
        "Readiness percentage is not applicable to Headroom. It is not a "
        "standalone QI application but a utility that lives inside Claude "
        "Manager at C:\\APPS\\CLAUDE\\Tools, so it has no INTRO folder, no service, "
        "no port allocation and no independent delivery milestone. Its status "
        "is carried by its parent project (claude_manager). If Headroom is "
        "ever promoted to a standalone project, register it in "
        "qi_registry.json with its own path and seed an INTRO folder; a "
        "readiness figure becomes meaningful at that point."
    ),
}


def derive(intro: Path) -> tuple[int, str, str] | None:
    """Return (pct, label, basis) from status_features_dev.json, or None."""
    f = intro / "status_features_dev.json"
    if not f.exists():
        return None
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return None
    live = partial = planned = 0
    for cat in data if isinstance(data, list) else []:
        for feat in cat.get("features", []):
            s = str(feat.get("status", "")).lower()
            if s == "live":
                live += 1
            elif s == "partial":
                partial += 1
            else:
                planned += 1
    total = live + partial + planned
    if not total:
        return None
    if total < STUB_THRESHOLD:
        return (10, "Inventory not written up",
                f"INTRO carries only {total} placeholder feature(s); the real "
                f"feature inventory has not been documented yet, so completeness "
                f"cannot be inferred from it.")
    pct = round(100 * (live + 0.5 * partial) / total)
    basis = (f"{live} live, {partial} partial, {planned} planned "
             f"across {total} documented features in status_features_dev.json.")
    if total < THIN_INVENTORY:
        # A handful of features all marked live reads as 100% complete, which
        # says more about how little was written down than about the product.
        return (pct, "Derived — thin inventory",
                basis + f" Only {total} features are documented, so this figure "
                        f"reflects a sparse inventory rather than a verified "
                        f"delivery state; treat it as a ceiling, not a measure.")
    return (pct, "Derived from feature status", basis)


def main() -> None:
    doc = json.loads(READINESS.read_text(encoding="utf-8"))
    entries = {pid: (name, intro) for pid, name, intro in PS._all_project_entries()}

    added, skipped = [], []
    for pid, (name, intro) in sorted(entries.items()):
        if pid in doc:
            skipped.append(pid)
            continue
        if pid in NOT_APPLICABLE:
            doc[pid] = {"pct": None, "label": "Not applicable",
                        "not_applicable": True, "note": NOT_APPLICABLE[pid],
                        "derived": True}
            added.append((pid, "n/a", "Not applicable"))
            continue
        d = derive(intro)
        if d is None:
            doc[pid] = {"pct": None, "label": "Unknown — no feature inventory",
                        "derived": True,
                        "note": (f"No status_features_dev.json found under {intro}. "
                                 f"Seed the INTRO folder to make readiness measurable.")}
            added.append((pid, "—", "no feature inventory"))
            continue
        pct, label, basis = d
        doc[pid] = {"pct": pct, "label": label, "derived": True, "note": basis}
        added.append((pid, pct, label))

    doc["_meta"] = (doc.get("_meta") if isinstance(doc.get("_meta"), str) else "") or ""
    READINESS.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"already owner-set (untouched): {len(skipped)}")
    print(f"added: {len(added)}")
    for pid, pct, label in added:
        print(f"  {pid:<22} {str(pct):<5} {label}")


if __name__ == "__main__":
    main()
