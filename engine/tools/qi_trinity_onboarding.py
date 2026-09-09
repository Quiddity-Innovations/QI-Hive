"""
QI Trinity — Assistant Onboarding Generator

Builds the three-layer onboarding briefing described in
C:\\QIH\\shared\\documentation\\plans\\QI_Trinity_Onboarding_Design_2026-09-08.md
(section 2): an ecosystem-wide L1 brief, per-project L2 briefs, and an
AGENTS.md drop for Codex working directories.

Python 3.11, stdlib only. Never calls MCP tools — Brain is read over plain
HTTP at 127.0.0.1:9011.

Subcommands:
  --ecosystem                      write C:\\QIH\\trinity\\ONBOARDING.md (L1)
  --project <id>                   write C:\\QIH\\trinity\\briefs\\<id>.md (L2)
  --all                            --ecosystem, then --project for every registry id
  --agents-md <dir> --project <id> drop AGENTS.md = L1 + L2 + footer into <dir>
  --force                          ignore the 24h L2 cache
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\QIH\engine\common")
from qi_handoff import scan_secrets  # noqa: E402  (path inserted above)

REGISTRY_PATH = Path(r"C:\QIH\ecosystem\qi_registry.json")
PRINCIPLES_PATH = Path(r"C:\QIH\ecosystem\QI_Architecture_Principles.md")
ECOSYSTEM_DIR = Path(r"C:\QIH\ecosystem")
TRINITY_DIR = Path(r"C:\QIH\trinity")
ONBOARDING_PATH = TRINITY_DIR / "ONBOARDING.md"
BRIEFS_DIR = TRINITY_DIR / "briefs"

BRAIN_BASE = "http://127.0.0.1:9011"
BRAIN_TIMEOUT = 3

RULE_KEYWORDS = [
    "never", "always", "rule", "must", "do not", "don't",
    "regra", "nunca", "sempre", "não", "congelad", "frozen", "proibid",
]

L2_CACHE_HOURS = 24
L2_LINE_CAP = 150
ENTRY_POINT_EXTS = (".py", ".js", ".html", ".bat")
ENTRY_POINT_CAP = 25


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def registry_hash() -> str:
    return hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()[:12]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _redact_candidate_line(line: str) -> str:
    """Neutralize a single candidate line before it ever reaches the
    assembled document. CLAUDE.md files legitimately mention env-var
    NAMES like GEMINI_API_KEY next to rule words like 'Nunca' — that is
    not a leaked secret, but qi_handoff.scan_secrets() cannot tell the
    difference from inside a single line. Filtering per-line here means
    the final whole-document gate (below) stays a real backstop instead
    of a near-certain false-positive block on ordinary project rules."""
    hits = scan_secrets(line)
    if not hits:
        return line
    # Deliberately does not name the matched pattern (e.g. "api_key") in the
    # placeholder text — doing so would itself match the same pattern on the
    # final whole-document redaction pass below.
    return "[line redacted by qi_handoff secret-pattern filter]"


def sanitize_lines(lines: list[str]) -> list[str]:
    """Line-level pre-filter applied to every assembled document (not just
    CLAUDE.md excerpts) — registry `notes`/`description` text can just as
    easily mention an env-var NAME (e.g. EXA_API_KEY) in prose. See
    _redact_candidate_line for why this runs before the final gate."""
    return [_redact_candidate_line(line) for line in lines]


def write_with_redaction(path: Path, text: str) -> bool:
    """Final whole-document gate. Returns True if written, False (and
    prints line numbers, writes nothing) if a secret pattern hit."""
    hits = scan_secrets(text)
    if hits:
        print(f"REDACTION FAILED — {path} NOT written. Secret patterns found:")
        for line_no, name in hits:
            print(f"  line {line_no}: {name}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def brain_context(project_id: str, token_budget: int = 1500) -> dict | None:
    url = f"{BRAIN_BASE}/api/context"
    payload = json.dumps({"project_id": project_id, "token_budget": token_budget}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=BRAIN_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# L1 — Ecosystem brief
# ─────────────────────────────────────────────────────────────────────────────

def extract_law_titles(principles_text: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"^### (Law \d+ .+)$", principles_text, re.MULTILINE)]


def one_line_purpose(proj: dict, max_len: int = 90) -> str:
    text = proj.get("description") or proj.get("notes") or proj.get("family_notes") or ""
    text = text.replace("\n", " ").strip()
    if not text:
        return "-"
    first = text.split(". ")[0].rstrip(". ").strip()
    first = first.replace("|", "/")
    if len(first) > max_len:
        first = first[: max_len - 1].rstrip() + "\u2026"
    return first


def short_phase(proj: dict, max_len: int = 30) -> str:
    phase = (proj.get("phase") or "-").replace("\n", " ").strip()
    phase = phase.replace("|", "/")
    if not phase:
        return "-"
    if len(phase) > max_len:
        phase = phase[: max_len - 1].rstrip() + "\u2026"
    return phase


def compact_ports(proj: dict) -> str:
    ports = proj.get("ports") or {}
    bits = []
    for role, info in ports.items():
        if not isinstance(info, dict):
            continue
        current = info.get("current")
        if current in (None, ""):
            continue
        bits.append(f"{role} {current}")
    return " \u00b7 ".join(bits) if bits else "\u2014"


ONBOARDING_LINE_CAP = 120


def _render_project_table(projects: list[dict], purpose_max_len: int) -> list[str]:
    lines = ["| id | path | status | phase | ports | purpose |", "|---|---|---|---|---|---|"]
    for proj in projects:
        pid = proj.get("id", "-")
        path = (proj.get("path") or "-").replace("|", "/")
        status = (proj.get("status") or "-").replace("|", "/")
        phase = short_phase(proj)
        ports = compact_ports(proj)
        purpose = one_line_purpose(proj, max_len=purpose_max_len)
        lines.append(f"| {pid} | {path} | {status} | {phase} | {ports} | {purpose} |")
    return lines


def build_ecosystem_brief(registry: dict) -> str:
    projects = registry["projects"]
    laws = extract_law_titles(PRINCIPLES_PATH.read_text(encoding="utf-8"))

    lines = []
    lines.append("# QI Ecosystem — Assistant Onboarding (L1)")
    lines.append("")
    lines.append(f"_Generated {now_iso()} \u00b7 qi_registry.json sha256[:12] = {registry_hash()}_")
    lines.append("")
    lines.append("## Who QI is")
    lines.append("")
    lines.append("- Quiddity Innovations (QI) — owner Renne Santiago, sole developer + AI ambassador.")
    lines.append(f"- {len(projects)} registered projects sharing one machine, ports, git, and a converging future.")
    lines.append("- Two run tiers: `C:\\APPS` is the gold build/run tier; `D:\\Dev` is the packaged-out copy.")
    lines.append("- Port blocks are per-project (e.g. Maia 8100-8199, NEXUS 8300-8399, QI Hive 9000-9099) —")
    lines.append("  never pick an adjacent port; check `C:\\QIH\\ecosystem\\qi_registry.json` `port_strategy`.")
    lines.append("- `C:\\QIH\\ecosystem\\qi_registry.json` is the single source of truth for ports, services,")
    lines.append("  status and relationships across every project.")
    lines.append("")
    lines.append("## The Six Laws (QI_Architecture_Principles.md)")
    lines.append("")
    for law in laws:
        lines.append(f"- {law}")
    lines.append("")
    lines.append("## Assistant non-negotiables")
    lines.append("")
    lines.append("- Read-only, unless a worktree is explicitly named for you to work in.")
    lines.append("- Never touch `C:\\QIH\\ecosystem`, any folder literally named `secrets`, NSSM services,")
    lines.append("  ports, or `.claude.json`.")
    lines.append("- Answer in the exact format the task requests.")
    lines.append("- If you don't know something, say UNKNOWN — never guess.")
    lines.append("- If a rule in this brief conflicts with the task, stop and say which rule conflicts.")
    lines.append("- Assistants never call, route through, or depend on a QI application (NEXUS, Maia,")
    lines.append("  OpenClaw…); apps are context, not tools — the only tools you may call are the MCP")
    lines.append("  servers you were given (qi-registry, qi-brain).")
    lines.append("")
    lines.append("## Project index")
    lines.append("")

    header_len = len(lines)
    table = _render_project_table(projects, purpose_max_len=90)
    if header_len + len(table) + 1 > ONBOARDING_LINE_CAP:
        table = _render_project_table(projects, purpose_max_len=70)
    if header_len + len(table) + 1 > ONBOARDING_LINE_CAP:
        keep = max(ONBOARDING_LINE_CAP - header_len - 2, 2)
        table = table[:keep] + [f"...(truncated — cap {ONBOARDING_LINE_CAP} lines)"]
    lines.extend(table)
    lines.append("")
    return "\n".join(sanitize_lines(lines))


def cmd_ecosystem(_args) -> bool:
    registry = load_registry()
    text = build_ecosystem_brief(registry)
    ok = write_with_redaction(ONBOARDING_PATH, text)
    if ok:
        print(str(ONBOARDING_PATH))
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# L2 — Project brief
# ─────────────────────────────────────────────────────────────────────────────

def extract_claude_md_rules(claude_md_path: Path) -> list[str]:
    if not claude_md_path.exists():
        return []
    raw_lines = claude_md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    keep = set()
    for i, line in enumerate(raw_lines):
        if line.lstrip().startswith("#"):
            keep.add(i)
            continue
        low = line.lower()
        if any(k in low for k in RULE_KEYWORDS):
            keep.add(i)
            keep.add(i + 1)
            keep.add(i + 2)
    idxs = sorted(i for i in keep if 0 <= i < len(raw_lines))
    return [_redact_candidate_line(raw_lines[i]) for i in idxs]


def entry_points(project_path: Path) -> list[str]:
    if not project_path.exists() or not project_path.is_dir():
        return []
    names = sorted(
        p.name for p in project_path.iterdir()
        if p.is_file() and p.suffix.lower() in ENTRY_POINT_EXTS
    )
    return names[:ENTRY_POINT_CAP]


def build_project_brief(pid: str, proj: dict) -> str:
    status = proj.get("status", "unknown")
    flagged = any(k in status.lower() for k in ("frozen", "blocked"))

    lines = []
    lines.append(f"# {proj.get('name', pid)} ({pid}) — L2 brief")
    if flagged:
        lines.append("")
        lines.append(f"**{status.upper()}**")
    lines.append("")
    lines.append(f"_Generated {now_iso()}_")
    lines.append("")

    lines.append("## Registry facts")
    lines.append(f"- Path: `{proj.get('path', '-')}`")
    lines.append(f"- Status: {status}")
    if proj.get("phase"):
        lines.append(f"- Phase: {proj['phase']}")
    ports = proj.get("ports") or {}
    if ports:
        bits = ", ".join(f"{k}:{v.get('current')}" for k, v in ports.items())
        lines.append(f"- Ports: {bits}")
    services = proj.get("services") or []
    if services:
        bits = []
        for s in services:
            if isinstance(s, dict):
                bits.append(s.get("nssm_name") or s.get("name") or "?")
            else:
                bits.append(str(s))
        lines.append(f"- Services: {', '.join(bits)}")
    notes = proj.get("notes") or proj.get("family_notes") or ""
    if notes:
        lines.append(f"- Notes: {notes}")
    lines.append("")

    lines.append("## Brain")
    ctx = brain_context(pid)
    if ctx is None:
        lines.append("- Brain offline or unreachable — skipped.")
    else:
        state = ctx.get("current_state") or {}
        if state:
            lines.append(f"- Current state: status={state.get('status', '-')}, phase={state.get('phase', '-')}")
            if state.get("summary"):
                lines.append(f"  {state['summary']}")
        else:
            lines.append("- No current_state recorded.")
        # /api/context ranks project-scoped decisions first but still backfills
        # with ecosystem/global ones to fill the token budget — filter to this
        # project's own decisions only, keep the (already recency-sorted) order.
        all_decisions = ctx.get("recent_decisions") or []
        project_decisions = [d for d in all_decisions if d.get("project_id") == pid][:3]
        if project_decisions:
            lines.append("- Last decisions:")
            for d in project_decisions:
                date = (d.get("recorded_at") or "")[:10]
                lines.append(f"  - {d.get('title', '')} ({date})")
        else:
            lines.append("- No project-scoped decisions recorded.")
    lines.append("")

    lines.append("## CLAUDE.md rules")
    claude_path = Path(proj.get("path", "")) / "CLAUDE.md"
    rule_lines = extract_claude_md_rules(claude_path)
    if rule_lines:
        lines.extend(rule_lines)
    else:
        lines.append("- No CLAUDE.md found (or no matching rule/heading lines).")
    lines.append("")

    lines.append("## Entry points")
    eps = entry_points(Path(proj.get("path", "")))
    lines.append(", ".join(f"`{e}`" for e in eps) if eps else "- none found")
    lines.append("")

    lines = sanitize_lines(lines)
    if len(lines) > L2_LINE_CAP:
        lines = lines[: L2_LINE_CAP - 1] + [f"...(truncated \u2014 cap {L2_LINE_CAP} lines)"]
    return "\n".join(lines)


def generate_project_brief(pid: str, registry: dict, force: bool = False) -> bool:
    by_id = {p["id"]: p for p in registry["projects"]}
    if pid not in by_id:
        print(f"Unknown project id: {pid}")
        return False

    brief_path = BRIEFS_DIR / f"{pid}.md"
    if brief_path.exists() and not force:
        age_hours = (datetime.now().timestamp() - brief_path.stat().st_mtime) / 3600
        if age_hours < L2_CACHE_HOURS:
            print(f"{brief_path} — cached ({age_hours:.1f}h old, < {L2_CACHE_HOURS}h), skipping")
            return True

    text = build_project_brief(pid, by_id[pid])
    ok = write_with_redaction(brief_path, text)
    if ok:
        print(str(brief_path))
    return ok


def cmd_project(args) -> bool:
    registry = load_registry()
    return generate_project_brief(args.project, registry, force=args.force)


# ─────────────────────────────────────────────────────────────────────────────
# --all
# ─────────────────────────────────────────────────────────────────────────────

def cmd_all(args) -> bool:
    registry = load_registry()
    ok = write_with_redaction(ONBOARDING_PATH, build_ecosystem_brief(registry))
    if ok:
        print(str(ONBOARDING_PATH))
    all_ok = ok
    for proj in registry["projects"]:
        pid = proj["id"]
        all_ok = generate_project_brief(pid, registry, force=args.force) and all_ok
    return all_ok


# ─────────────────────────────────────────────────────────────────────────────
# --agents-md
# ─────────────────────────────────────────────────────────────────────────────

def _forbidden_reason(target_dir: Path, registry: dict) -> str | None:
    resolved = str(target_dir.resolve()).lower().rstrip("\\")

    eco_resolved = str(ECOSYSTEM_DIR.resolve()).lower().rstrip("\\")
    if resolved == eco_resolved or resolved.startswith(eco_resolved + "\\"):
        return "target is under C:\\QIH\\ecosystem"

    if any(part.lower() == "secrets" for part in target_dir.parts):
        return "target is under a folder literally named 'secrets'"

    for proj in registry["projects"]:
        proj_path = proj.get("path")
        if not proj_path:
            continue
        proj_resolved = str(Path(proj_path).resolve()).lower().rstrip("\\")
        if resolved == proj_resolved:
            return (
                f"target IS the project ROOT for '{proj['id']}' — "
                "point --agents-md at a worktree or a _trinity subfolder instead"
            )
    return None


def cmd_agents_md(args) -> bool:
    registry = load_registry()
    target_dir = Path(args.agents_md)

    reason = _forbidden_reason(target_dir, registry)
    if reason:
        print(f"REFUSED — {reason}")
        return False

    by_id = {p["id"]: p for p in registry["projects"]}
    if args.project not in by_id:
        print(f"Unknown project id: {args.project}")
        return False

    if not ONBOARDING_PATH.exists():
        write_with_redaction(ONBOARDING_PATH, build_ecosystem_brief(registry))
    if not generate_project_brief(args.project, registry, force=args.force):
        return False

    l1 = ONBOARDING_PATH.read_text(encoding="utf-8")
    brief_path = BRIEFS_DIR / f"{args.project}.md"
    l2 = brief_path.read_text(encoding="utf-8")

    text = (
        l1.rstrip("\n") + "\n\n---\n\n"
        + l2.rstrip("\n") + "\n\n---\n\n"
        + "Task follows in the prompt. Reply in the requested format.\n"
    )

    target_dir.mkdir(parents=True, exist_ok=True)
    ok = write_with_redaction(target_dir / "AGENTS.md", text)
    if ok:
        print(str(target_dir / "AGENTS.md"))
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QI Trinity assistant onboarding generator")
    parser.add_argument("--ecosystem", action="store_true", help="write L1 ONBOARDING.md")
    parser.add_argument("--project", metavar="ID", help="write L2 brief for one project id")
    parser.add_argument("--all", action="store_true", help="L1 + L2 for every registry id")
    parser.add_argument("--agents-md", metavar="DIR", help="drop AGENTS.md into DIR (needs --project)")
    parser.add_argument("--force", action="store_true", help="ignore the 24h L2 cache")
    args = parser.parse_args()

    if args.agents_md:
        if not args.project:
            parser.error("--agents-md requires --project")
        ok = cmd_agents_md(args)
        sys.exit(0 if ok else 2)

    if args.all:
        ok = cmd_all(args)
        sys.exit(0 if ok else 1)

    ran = False
    ok = True
    if args.ecosystem:
        ok = cmd_ecosystem(args) and ok
        ran = True
    if args.project:
        ok = cmd_project(args) and ok
        ran = True

    if not ran:
        parser.error("nothing to do — pass --ecosystem, --project <id>, --all, or --agents-md <dir> --project <id>")

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
