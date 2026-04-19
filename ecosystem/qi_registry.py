"""
Quiddity Innovations — Ecosystem Registry
A Python module any QI project can import to get port, service,
and relationship info for the entire ecosystem.

Usage:
    from qi_registry import QI
    print(QI.port("maia", "api"))          # 8001
    print(QI.port("nexus", "ui"))          # 7880
    print(QI.cors_origins())               # list of all project URLs for CORS
    print(QI.project("nexus"))             # full project dict
    print(QI.relationships("maia"))        # all relationships for maia
"""
import json
import os
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent / "qi_registry.json"

with open(_REGISTRY_PATH, "r", encoding="utf-8") as _f:
    _DATA = json.load(_f)

_PROJECTS = {p["id"]: p for p in _DATA["projects"]}


class QI:
    """Static access to the QI ecosystem registry."""

    @staticmethod
    def project(project_id: str) -> dict:
        """Return full project entry. Raises KeyError if not found."""
        return _PROJECTS[project_id]

    @staticmethod
    def port(project_id: str, service: str = "api") -> int | None:
        """
        Return the current port for a project service.
        service: "api" | "ui" | "gateway" | any key in project["ports"]
        """
        proj = _PROJECTS.get(project_id, {})
        ports = proj.get("ports", {})
        entry = ports.get(service, {})
        return entry.get("current")

    @staticmethod
    def url(project_id: str, service: str = "api") -> str | None:
        """Return http://127.0.0.1:<port> for a project service."""
        p = QI.port(project_id, service)
        return f"http://127.0.0.1:{p}" if p else None

    @staticmethod
    def cors_origins() -> list[str]:
        """Return all project service URLs — use for FastAPI CORS allow_origins."""
        origins = []
        for proj in _PROJECTS.values():
            for service_key, service_val in proj.get("ports", {}).items():
                p = service_val.get("current")
                if p:
                    origins.append(f"http://localhost:{p}")
                    origins.append(f"http://127.0.0.1:{p}")
        return list(set(origins))

    @staticmethod
    def all_projects() -> list[str]:
        """Return list of all project IDs."""
        return list(_PROJECTS.keys())

    @staticmethod
    def relationships(project_id: str) -> list[dict]:
        """Return all relationships involving a given project."""
        rels = _DATA.get("family_taxonomy", {}).get("current_relationships", [])
        return [r for r in rels if project_id in r.get("projects", [])]

    @staticmethod
    def port_block(project_id: str, service: str = "api") -> str | None:
        """Return the recommended port block for a project service."""
        proj = _PROJECTS.get(project_id, {})
        ports = proj.get("ports", {})
        entry = ports.get(service, {})
        return entry.get("recommended_block") or entry.get("block")

    @staticmethod
    def summary() -> str:
        """Human-readable port summary table."""
        lines = [
            "QI Ecosystem — Port Registry",
            "=" * 50,
            f"{'Project':<12} {'Service':<10} {'Port':<8} {'Status'}",
            "-" * 50,
        ]
        for pid, proj in _PROJECTS.items():
            status = proj.get("status", "unknown")
            for svc, info in proj.get("ports", {}).items():
                port = info.get("current", "—")
                lines.append(f"{pid:<12} {svc:<10} {str(port):<8} {status}")
            if not proj.get("ports"):
                lines.append(f"{pid:<12} {'—':<10} {'—':<8} {status}")
        return "\n".join(lines)


if __name__ == "__main__":
    print(QI.summary())
    print()
    print("CORS origins:", QI.cors_origins())
