# -*- coding: utf-8 -*-
"""NSSM launcher for QI_MapSnapMCPBU — MapSnap BU Edition MCP gateway.
Runs the SHIPPED gateway copy (C:\\MapSnap\\tools\\qi_mcp_gateway.py — the one
with relative-path + deploy.json support) against the BU config. Exists because
the QI_Elevate whitelist only allows a bare .py path as AppParameters, same
pattern as mapsnap_mcp_launcher.py. Dev-machine glue only — NOT shipped in the
BU kit (the kit registers its own service via install.ps1)."""
import sys

sys.path.insert(0, r"C:\MapSnap\tools")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qi_mcp_gateway import main  # noqa: E402

main(r"C:\MapSnap\config\mcp_gateway_bu.json")
