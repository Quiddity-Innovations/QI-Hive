# -*- coding: utf-8 -*-
"""NSSM launcher for QI_MapSnapMCP — runs the reusable QI MCP Gateway with
MapSnap's config. Exists because the QI_Elevate whitelist only allows a bare
.py path as AppParameters (no --config args), same pattern as
claudevoice_control_launcher.py."""
import sys

sys.path.insert(0, r"C:\QIH\engine\common")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qi_mcp_gateway import main  # noqa: E402

main(r"C:\APPS\MapSnap\config\mcp_gateway.json")
