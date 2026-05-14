# -*- coding: utf-8 -*-
"""Post-diff mechanical checks. No LLM. Returns {pass: bool, checks: [...], errors: [...]}."""
import ast
import re
import subprocess
from pathlib import Path


def check_python_syntax(file: Path) -> tuple[bool, str | None]:
    if file.suffix != ".py":
        return True, None
    try:
        ast.parse(file.read_text(encoding="utf-8"))
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"


def check_markdown_links(file: Path, project_root: Path) -> tuple[bool, list[str]]:
    if file.suffix.lower() not in {".md", ".markdown"}:
        return True, []
    text = file.read_text(encoding="utf-8")
    broken = []
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        url = m.group(2)
        if url.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (file.parent / url).resolve()
        try:
            target.relative_to(project_root.resolve())
        except ValueError:
            broken.append(f"link escapes project root: {url}")
            continue
        if not target.exists():
            broken.append(f"broken link: {url}")
    return len(broken) == 0, broken


def check_git_diff(worktree: Path) -> tuple[bool, str | None]:
    r = subprocess.run(
        ["git", "diff", "--check"],
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return False, r.stdout + r.stderr
    return True, None


def check_size_limits(worktree: Path, max_files: int = 1, max_lines: int = 40) -> tuple[bool, str | None]:
    r = subprocess.run(
        ["git", "diff", "--numstat"],
        cwd=worktree,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return False, f"git diff failed: {r.stderr}"
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if len(lines) > max_files:
        return False, f"changed {len(lines)} files (max {max_files})"
    total = 0
    for l in lines:
        parts = l.split("\t")
        if len(parts) >= 2:
            try:
                total += int(parts[0]) + int(parts[1])
            except ValueError:
                pass
    if total > max_lines:
        return False, f"changed {total} lines (max {max_lines})"
    return True, None


def run_all(worktree: Path, changed_files: list[Path], project_root: Path) -> dict:
    """Run all mechanical checks. Returns {pass: bool, checks: list, errors: list}."""
    checks = []
    errors = []

    for f in changed_files:
        ok, err = check_python_syntax(f)
        checks.append({"file": str(f), "check": "py_syntax", "pass": ok, "error": err})
        if not ok:
            errors.append(err)

        ok, broken = check_markdown_links(f, project_root)
        checks.append({"file": str(f), "check": "md_links", "pass": ok, "error": broken or None})
        if not ok:
            errors.extend(broken)

    ok, err = check_git_diff(worktree)
    checks.append({"file": "*", "check": "git_diff_check", "pass": ok, "error": err})
    if not ok:
        errors.append(err)

    ok, err = check_size_limits(worktree)
    checks.append({"file": "*", "check": "size_limits", "pass": ok, "error": err})
    if not ok:
        errors.append(err)

    return {"pass": len(errors) == 0, "checks": checks, "errors": errors}
