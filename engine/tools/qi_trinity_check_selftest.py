# -*- coding: utf-8 -*-
"""Prove the new MCP handshake check FAILS when Codex cannot serve MCP.

A health check that has only ever been run against a working system is not
evidence of anything — that is precisely how the process-count check shipped
green while the Codex leg was dead. So drive it through each failure mode and
assert it goes red.

Nothing here reinstalls or modifies Codex. Each case only rewrites the module's
CODEX_BIN for the duration of one call.
"""
import importlib.util
import sys

sys.stdout.reconfigure(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "qi_trinity_check", r"C:\QIH\engine\tools\qi_trinity_check.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

REAL_BIN = mod.CODEX_BIN
CASES = [
    ("healthy 0.153.4 (control)", REAL_BIN, mod.PASS),
    # Binary gone entirely.
    ("binary missing", "/home/hyosuke/.npm-global/bin/codex_DOES_NOT_EXIST", mod.FAIL),
    # The real 0.154.0 failure: app-server answers `initialize` but is not MCP.
    # The trailing '#' comments out the ' mcp-server' the check appends.
    ("0.154.0-style: app-server instead of mcp-server",
     f"{REAL_BIN} app-server --listen stdio:// #", mod.FAIL),
    # Something that runs, exits clean, and says nothing.
    ("silent binary (no JSON at all)", "true #", mod.FAIL),
]

failures = []
for label, fake_bin, expected in CASES:
    mod.CODEX_BIN = fake_bin
    checker = mod.Checks()
    checker.check_codex_handshake()
    rows = [r for r in checker.rows if r["check"] == "MCP handshake"]
    got = rows[-1]["status"] if rows else "NO RESULT"
    detail = (rows[-1]["detail"] or "")[:105] if rows else ""
    ok = got == expected
    if not ok:
        failures.append(label)
    print(f"{'PASS' if ok else 'BAD '} | {label}")
    print(f"       expected={expected}  got={got}")
    print(f"       {detail}")

mod.CODEX_BIN = REAL_BIN
print()
if failures:
    print("CHECK IS NOT TRUSTWORTHY — did not go red for:", failures)
    raise SystemExit(1)
print("All failure modes correctly detected. The check goes red when Codex cannot serve MCP.")
