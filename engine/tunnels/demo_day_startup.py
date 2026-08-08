# -*- coding: utf-8 -*-
"""
QI Demo-Day Startup & Tunnel Verifier
=====================================
Brings up EVERY QI application and EVERY Cloudflare named tunnel, waits for warm-up,
verifies each public URL actually responds, retries anything that is down, and pushes
a concise pass/fail summary to Renne's Tasuke LINE.

Designed to be fired by the one-time scheduled task QI_DemoDayStartup (07:30) so that on
a full demo day every app is reachable from outside regardless of what a visitor asks to see.

Idempotent: starting an already-running service is a harmless no-op.
Run elevated (the scheduled task uses RunLevel=Highest) so `nssm start` succeeds without UAC.
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TUNNELS_JSON = os.path.join(HERE, "tunnels.json")
NSSM = r"C:\QIH\engine\bin\nssm.exe"
NOTIFY = r"C:\CLAUDE\Tools\qi_tasuke_notify.py"
PYTHON = sys.executable
LOG_DIR = os.path.join(HERE, "LOGS")
os.makedirs(LOG_DIR, exist_ok=True)

sys.path.insert(0, r"C:\QIH")
from engine.common.qi_elevate_client import run_elevated  # noqa: E402

CONFIG = json.load(open(TUNNELS_JSON, encoding="utf-8"))
DOMAIN = CONFIG["_meta"]["domain"]

# Only demo apps on the primary domain. quiddam.com is intentionally out of scope
# (Renne, 2026-06-25: "no quiddam.com, just quiddityinnovations.com").
TUNNELS = [e for e in CONFIG["tunnels"] if e.get("domain", DOMAIN) == DOMAIN]

# Dry-run (QI_DEMO_DRYRUN=1): verify only — never start/restart services, no LINE push,
# short waits. Used to validate the script without side effects.
DRYRUN = os.environ.get("QI_DEMO_DRYRUN") == "1"
WARMUP = 3 if DRYRUN else 30

# Origin app services keyed by the local port they serve (NSSM services only;
# ports served from WSL / not-yet-an-NSSM-app are intentionally absent and just skipped).
PORT_TO_APP = {
    8001: "QI_MaiaBot",
    7860: "QI_MaiaGradio",
    7861: "QI_NayaGradio",
    8002: "QI_NayaBot",
    7880: "QI_NEXUS",
    8600: "QI_Dashboard",
    # 6969: "QI_AutoPDF",  # SKIP (Renne, 2026-07-20): :6969 has a double-owner (service stopped,
    # http.sys process serving). App + tunnel already answer 200/401, so leave the service untouched.
    # qi-autopdf tunnel is still started (from tunnels.json) and the URL is still verified below.
    8650: "QI_CogniBase",
    9876: "QI_MapSnap",
    8777: "QI_LotteryWiz",
    7842: "QI_CypherMinerUI",
    8503: "QI_TubeScout",
    8710: "QI_GamezProxy",
    8721: "QI_ClaudeVoiceLine",
    # 18800/18789 -> Kaze/OpenClaw (WSL, no NSSM), 7840/8500/7849 -> MQ, 7841 -> M2V: no NSSM app service
}
# Brain backs several UIs (dashboard, mission-control) — bring it up too.
EXTRA_APPS = ["QI_BrainAPI", "QI_KazeConfigAPI"]

# Apps that have a tunnel but NO NSSM service — launched directly, detached, as the
# task's (non-elevated) user. M2V's files live under C:\M2V (outside QIH/QIP) so the
# elevation broker can't service-install it; we just start its process if the port is dead.
NON_SERVICE_APPS = [
    {"name": "M2V", "port": 7841,
     "exe": r"C:\M2V\.venv\Scripts\python.exe", "args": ["main.py"], "cwd": r"C:\M2V"},
]

log_lines = []


def log(msg):
    print(msg, flush=True)
    log_lines.append(msg)


def nssm(action, svc):
    """Run `nssm <action> <svc>` elevated via the QI_Elevate broker.
    Service start/stop needs admin rights; the broker grants them without UAC,
    so this script can run from an ordinary (non-elevated) scheduled task."""
    try:
        r = run_elevated("nssm", [action, svc], submitted_by="demo_day_startup", timeout=45)
        out = ((r.get("stdout") or "") + (r.get("stderr") or "")).strip()
        return r.get("returncode", 1), out
    except Exception as e:
        return 1, f"BROKER_ERROR: {e}"


def status(svc):
    _, out = nssm("status", svc)
    return out.strip().upper()


def installed(svc):
    up = status(svc)
    return "SERVICE_" in up  # SERVICE_RUNNING / _STOPPED / _PAUSED ; missing svc lacks this token


def start(svc):
    """Start a service if not already running. Returns final status string."""
    st = status(svc)
    if "RUNNING" in st:
        return "RUNNING (already)"
    if DRYRUN:
        return f"{st or 'UNKNOWN'} (dryrun: would start)"
    nssm("start", svc)
    time.sleep(2)
    return status(svc) or "UNKNOWN"


def port_listening(port):
    s = socket.socket()
    s.settimeout(1.5)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def launch_non_service(app):
    if port_listening(app["port"]):
        return "already listening"
    if DRYRUN:
        return "not listening (dryrun: would launch)"
    try:
        DETACHED, NEW_GROUP = 0x00000008, 0x00000200
        subprocess.Popen([app["exe"], *app["args"]], cwd=app["cwd"],
                         creationflags=DETACHED | NEW_GROUP,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, close_fds=True)
        return "launched"
    except Exception as e:
        return f"launch failed: {e}"


def fqdn(entry, ing):
    h = ing["hostname"]
    d = entry.get("domain", DOMAIN)
    return d if h in ("@", "") else f"{h}.{d}"


BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def https_code(host):
    """GET (browser-like) so the check mirrors what a visiting browser sees.
    Returns an int status, or None if the edge is unreachable."""
    try:
        req = urllib.request.Request(f"https://{host}", method="GET",
                                     headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code  # tunnel + origin reachable, origin returned a status code
    except Exception:
        return None


def classify(host, code):
    """Return one of: 'ok', 'origin_down', 'unreachable', 'pending_dns'."""
    if host.endswith("quiddam.com"):
        return "pending_dns"  # quiddam.com DNS not yet provisioned (known, can't fix here)
    if code is None:
        return "unreachable"          # can't reach the Cloudflare edge at all
    if code in (502, 503, 504, 521, 522, 523, 530):
        return "origin_down"          # tunnel up but the app behind it isn't answering
    if code < 500:
        return "ok"                   # 200/3xx/401/403 — reachable through the tunnel
    return "origin_down"


def notify(text):
    try:
        subprocess.run([PYTHON, NOTIFY, text], capture_output=True, text=True, timeout=60)
    except Exception as e:
        log(f"(notify failed: {e})")


def main():
    log("=" * 70)
    log("QI DEMO-DAY STARTUP — bringing up all apps + tunnels")
    log("=" * 70)

    # ---- 1. Collect the full service set from tunnels.json ----------------
    tunnel_services = []
    origin_apps = []
    for e in TUNNELS:
        if e.get("service"):
            tunnel_services.append(e["service"])
        for ing in e["ingress"]:
            app = PORT_TO_APP.get(ing["port"])
            if app and app not in origin_apps:
                origin_apps.append(app)
    for a in EXTRA_APPS:
        if a not in origin_apps:
            origin_apps.append(a)

    # ---- 2. Start origin apps first so tunnels have a live origin ---------
    log("\n--- Starting application origins ---")
    for svc in origin_apps:
        if not installed(svc):
            log(f"  SKIP  {svc:<22} (not installed)")
            continue
        log(f"  {svc:<22} -> {start(svc)}")

    # Non-service origins (have a tunnel but no NSSM service)
    log("\n--- Starting non-service app origins ---")
    for app in NON_SERVICE_APPS:
        log(f"  {app['name']:<22} -> {launch_non_service(app)}")

    log(f"\nWaiting {WARMUP}s for apps to warm up...")
    time.sleep(WARMUP)

    # ---- 3. Start tunnels -------------------------------------------------
    log("\n--- Starting Cloudflare tunnels ---")
    for svc in tunnel_services:
        if not installed(svc):
            log(f"  SKIP  {svc:<22} (not installed)")
            continue
        log(f"  {svc:<22} -> {start(svc)}")

    log(f"\nWaiting {WARMUP}s for tunnels to register with the Cloudflare edge...")
    time.sleep(WARMUP)

    # ---- 4. Verify every public URL responds (2 passes w/ retry) ----------
    log("\n--- Verifying public URLs ---")
    results = []  # (product, host, code)
    for e in TUNNELS:
        for ing in e["ingress"]:
            host = fqdn(e, ing)
            results.append([e["product"], host, ing["port"], None])

    def needs_work(r):
        return classify(r[1], r[3]) in ("origin_down", "unreachable")

    for attempt in (1, 2):
        if not any(needs_work(r) for r in results):
            break
        if attempt == 2 and not DRYRUN:
            log("\nRetrying URLs that did not respond + restarting their tunnels...")
            down_services = set()
            for e in TUNNELS:
                for ing in e["ingress"]:
                    r = next((x for x in results if x[1] == fqdn(e, ing)), None)
                    if r and needs_work(r) and e.get("service") and installed(e["service"]):
                        down_services.add(e["service"])
            for svc in down_services:
                nssm("restart", svc)
                log(f"  restarted {svc}")
            time.sleep(25)
        for r in results:
            if classify(r[1], r[3]) == "ok":
                continue
            r[3] = https_code(r[1])

    # ---- 5. Report --------------------------------------------------------
    log("\n--- RESULTS ---")
    ok, bad, pending = [], [], []
    for product, host, port, code in results:
        kind = classify(host, code)
        bucket = {"ok": ok, "pending_dns": pending}.get(kind, bad)
        bucket.append((product, host, code))
        mark = {"ok": "OK  ", "pending_dns": "PEND", "origin_down": "ORIG", "unreachable": "DOWN"}[kind]
        log(f"  [{mark}] {str(code):>4}  https://{host}")

    summary_head = (f"QI Demo-Day startup {time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Public URLs live: {len(ok)}/{len(ok) + len(bad)}"
                    + (f" (+{len(pending)} pending DNS)" if pending else ""))
    if bad:
        summary = summary_head + "\nNEEDS ATTENTION:\n" + "\n".join(
            f"- {h} ({c})" for _, h, c in bad)
    else:
        summary = summary_head + "\nAll public URLs are live. Ready for demos."
    log("\n" + summary)

    # Write report log
    stamp = time.strftime("%Y-%m-%d_%H%M")
    report = os.path.join(LOG_DIR, f"demo_day_{stamp}.log")
    with open(report, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    log(f"\nReport: {report}")

    # Notify Renne via Tasuke LINE
    if DRYRUN:
        log("\n(dryrun: skipping Tasuke LINE notification)")
    else:
        notify(summary)


if __name__ == "__main__":
    main()
