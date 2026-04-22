# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'C:\UNIVERSAL\qi_session')
from qi_context_loader import detect_project

tests = [
    ("hi", None),
    ("Hi, let us work on Maia today", "maia"),
    ("I want to fix a bug in Naya", "naya"),
    ("NEXUS is giving me issues", "nexus"),
    ("let us look at the dashboard", "universal"),
    ("OpenClaw agents are broken", "openclaw"),
    ("random message about stuff", None),
    ("EasyFlow email integration", "easyflow"),
    ("qi brain feature propagation", "universal"),
    ("Maia gradio tab is broken", "maia"),
]

print("Project Detection Test\n" + "─"*40)
all_pass = True
for msg, expected in tests:
    got = detect_project(msg)
    ok = got == expected
    if not ok:
        all_pass = False
    status = "✅" if ok else "❌"
    print(f"{status} [{msg[:42]:42}] → {str(got):12} (expected {expected})")

print("─"*40)
print("ALL PASS" if all_pass else "SOME FAILED")
