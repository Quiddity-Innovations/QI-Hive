# -*- coding: utf-8 -*-
"""Correct a broken markdown link. Spec: {file: str, broken_link: str, corrected_link: str}.

Only operates on .md files that live under a docs-family folder.
Docs folders recognised: docs/, documentation/, doc/, shared/documentation/.
"""
from pathlib import Path


_DOCS_FOLDER_NAMES = {"docs", "documentation", "doc"}


def _is_docs_path(file_path: Path) -> bool:
    """Return True if any ancestor folder name matches a docs-family name."""
    for part in file_path.parts:
        if part.lower() in _DOCS_FOLDER_NAMES:
            return True
    return False


def validate(spec: dict) -> list[str]:
    errors = []
    for k in ("file", "broken_link", "corrected_link"):
        if not isinstance(spec.get(k), str) or not spec.get(k):
            errors.append(f"missing or invalid '{k}'")
    if errors:
        return errors
    if not spec["file"].endswith(".md"):
        errors.append("file must be a .md file")
    if spec.get("broken_link") == spec.get("corrected_link"):
        errors.append("broken_link and corrected_link are identical")
    return errors


def apply(project_root: Path, spec: dict) -> dict:
    """Replace broken_link with corrected_link inside the .md file.

    Returns {applied, count, before_size, after_size} or {applied, error}.
    """
    rel = spec["file"]
    target = project_root / rel

    if not target.exists() or not target.is_file():
        return {"applied": False, "error": "target file missing"}

    if target.suffix.lower() != ".md":
        return {"applied": False, "error": "file is not a .md file"}

    # Resolve relative to project_root so we can check ancestors
    try:
        rel_path = target.resolve().relative_to(project_root.resolve())
    except ValueError:
        return {"applied": False, "error": "file is outside project root"}

    if not _is_docs_path(rel_path):
        return {"applied": False, "error": "file is not under a docs folder (docs/, documentation/, doc/)"}

    text = target.read_text(encoding="utf-8")
    broken = spec["broken_link"]
    corrected = spec["corrected_link"]

    if broken not in text:
        return {"applied": False, "error": "broken_link not found in file"}

    count = text.count(broken)
    new = text.replace(broken, corrected)
    target.write_text(new, encoding="utf-8")
    return {"applied": True, "count": count, "before_size": len(text), "after_size": len(new)}
