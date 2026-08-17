# -*- coding: utf-8 -*-
"""NSSM launcher for QI_NexusMCP — runs the reusable QI MCP Gateway with NEXUS's
config (bare .py path required by the QI_Elevate whitelist, same pattern as
mapsnap_mcp_launcher.py)."""
import sys

sys.path.insert(0, r"C:\QIH\engine\common")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qi_mcp_gateway import main  # noqa: E402

main(r"C:\APPS\NEXUS\config\mcp_gateway.json")
