# -*- coding: utf-8 -*-
"""
Render Caddyfile.gate from config/gate.json.

The policy lives in ONE place (gate.json). This script turns it into Caddy
config so the two can never drift. The main Caddyfile imports the result, so
the hand-written *.qi.local blocks are left untouched.

Run after any edit to gate.json:
    python C:\\QIH\\engine\\gate\\gen_caddyfile.py
    C:\\QIH\\engine\\bin\\caddy.exe reload --config C:\\QIH\\engine\\proxy\\Caddyfile
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

GATE_DIR = Path(__file__).parent.resolve()
CFG = json.loads((GATE_DIR / "config" / "gate.json").read_text(encoding="utf-8"))
OUT = GATE_DIR / "config" / "Caddyfile.gate"

G = CFG["gate"]
LISTEN = G["listen_port"]
AUTH = f"127.0.0.1:{G['auth_port']}"
PREFIX = G.get("auth_prefix", "/qi-auth")


def path_matcher(paths):
    """gate.json path convention: a trailing '/' means 'this prefix and
    everything under it'; anything else is matched exactly."""
    out = []
    for p in paths:
        out.append(f"{p.rstrip('/')}/*" if p.endswith("/") else p)
    return " ".join(out)


# Every public host is HTTPS-only at the Cloudflare edge, but the hop from
# cloudflared into Caddy is plain HTTP. Without this, Caddy tells the app
# X-Forwarded-Proto: http, and any app that builds absolute URLs from it emits
# http:// links on an https:// page — which browsers block as mixed content.
# That is what broke Gradio's theme.css preload and heartbeat stream on NEXUS.
UPSTREAM_HEADERS = [
    "header_up X-Forwarded-Proto https",
    "header_up X-Forwarded-Host {http.request.host}",
]


def proxy(upstream, indent):
    pad = "\t" * indent
    lines = [f"{pad}reverse_proxy {upstream} {{"]
    lines += [f"{pad}\t{h}" for h in UPSTREAM_HEADERS]
    lines.append(f"{pad}}}")
    return lines


def host_block(h, idx):
    host = h["host"]
    up = h["upstream"]
    mode = h.get("mode", "protected")
    app = h.get("app", "")
    tag = f"h{idx}"
    L = []

    L.append(f"\t# ── {host}  →  {app}  [{mode}]")
    for key in ("note", "why"):
        if h.get(key):
            for line in _wrap(h[key], 88):
                L.append(f"\t#   {line}")

    L.append(f"\t@{tag} host {host}")
    L.append(f"\thandle @{tag} {{")

    if mode == "open":
        L += proxy(up, 2)
        L.append("\t}")
        L.append("")
        return L

    # The login screen itself must never require a login.
    L.append(f"\t\thandle {PREFIX}/* {{")
    L += proxy(AUTH, 3)
    L.append("\t\t}")

    if mode == "mixed" and h.get("public_paths"):
        # Matched BEFORE forward_auth on purpose: machine callbacks keep
        # working even if QI Gate itself is stopped.
        L.append(f"\t\t@{tag}_public path {path_matcher(h['public_paths'])}")
        L.append(f"\t\thandle @{tag}_public {{")
        L += proxy(up, 3)
        L.append("\t\t}")

    L.append("\t\thandle {")
    L.append(f"\t\t\tforward_auth {AUTH} {{")
    L.append(f"\t\t\t\turi {PREFIX}/verify")
    L.append("\t\t\t\tcopy_headers X-Qi-User X-Qi-Role")
    L.append("\t\t\t\theader_up X-Forwarded-Proto https")
    L.append("\t\t\t}")
    L += proxy(up, 3)
    L.append("\t\t}")
    L.append("\t}")
    L.append("")
    return L


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > width:
            out.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out


def main():
    hosts = CFG.get("hosts", [])
    n_prot = sum(1 for h in hosts if h.get("mode") == "protected")
    n_mix = sum(1 for h in hosts if h.get("mode") == "mixed")
    n_open = sum(1 for h in hosts if h.get("mode") == "open")

    L = [
        "# ═══════════════════════════════════════════════════════════════",
        "# QI Gate — public edge.  GENERATED FILE — DO NOT EDIT BY HAND.",
        "#   source:    C:\\QIH\\engine\\gate\\config\\gate.json",
        "#   regenerate: python C:\\QIH\\engine\\gate\\gen_caddyfile.py",
        f"#   generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "#",
        f"#   {len(hosts)} public hostnames: {n_prot} protected, "
        f"{n_mix} mixed, {n_open} open",
        "#",
        "#   Every Cloudflare tunnel points here. Caddy does the proxying",
        "#   (websockets/SSE/Gradio queues pass through untouched) and asks",
        "#   QI Gate whether the caller is signed in.",
        "# ═══════════════════════════════════════════════════════════════",
        "",
        f":{LISTEN} {{",
        "\tlog {",
        "\t\toutput file C:\\QIH\\engine\\gate\\LOGS\\caddy_edge.log {",
        "\t\t\troll_size 20mb",
        "\t\t\troll_keep 10",
        "\t\t}",
        "\t\tformat json",
        "\t}",
        "",
        "\theader {",
        "\t\t-Server",
        "\t\tX-Content-Type-Options nosniff",
        "\t\tReferrer-Policy strict-origin-when-cross-origin",
        "\t}",
        "",
    ]

    for i, h in enumerate(hosts):
        L += host_block(h, i)

    L += [
        "\t# Anything arriving with a Host we do not publish is not ours.",
        "\thandle {",
        '\t\trespond "Not found" 404',
        "\t}",
        "}",
        "",
    ]

    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"[OK] wrote {OUT}")
    print(f"     {len(hosts)} hosts — {n_prot} protected, {n_mix} mixed, {n_open} open")
    for h in hosts:
        if h.get("mode") == "open":
            print(f"     [!] OPEN: {h['host']} — {h.get('why','no reason given')[:80]}")


if __name__ == "__main__":
    main()
