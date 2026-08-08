# -*- coding: utf-8 -*-
"""One-shot repair: QI_M2VTunnel had empty AppParameters + wrong AppDirectory, so the
service launched cloudflared with no args and never connected (m2v 530). Wire it like the
other named-tunnel services and add log paths. All edits go through the QI_Elevate broker."""
import sys
sys.path.insert(0, r"C:\QIH")
sys.stdout.reconfigure(encoding="utf-8")
from engine.common.qi_elevate_client import run_elevated as R


def do(args):
    r = R("nssm", args, submitted_by="m2v_svc_fix", timeout=40)
    tag = args[2] if len(args) > 2 else args[0]
    print(f"{tag:<14} -> {r.get('status')}  {r.get('rule_matched') or r.get('error')}")
    return r


do(["set", "QI_M2VTunnel", "AppParameters",
    r"tunnel --no-autoupdate --config C:\QIH\engine\tunnels\configs\qi-m2v.yml run qi-m2v"])
do(["set", "QI_M2VTunnel", "AppDirectory", r"C:\QIH\engine\tunnels"])
do(["set", "QI_M2VTunnel", "AppStdout", r"C:\QIH\engine\tunnels\LOGS\QI_M2VTunnel.out.log"])
do(["set", "QI_M2VTunnel", "AppStderr", r"C:\QIH\engine\tunnels\LOGS\QI_M2VTunnel.err.log"])
do(["restart", "QI_M2VTunnel"])
