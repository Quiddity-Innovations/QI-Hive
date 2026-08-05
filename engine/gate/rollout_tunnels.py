# -*- coding: utf-8 -*-
"""
Repoint every Cloudflare tunnel through QI Gate.

For each hostname declared in config/gate.json with mode != "open", rewrite the
matching ingress rule in the tunnel YAML so it points at Caddy (:9040) instead
of straight at the app port. Hosts marked "open" are left exactly as they are.

    python rollout_tunnels.py            # dry run — show what would change
    python rollout_tunnels.py --apply    # write the YAMLs
    python rollout_tunnels.py --apply --restart   # ...and restart the services

Backups of the originals live in ..\\tunnels\\configs_backup_20260805\\.
"""

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GATE_DIR = Path(__file__).parent.resolve()
CFG = json.loads((GATE_DIR / "config" / "gate.json").read_text(encoding="utf-8"))
LISTEN = CFG["gate"]["listen_port"]
TUNNEL_DIR = Path(r"C:\QIH\engine\tunnels\configs")

POLICY = {h["host"].lower(): h for h in CFG["hosts"]}

# tunnel config stem -> NSSM service name
SERVICE_FOR = {
    "qi-hive": "QI_DashboardTunnel", "qi-cognibase": "QI_CogniBaseTunnel",
    "qi-mapsnap": "QI_MapSnapTunnel", "qi-tubescout": "QI_TubeScoutTunnel",
    "qi-nexus": "QI_NEXUSTunnel", "qi-naya": "QI_NayaTunnel",
    "qi-lotterywiz": "QI_LotteryWizTunnel", "qi-cypherminer": "QI_CypherMinerTunnel",
    "qi-gamez": "QI_GamezTunnel", "qi-m2v": "QI_M2VTunnel",
    "qi-autopdf": "QI_AutoPDFTunnel", "qi-maia": "QI_MaiaTunnel",
    "qi-kaze": "QI_KazeNewsTunnel", "qi-mq": "QI_MQTunnel",
    "qi-claudevoice": "QI_ClaudeVoiceTunnel", "qi-connector": "QI_ConnectorTunnel",
}

GATE_URL = f"http://localhost:{LISTEN}"
HOST_RE = re.compile(r"^(\s*-\s*hostname:\s*)(\S+)\s*$")
SVC_RE = re.compile(r"^(\s*)service:\s*(\S+)\s*$")


def process(path: Path, apply: bool):
    lines = path.read_text(encoding="utf-8").splitlines()
    out, changes = [], []
    pending_host = None

    for line in lines:
        m = HOST_RE.match(line)
        if m:
            pending_host = m.group(2).lower()
            out.append(line)
            continue

        s = SVC_RE.match(line)
        if s and pending_host:
            indent, current = s.group(1), s.group(2)
            pol = POLICY.get(pending_host)
            if pol and pol.get("mode") != "open" and current != GATE_URL:
                changes.append((pending_host, current, GATE_URL, pol.get("mode")))
                out.append(f"{indent}service: {GATE_URL}")
                pending_host = None
                continue
            if pol and pol.get("mode") == "open":
                changes.append((pending_host, current, current, "open (left alone)"))
            pending_host = None

        out.append(line)

    if apply and any(c[1] != c[2] for c in changes):
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changes


def main():
    apply = "--apply" in sys.argv
    restart = "--restart" in sys.argv

    print(f"{'DRY RUN — nothing written' if not apply else 'APPLYING'}\n")
    touched = []
    for path in sorted(TUNNEL_DIR.glob("qi-*.yml")):
        changes = process(path, apply)
        if not changes:
            continue
        print(f"{path.name}")
        moved = False
        for host, old, new, mode in changes:
            if old == new:
                print(f"    -  {host:<44} {old:<28} [{mode}]")
            else:
                print(f"    ->  {host:<44} {old:<28} -> {new}  [{mode}]")
                moved = True
        if moved:
            touched.append(SERVICE_FOR.get(path.stem))
        print()

    touched = [t for t in touched if t]
    print(f"Tunnels needing a restart ({len(touched)}): {', '.join(touched) or '(none)'}")

    if restart and apply and touched:
        sys.path.insert(0, r"C:\QIH\engine\common")
        from qi_elevate_client import run_elevated
        print("\nRestarting…")
        for svc in touched:
            r = run_elevated("nssm", ["restart", svc],
                             submitted_by="claude:gate_rollout", timeout=60)
            print(f"  {'OK ' if r.get('status') == 'ok' else '!! '} {svc:<24} {r.get('status')}")
    elif not apply:
        print("\nRe-run with --apply --restart to make it real.")


if __name__ == "__main__":
    main()
