# -*- coding: utf-8 -*-
"""Dump qi_registry.json projects: id, path, ports. Used to build the
service verification map for the Phase 2 Python repoint."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

REG = r"C:\QIH\ecosystem\qi_registry.json"
d = json.load(open(REG, encoding="utf-8"))

print("=" * 78)
print("PROJECTS")
print("=" * 78)
for p in d["projects"]:
    ports = p.get("ports", {}) or {}
    flat = []
    for role, spec in ports.items():
        if isinstance(spec, dict):
            flat.append(f"{role}={spec.get('current')}")
        else:
            flat.append(f"{role}={spec}")
    print(f"{p.get('id',''):<22} {p.get('status',''):<20} {p.get('path','')}")
    if flat:
        print(f"{'':<22} ports: {', '.join(flat)}")

print()
print("=" * 78)
print("SHARED INFRASTRUCTURE")
print("=" * 78)
print(json.dumps(d.get("shared_infrastructure", {}), indent=2, ensure_ascii=False)[:3000])

print()
print("=" * 78)
print("PORT STRATEGY")
print("=" * 78)
print(json.dumps(d.get("port_strategy", {}), indent=2, ensure_ascii=False)[:2000])
