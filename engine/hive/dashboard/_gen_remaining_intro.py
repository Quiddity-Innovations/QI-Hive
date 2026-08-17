# -*- coding: utf-8 -*-
"""Close the last INTRO gaps found by _audit_tabs.py.

Three projects render an empty "Code Explained" tab (connector, playdeck,
retirementanalyzer) and Headroom renders all seven tabs empty because it has
no INTRO folder at all.

Snippets are extracted verbatim from live source at generation time, so a tab
can never describe code that has since changed. Headroom gets an explicit
not-applicable write-up on every tab instead of an invented feature inventory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

MAX_LINES = 20


def grab(path: str, start: int, end: int) -> str:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    chunk = lines[start - 1:end]
    while chunk and not chunk[-1].strip():
        chunk.pop()
    if len(chunk) > MAX_LINES:
        chunk = chunk[:MAX_LINES] + ["    # ..."]
    return "\n".join(chunk)


JOBS = [
    # ── QI Connector ────────────────────────────────────────────────────
    (r"C:\APPS\QIP\Connector\INTRO", {
        "intro": (
            "QI Connector is a remote MCP server that exposes the QI ecosystem "
            "to Claude as a set of callable tools. It holds no data of its own "
            "— every tool is a thin, bounded proxy onto the Brain API or the "
            "registry, which is what keeps the public surface small and "
            "auditable."),
        "sections": [
            ("Authentication", [
                (r"C:\APPS\QIP\Connector\api\main.py", 54, 66,
                 "Self-provisioning bearer + path tokens",
                 "Capability-URL access control",
                 "Both tokens are generated once with secrets.token_urlsafe(32) "
                 "and persisted under secrets/, so a fresh deployment secures "
                 "itself with no manual key ceremony and no secret in source "
                 "control. The path token is embedded in the connector URL, "
                 "which makes that URL itself a credential — it must be "
                 "treated as a password and rotated by deleting the token file "
                 "and restarting."),
            ]),
            ("Brain Proxy", [
                (r"C:\APPS\QIP\Connector\api\main.py", 79, 84,
                 "Single bounded call into the Brain API",
                 "Every tool is a thin proxy",
                 "All Brain-backed tools funnel through this one helper: a "
                 "short-timeout httpx POST that raises on any non-2xx. "
                 "Centralising it means timeout and error behaviour are "
                 "uniform across the whole tool surface rather than "
                 "reimplemented per tool."),
                (r"C:\APPS\QIP\Connector\api\main.py", 74, 78,
                 "Response clipping",
                 "Bounded payloads back to the model",
                 "Tool results are clipped before being returned. An unbounded "
                 "Brain response would otherwise flow straight into the "
                 "model's context window and could blow it out in a single "
                 "call."),
            ]),
        ]}),

    # ── Retirement Analyzer ─────────────────────────────────────────────
    (r"C:\APPS\Retirement Analyzer\INTRO", {
        "intro": (
            "Retirement Analyzer ingests a Fidelity positions export and turns "
            "it into an allocation, concentration and rebalancing view. The "
            "design problem is that brokerage CSVs are messy and inconsistent, "
            "so most of the real work is tolerant parsing and classification "
            "rather than arithmetic."),
        "sections": [
            ("Classification", [
                (r"C:\APPS\Retirement Analyzer\shared\analyzer.py", 37, 51,
                 "Asset-class classification",
                 "Allocation by asset class",
                 "Each holding is bucketed into Cash / Bond / International "
                 "Equity / US Equity / Real Estate / Other using a known-symbol "
                 "set first, then keyword matching on the description. The "
                 "order matters: cash and bonds are tested before equity so a "
                 "money-market fund is never miscounted as stock. Anything "
                 "unrecognised falls to Other rather than being silently "
                 "dropped, so totals always reconcile."),
            ]),
            ("Parsing", [
                (r"C:\APPS\Retirement Analyzer\shared\analyzer.py", 127, 146,
                 "Tolerant Fidelity CSV parser",
                 "Fidelity CSV import",
                 "Fidelity exports carry disclaimer rows, blank lines and "
                 "currency/percentage formatting that standard CSV parsing "
                 "chokes on. This walks rows defensively and skips what it "
                 "cannot interpret instead of aborting the import, so one bad "
                 "line never costs the user the whole file."),
            ]),
        ]}),

    # ── PlayDeck ────────────────────────────────────────────────────────
    (r"C:\PlayDeck\INTRO", {
        "intro": (
            "PlayDeck is a local media browser and player built on FastAPI with "
            "yt-dlp and ffmpeg as external tools. Because those two are the "
            "things most likely to be missing or outdated on a given machine, "
            "the health surface is built around proving they are actually "
            "present rather than assuming it."),
        "sections": [
            ("Health & Diagnostics", [
                (r"C:\PlayDeck\api\main.py", 95, 109,
                 "Deep health probe",
                 "Dependency-aware health check",
                 "The flat /health endpoint only proves the process is up. This "
                 "deep probe additionally reports the resolved yt-dlp version, "
                 "whether the ffmpeg binary actually exists on disk, and live "
                 "counts for cached streams, library files, favourites and "
                 "subscriptions. Importing yt-dlp inside a try/except means a "
                 "missing dependency is reported as a diagnostic string rather "
                 "than taking the endpoint down — the check still answers when "
                 "the thing it checks is broken, which is exactly when you "
                 "need it."),
            ]),
        ]}),
]

# Headroom: not a standalone project. Every tab says so, in its own words.
HEADROOM_WHY = (
    "Headroom is not a standalone QI application, so this tab is not "
    "applicable to it.\n\n"
    "Headroom is a utility that lives inside Claude Manager at "
    "`C:\\APPS\\CLAUDE\\Tools`, alongside the other maintenance scripts there. It has "
    "no source tree of its own, no service, no port allocation in the QI port "
    "registry and no independent delivery milestone — which is why it has no "
    "INTRO folder and why the dashboard shows `n/a` rather than a readiness "
    "percentage for it.\n\n"
    "Its status is carried by its parent project, **Claude Manager** "
    "(`claude_manager`). If you are looking for the information this tab would "
    "normally show, that is where it lives.\n\n"
    "If Headroom is ever promoted to a standalone project, register it in "
    "`qi_registry.json` with its own path and seed an INTRO folder; these tabs "
    "become meaningful at that point."
)


def write_headroom() -> list[str]:
    intro = Path(r"C:\APPS\CLAUDE\Tools\INTRO")
    intro.mkdir(parents=True, exist_ok=True)
    written = []

    (intro / "status_intro.md").write_text(
        "# Headroom\n\n" + HEADROOM_WHY + "\n", encoding="utf-8")
    written.append("status_intro.md")

    note = [{"category": "Not applicable",
             "features": [{"name": "Not a standalone project",
                           "file": "C:\\APPS\\CLAUDE\\Tools",
                           "status": "planned",
                           "detail": HEADROOM_WHY.replace("\n\n", " ")}]}]
    for f in ("status_features_business.json", "status_features_dev.json"):
        (intro / f).write_text(json.dumps(note, indent=2, ensure_ascii=False),
                               encoding="utf-8")
        written.append(f)

    (intro / "status_code.json").write_text(json.dumps(
        {"intro": HEADROOM_WHY.replace("\n\n", " "), "sections": []},
        indent=2, ensure_ascii=False), encoding="utf-8")
    written.append("status_code.json")

    (intro / "status_future.json").write_text(json.dumps(
        {"intro": HEADROOM_WHY.replace("\n\n", " "), "items": []},
        indent=2, ensure_ascii=False), encoding="utf-8")
    written.append("status_future.json")

    (intro / "status_techstack.json").write_text(json.dumps(
        {"table": [], "descriptions": {"Not applicable": HEADROOM_WHY.replace("\n\n", " ")}},
        indent=2, ensure_ascii=False), encoding="utf-8")
    written.append("status_techstack.json")

    (intro / "status_documentation.json").write_text(json.dumps(
        {"intro": HEADROOM_WHY.replace("\n\n", " "), "documents": []},
        indent=2, ensure_ascii=False), encoding="utf-8")
    written.append("status_documentation.json")
    return written


def main() -> None:
    for intro_dir, spec in JOBS:
        d = Path(intro_dir)
        d.mkdir(parents=True, exist_ok=True)
        sections = []
        for category, items in spec["sections"]:
            snippets = []
            for path, a, b, title, feature, explanation in items:
                if not Path(path).exists():
                    print(f"  SKIP missing source {path}")
                    continue
                snippets.append({
                    "title": title, "feature": feature,
                    "file": f"{Path(path).name} :: lines {a}-{b}",
                    "language": "python",
                    "code": grab(path, a, b),
                    "explanation": explanation,
                })
            if snippets:
                sections.append({"category": category, "snippets": snippets})
        out = d / "status_code.json"
        out.write_text(json.dumps({"intro": spec["intro"], "sections": sections},
                                  indent=2, ensure_ascii=False), encoding="utf-8")
        n = sum(len(s["snippets"]) for s in sections)
        print(f"wrote {out}  ({len(sections)} sections, {n} snippets)")

    w = write_headroom()
    print(f"wrote C:\\APPS\\CLAUDE\\Tools\\INTRO  ({len(w)} files: {', '.join(w)})")


if __name__ == "__main__":
    main()
