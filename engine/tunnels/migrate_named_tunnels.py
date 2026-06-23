#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
QI Static (Named) Cloudflare Tunnel migrator.

Converts every QI quick tunnel (random *.trycloudflare.com) into a STATIC named
tunnel bound to a permanent subdomain of quiddityinnovations.com.

Driven entirely by tunnels.json (same folder). Idempotent: safe to re-run.

PREREQUISITES (the two things only YOU can do):
  1. Authenticate cloudflared ONCE against the account that owns the domain:
         cloudflared tunnel login
     -> a browser opens; pick quiddityinnovations.com; this writes
        %USERPROFILE%\\.cloudflared\\cert.pem  (needed only for create/route).
  2. Run THIS script from an ELEVATED (Administrator) terminal, as the SAME user
     who logged in (NSSM service edits require admin; cert.pem lives in that
     user's profile).

USAGE:
    python migrate_named_tunnels.py            # do it all
    python migrate_named_tunnels.py --dry-run  # print actions, change nothing
    python migrate_named_tunnels.py --only qi-maia qi-gamez
    python migrate_named_tunnels.py --skip-services   # tunnels+DNS+config only

The NSSM services (LocalSystem) only need `tunnel run`, which reads the
credentials file by absolute path (copied into creds/). They do NOT need cert.pem.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
MAP_FILE = os.path.join(HERE, "tunnels.json")
CONFIG = json.load(open(MAP_FILE, encoding="utf-8"))
META = CONFIG["_meta"]
DOMAIN = META["domain"]
CLOUDFLARED = META["cloudflared"]
NSSM = META["nssm"]
CONFIGS_DIR = META["configs_dir"]
CREDS_DIR = META["creds_dir"]
USER_CFDIR = os.path.join(os.path.expanduser("~"), ".cloudflared")

DRY = False
VIA_BROKER = False


def entry_domain(entry):
    """Domain for this tunnel — per-entry override, else the global META domain."""
    return entry.get("domain", DOMAIN)


def fqdn(entry, ing):
    """Full hostname. hostname '@' (or '') means the zone apex (the bare domain)."""
    h = ing["hostname"]
    d = entry_domain(entry)
    return d if h in ("@", "") else f"{h}.{d}"


def log(msg, kind="·"):
    print(f"  {kind} {msg}")


def _broker_nssm(nssm_args):
    """Route an nssm invocation through the QI_Elevate broker (runs as SYSTEM).
    Used when --via-broker is set so service edits work from a non-admin shell."""
    common = r"C:\QIH\engine\common"
    if common not in sys.path:
        sys.path.insert(0, common)
    from qi_elevate_client import run_elevated
    try:
        r = run_elevated("nssm", list(nssm_args),
                         submitted_by="migrate_named_tunnels", timeout=60)
    except Exception as e:
        return 1, f"broker error: {e}"
    rc = r.get("returncode")
    rc = rc if isinstance(rc, int) else (0 if r.get("status") == "ok" else 1)
    out = (r.get("stdout") or "") + (r.get("stderr") or "")
    if r.get("status") not in ("ok",) and r.get("error"):
        out = f"[broker {r.get('status')}] {r.get('error')}\n" + out
    return rc, out


def run(cmd, check=False, capture=True):
    """Run a command list. Returns (rc, stdout+stderr)."""
    printable = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    if DRY:
        log(f"WOULD RUN: {printable}", "→")
        return 0, ""
    if VIA_BROKER and cmd and cmd[0] == NSSM:
        rc, out = _broker_nssm(cmd[1:])
        if check and rc != 0:
            log(f"FAILED ({rc}): {printable}", "✗")
            log(out.strip(), " ")
        return rc, out
    p = subprocess.run(cmd, capture_output=capture, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    if check and p.returncode != 0:
        log(f"FAILED ({p.returncode}): {printable}", "✗")
        log(out.strip(), " ")
    return p.returncode, out


# ----------------------------------------------------------------------------- preflight
def preflight():
    print("=" * 70)
    print(f"QI NAMED-TUNNEL MIGRATION  —  domain: {DOMAIN}")
    print("=" * 70)
    if not os.path.exists(CLOUDFLARED):
        sys.exit(f"FATAL: cloudflared not found at {CLOUDFLARED}")
    cert = os.path.join(USER_CFDIR, "cert.pem")
    if not os.path.exists(cert) and not DRY:
        sys.exit(
            "FATAL: not authenticated. Run `cloudflared tunnel login` first\n"
            f"       (expected {cert}). See header of this script."
        )
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    os.makedirs(CREDS_DIR, exist_ok=True)
    log(f"cloudflared: {CLOUDFLARED}")
    log(f"cert.pem   : {'OK' if os.path.exists(cert) else '(dry-run, unchecked)'}")
    print()


# ----------------------------------------------------------------------------- cloudflared helpers
def list_tunnels():
    """name -> uuid for all existing tunnels. Reads STDOUT only (cloudflared logs to stderr)."""
    if DRY:
        return {}
    p = subprocess.run([CLOUDFLARED, "tunnel", "list", "--output", "json"],
                       capture_output=True, text=True)
    out = p.stdout or ""
    # isolate the JSON array (cloudflared may emit a warning line on stdout too)
    i, j = out.find("["), out.rfind("]")
    if i == -1 or j == -1:
        return {}
    try:
        return {t["name"]: t["id"] for t in json.loads(out[i:j + 1])}
    except Exception:
        return {}


def ensure_tunnel(name, existing):
    if name in existing:
        log(f"tunnel '{name}' exists (id {existing[name][:8]}…)")
        return existing[name]
    rc, out = run([CLOUDFLARED, "tunnel", "create", name], check=True)
    if DRY:
        return "DRYRUN-UUID"
    # parse "Created tunnel <name> with id <uuid>" from output, fall back to re-query
    uuid = None
    import re
    m = re.search(r"with id\s+([0-9a-fA-F-]{36})", out)
    if m:
        uuid = m.group(1)
    if not uuid:
        uuid = list_tunnels().get(name)
    if uuid:
        log(f"created tunnel '{name}' (id {uuid[:8]}…)", "✓")
    else:
        log(f"could not determine UUID for '{name}'", "✗")
    return uuid


def stash_creds(name, uuid):
    """Copy ~/.cloudflared/<uuid>.json -> creds/<name>.json (profile-independent)."""
    dst = os.path.join(CREDS_DIR, f"{name}.json")
    if DRY:
        log(f"WOULD copy creds -> {dst}", "→")
        return dst
    src = os.path.join(USER_CFDIR, f"{uuid}.json")
    if os.path.exists(src):
        shutil.copyfile(src, dst)
        log(f"creds -> {dst}", "✓")
    elif not os.path.exists(dst):
        log(f"WARNING: credentials file {src} not found and {dst} missing", "✗")
    return dst


def route_dns(name, fqdn):
    rc, out = run([CLOUDFLARED, "tunnel", "route", "dns", "--overwrite-dns", name, fqdn])
    if rc == 0:
        log(f"DNS  {fqdn}  →  {name}", "✓")
    else:
        # already-exists is fine; surface anything else
        low = out.lower()
        if "already" in low or "exists" in low:
            log(f"DNS  {fqdn}  already routed", "·")
        else:
            log(f"DNS route issue for {fqdn}: {out.strip()[:160]}", "✗")


# ----------------------------------------------------------------------------- config.yml
def write_config(entry, uuid, creds_path):
    name = entry["name"]
    path = os.path.join(CONFIGS_DIR, f"{name}.yml")
    lines = [
        f"# {entry['product']} — static named tunnel (generated by migrate_named_tunnels.py)",
        f"tunnel: {uuid}",
        f"credentials-file: {creds_path}",
        "no-autoupdate: true",
        "ingress:",
    ]
    for ing in entry["ingress"]:
        lines.append(f"  - hostname: {fqdn(entry, ing)}")
        lines.append(f"    service: http://localhost:{ing['port']}")
    lines.append("  - service: http_status:404")
    body = "\n".join(lines) + "\n"
    if DRY:
        log(f"WOULD write {path}", "→")
    else:
        open(path, "w", encoding="utf-8").write(body)
        log(f"config -> {path}", "✓")
    return path


# ----------------------------------------------------------------------------- NSSM
def service_exists(svc):
    rc, out = run([NSSM, "status", svc])
    return rc == 0 and "does not exist" not in out.lower()


def nset(svc, key, val):
    run([NSSM, "set", svc, key, val], check=True)


def configure_service(entry, cfg_path):
    svc = entry["service"]
    params = f"tunnel --no-autoupdate --config {cfg_path} run {entry['name']}"
    logdir = os.path.join(HERE, "LOGS")
    outlog = os.path.join(logdir, f"{svc}.out.log")
    errlog = os.path.join(logdir, f"{svc}.err.log")

    if not service_exists(svc):
        if entry.get("install_if_missing"):
            log(f"installing new service {svc}", "✓")
            run([NSSM, "install", svc, CLOUDFLARED], check=True)
        else:
            log(f"service {svc} not found — skipping (expected to exist)", "✗")
            return
    run([NSSM, "stop", svc])
    nset(svc, "Application", CLOUDFLARED)
    nset(svc, "AppDirectory", HERE)
    nset(svc, "AppParameters", params)
    nset(svc, "AppStdout", outlog)
    nset(svc, "AppStderr", errlog)
    nset(svc, "Start", "SERVICE_AUTO_START")
    nset(svc, "Description",
         f"QI static Cloudflare tunnel '{entry['name']}' for {entry['product']} "
         f"→ {', '.join(fqdn(entry, i) for i in entry['ingress'])}")
    run([NSSM, "start", svc], check=True)
    log(f"service {svc} now runs named tunnel '{entry['name']}'", "✓")


def retire_service(svc):
    if not service_exists(svc):
        log(f"retire: {svc} already absent", "·")
        return
    run([NSSM, "stop", svc])
    nset(svc, "Start", "SERVICE_DISABLED")
    log(f"retired (stopped + disabled, not removed): {svc}", "✓")


# ----------------------------------------------------------------------------- URL files for consumers
def write_url_file(entry):
    uf = entry.get("url_file")
    if not uf:
        return
    url = f"https://{fqdn(entry, entry['ingress'][0])}"
    kind = entry.get("url_file_kind", "plain")
    if DRY:
        log(f"WOULD write static URL {url} -> {uf} ({kind})", "→")
        return
    os.makedirs(os.path.dirname(uf), exist_ok=True)
    if kind == "dashboard_json":
        payload = {"url": url, "static": True, "tunnel": entry["name"], "updated": "named-tunnel"}
        open(uf, "w", encoding="utf-8").write(json.dumps(payload, indent=2))
    else:
        open(uf, "w", encoding="utf-8").write(url + "\n")
    log(f"static URL {url} -> {uf}", "✓")


# ----------------------------------------------------------------------------- main
def main():
    global DRY, VIA_BROKER
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", help="only these tunnel names")
    ap.add_argument("--skip-services", action="store_true",
                    help="do tunnels+DNS+config but leave NSSM services untouched")
    ap.add_argument("--via-broker", action="store_true",
                    help="route NSSM service edits through the QI_Elevate broker "
                         "(lets the service swap run from a non-admin shell)")
    args = ap.parse_args()
    DRY = args.dry_run
    VIA_BROKER = args.via_broker
    if VIA_BROKER:
        log("NSSM service edits will be routed through QI_Elevate broker", "·")

    preflight()
    existing = list_tunnels()
    if existing:
        log(f"existing tunnels: {', '.join(existing) or '(none)'}\n")

    tunnels = CONFIG["tunnels"]
    if args.only:
        tunnels = [t for t in tunnels if t["name"] in set(args.only)]

    summary = []
    for entry in tunnels:
        name = entry["name"]
        print(f"── {name}  ({entry['product']}) " + "─" * (50 - len(name) - len(entry['product'])))
        uuid = ensure_tunnel(name, existing)
        creds = stash_creds(name, uuid)
        for ing in entry["ingress"]:
            route_dns(name, fqdn(entry, ing))
        cfg = write_config(entry, uuid, creds)
        if not args.skip_services:
            configure_service(entry, cfg)
            for r in entry.get("retire", []):
                retire_service(r)
        write_url_file(entry)
        hosts = ", ".join(f"https://{fqdn(entry, i)}" for i in entry["ingress"])
        summary.append((entry["service"], name, hosts))
        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for svc, name, hosts in summary:
        print(f"  {svc:<22} {name:<16} {hosts}")
    print()
    if DRY:
        print("DRY-RUN — nothing was changed. Re-run without --dry-run to apply.")
    else:
        print("Done. Verify with:  python verify_named_tunnels.py")


if __name__ == "__main__":
    main()
