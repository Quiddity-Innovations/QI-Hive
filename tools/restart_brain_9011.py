# -*- coding: utf-8 -*-
"""
Restart QI_BrainAPI on port 9011.
Stops dependents first, restarts Brain, then restarts dependents.
Run once after port migration from 9010 to 9011.
"""
import sys
import time

sys.path.insert(0, r'C:\QIH\engine\common')
from qi_elevate_client import run_elevated

def elevate(action, service):
    result = run_elevated('nssm', [action, service], submitted_by='claude_builder')
    print(f"  nssm {action} {service} -> {result}")
    return result

print("=== Brain 9011 Restart ===")

print("\n[1/3] Stopping dependents...")
elevate('stop', 'QI_NEXUS')
elevate('stop', 'QI_NayaBot')
elevate('stop', 'QI_MaiaBot')
elevate('stop', 'QI_Dashboard')

print("\n[2/3] Restarting QI_BrainAPI...")
elevate('restart', 'QI_BrainAPI')
print("  Waiting 5s for Brain to bind...")
time.sleep(5)

print("\n[3/3] Starting dependents...")
elevate('start', 'QI_Dashboard')
elevate('start', 'QI_MaiaBot')
elevate('start', 'QI_NayaBot')
elevate('start', 'QI_NEXUS')

print("\nDone.")
