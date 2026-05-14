# -*- coding: utf-8 -*-
"""Append a line to a .gitignore file if not already present.

Spec: {file: str, line: str}
  file  — relative path within project root; defaults to '.gitignore'.
  line  — the pattern line to add (e.g. '__pycache__/' or '*.db').

Dedup is case-sensitive. Comments (lines starting with #) and blank lines
in the existing file are ignored when checking for duplicates.
"""
from pathlib import Path


def validate(spec: dict) -> list[str]:
    errors = []
    file_val = spec.get("file", ".gitignore")
    line_val = spec.get("line")
    if not isinstance(file_val, str) or not file_val:
        errors.append("missing or invalid 'file'")
    elif not file_val.endswith(".gitignore"):
        errors.append("file must end with '.gitignore'")
    if not isinstance(line_val, str) or not line_val.strip():
        errors.append("missing or invalid 'line'")
    return errors


def apply(project_root: Path, spec: dict) -> dict:
    """Append line to the .gitignore if not already present.

    Returns {applied, reason} or {applied, error}.
    """
    rel = spec.get("file", ".gitignore")
    line = spec["line"].rstrip("\n")

    target = project_root / rel

    if not target.suffix == "" and not str(target).endswith(".gitignore"):
        return {"applied": False, "error": "file must end with '.gitignore'"}

    # Create the file if it doesn't exist yet (valid: new project without one)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(line + "\n", encoding="utf-8")
        return {"applied": True, "reason": "file created with line"}

    if not target.is_file():
        return {"applied": False, "error": "target path exists but is not a file"}

    text = target.read_text(encoding="utf-8")
    existing_patterns = {
        l.strip()
        for l in text.splitlines()
        if l.strip() and not l.strip().startswith("#")
    }

    if line in existing_patterns:
        return {"applied": False, "error": f"line already present: {line!r}"}

    # Ensure we append on a fresh line
    separator = "" if text.endswith("\n") or text == "" else "\n"
    target.write_text(text + separator + line + "\n", encoding="utf-8")
    return {"applied": True, "reason": "line appended"}
