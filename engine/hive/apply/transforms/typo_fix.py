# -*- coding: utf-8 -*-
"""Apply a typo fix. Spec: {file: str, find: str, replace: str, occurrences: int}."""
from pathlib import Path
from typing import TypedDict


class TypoSpec(TypedDict):
    file: str         # relative path within project root
    find: str         # exact string to replace
    replace: str      # replacement
    occurrences: int  # expected number; 0 = any


def validate(spec: dict) -> list[str]:
    errors = []
    for k in ("file", "find", "replace"):
        if not isinstance(spec.get(k), str) or not spec.get(k):
            errors.append(f"missing or invalid '{k}'")
    if "find" in spec and "replace" in spec and spec["find"] == spec["replace"]:
        errors.append("find and replace are identical")
    return errors


def apply(project_root: Path, spec: TypoSpec) -> dict:
    """Apply the typo fix. Returns {applied, count, before_size, after_size} or {applied, error}."""
    target = project_root / spec["file"]
    if not target.exists() or not target.is_file():
        return {"applied": False, "error": "target file missing"}
    text = target.read_text(encoding="utf-8")
    new = text.replace(spec["find"], spec["replace"])
    if new == text:
        return {"applied": False, "error": "find string not found in file"}
    count = text.count(spec["find"])
    expected = spec.get("occurrences", 0)
    if expected and count != expected:
        return {"applied": False, "error": f"expected {expected} occurrences, found {count}"}
    target.write_text(new, encoding="utf-8")
    return {"applied": True, "count": count, "before_size": len(text), "after_size": len(new)}
