"""
Diagnostic: run via the broker to introspect the broker's own token
and SCM access. Drops a request asking the broker to run a python
script that prints whoami /all-equivalent info.
"""
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"C:\QIH")
from engine.common.qi_elevate_client import run_elevated

# We'll use whoami — need to whitelist it first.
# Safer diag: ask broker to run `sc sdshow QI_Dashboard` (SCM direct),
# and compare vs a hypothetical nssm stop.
print("=== sc sdshow QI_Dashboard via broker ===")
r = run_elevated("sc", ["query", "QI_Dashboard"], submitted_by="diag")
print(r.get("stdout"), r.get("stderr"))
