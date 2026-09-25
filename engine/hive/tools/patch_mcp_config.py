# -*- coding: utf-8 -*-
"""Safely patch .claude.json to add the SQLite MCP servers."""
import json
import sys
import os

CONFIG_PATH = r"C:\Users\renne\.claude.json"

NEW_SERVERS = {
    "sqlite-maia": {
        "type": "stdio",
        "command": "C:/Program Files/Python311/Scripts/mcp-server-sqlite.exe",
        "args": ["--db-path", "C:/APPS/QI/maia.db"],
        "env": {}
    },
    "sqlite-naya": {
        "type": "stdio",
        "command": "C:/Program Files/Python311/Scripts/mcp-server-sqlite.exe",
        "args": ["--db-path", "C:/APPS/NAYA/naya.db"],
        "env": {}
    }
    # "git" (npm @cyanheads/git-mcp-server) removed 2026-09-25: the Windows npm global prefix is gone,
    # so it pointed at a missing command and failed in every session. Claude uses Bash git.
}

with open(CONFIG_PATH, encoding='utf-8') as f:
    config = json.load(f)

if "mcpServers" not in config:
    config["mcpServers"] = {}

added = []
for name, server_cfg in NEW_SERVERS.items():
    if name not in config["mcpServers"]:
        config["mcpServers"][name] = server_cfg
        added.append(name)
    else:
        print(f"  [skip] {name} already registered")

with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print(f"Done. Added: {added}")
print(f"All MCP servers: {list(config['mcpServers'].keys())}")
