# -*- coding: utf-8 -*-
"""OnBase licensing probe - API route.

Two transports, because MapSnap talks to two different OnBase systems:

  onbase13   LOCAL VM, OnBase 13. Talks HTTP/JSON to the guest-side Unity
             microservice (poc/guest_unity_service.ps1) on port 8088. The
             Hyland.Unity 13.0.2.192 assemblies stay on the guest where they
             belong; the host never loads them. This is ENABLED - it is
             Renne's own lab VM and consumes an existing MANAGER session.

  test/dev   BU Hyland Cloud, OnBase 25, over the Unity Client SOAP bridge.
  ut3/prod   DISABLED on 2026-08-06 at Renne's instruction. Two independent
             gates; this script will not contact them. See _bu_blocked().

Why an API probe at all, when SQL already reads the tables: licensing
enforcement lives in the Application Server, not in the database. SQL can tell
you what is persisted. Only the API can tell you whether OnBase will actually
grant a session, and what a given account is entitled to SEE - which is a
different and often smaller set than what the tables contain.

Environment:
    ONBASE_ENV                 onbase13 (default) | test | dev | ut3 | prod
    ONBASE_API_PROBE_ENABLE=1  opt-in required for the BU environments only
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

MAPSNAP_ROOT = Path(os.environ.get("MAPSNAP_ROOT", r"C:\MapSnap"))
PROFILE_DIR = MAPSNAP_ROOT / "Product" / "ONBASE13_POC"
CONN_FILE = PROFILE_DIR / ".mapsnap_conn.json"
ENV_FILE = MAPSNAP_ROOT / "config" / "onbase_environments.json"

ENV_KEY = (os.environ.get("ONBASE_ENV") or "onbase13").strip().lower()
ALLOW_BU = os.environ.get("ONBASE_API_PROBE_ENABLE", "") == "1"
BU_ENVS = {"test", "dev", "ut3", "prod"}

OK, BAD, LOCK, INFO = "[ OK ]", "[FAIL]", "[LOCK]", "[ .. ]"


def rule(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def get_json(url, timeout=25):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


# ---------------------------------------------------------------- OnBase 13

def load_conn():
    if not CONN_FILE.exists():
        return None
    try:
        return json.loads(CONN_FILE.read_text(encoding="utf-8-sig"))
    except ValueError:
        return None


def unity_base(conn):
    """Same resolution order server.py uses, so the probe and the app agree."""
    base = (conn.get("unity_url") or "").strip().rstrip("/")
    if base:
        return base
    host = (conn.get("server") or "").split(",")[0].strip()
    port = conn.get("unity_port", 8088)
    return "http://%s:%s" % (host, port) if host else ""


def sql_counts(conn):
    """Optional SQL side of the comparison. Never fatal - the API findings
    stand on their own if the database is unreachable."""
    try:
        import pyodbc
    except ImportError:
        return None, "pyodbc not installed"
    dsn = conn.get("dsn")
    if not dsn:
        return None, "no dsn in profile"
    try:
        cn = pyodbc.connect(dsn, timeout=10)
        cur = cn.cursor()
        out = {}
        for label, sql in (("useraccount", "SELECT COUNT(*) FROM hsi.useraccount"),
                           ("doctype", "SELECT COUNT(*) FROM hsi.doctype"),
                           ("usergroup", "SELECT COUNT(*) FROM hsi.usergroup")):
            try:
                cur.execute(sql)
                out[label] = cur.fetchone()[0]
            except Exception:
                out[label] = None
        cn.close()
        return out, None
    except Exception as exc:
        return None, str(exc)[:90]


def probe_onbase13():
    conn = load_conn()
    rule("PREFLIGHT - OnBase 13 (local VM)")
    if conn is None:
        print("%s profile connection missing: %s" % (BAD, CONN_FILE))
        return 2
    print("%s profile: %s" % (OK, conn.get("display_name", "ONBASE13_POC")))
    print("       database  : %s on %s (schema %s)"
          % (conn.get("database"), conn.get("server"),
             ",".join(conn.get("schemas") or [])))
    base = unity_base(conn)
    if not base:
        print("%s no unity_url or server in the profile - cannot reach the API" % BAD)
        return 2
    print("%s unity url : %s" % (OK, base))
    print("       appserver : %s" % conn.get("appserver_url", "(not set)"))

    rule("LIVE API - is there a session, and what is it entitled to?")
    started = time.time()
    try:
        ping = get_json(base + "/ping", timeout=25)
    except Exception as exc:
        print("%s guest Unity service unreachable: %s" % (BAD, str(exc)[:110]))
        print("       Start it in the VM: poc\\guest_unity_service.ps1")
        print("       (or the scheduled task QI_OnBaseUnityAPI)")
        return 2
    elapsed = time.time() - started

    if not ping.get("connected"):
        print("%s service is listening but Unity is NOT connected" % BAD)
        print("       error: %s" % (ping.get("error") or "(none reported)"))
        print("\nA refused session is itself a licensing signal - no seat, or the")
        print("account is not entitled. The error text distinguishes them.")
        return 2

    print("%s SESSION LIVE  (%.2fs)" % (OK, elapsed))
    print("       connected as : %s" % ping.get("user"))
    print("       data source  : %s" % ping.get("dataSource"))
    print("       service ver  : v%s" % ping.get("version"))
    print("\n       The Application Server granted and is holding this session.")
    print("       That is the licensing fact SQL cannot observe: enforcement")
    print("       lives in the App Server, not in the hsi tables.")

    routes = sorted(ping.get("routes") or [])
    rule("ENTITLEMENT SURFACE - %d collections this account can reach" % len(routes))
    print("The service probes each collection at /ping and advertises only the")
    print("ones this OnBase version AND this account can actually serve, so the")
    print("list below is an entitlement fingerprint rather than a static menu.\n")
    for i in range(0, len(routes), 4):
        print("   " + "".join("%-20s" % r for r in routes[i:i + 4]))

    rule("API vs SQL - what the account is allowed to SEE")
    print("Counts differing between the two routes are security trimming, not")
    print("error: the API returns only what MANAGER is entitled to.\n")
    sql, sql_err = sql_counts(conn)
    pairs = [("doctypes", "doctype", "Document types"),
             ("useraccounts", "useraccount", "User accounts"),
             ("usergroups", "usergroup", "User groups")]
    print("   %-18s %10s %10s   %s" % ("", "API", "SQL", "delta"))
    for route, table, label in pairs:
        api_n = "-"
        if route in routes:
            try:
                data = get_json(base + "/" + route, timeout=40)
                api_n = len(data) if isinstance(data, list) else "?"
            except Exception:
                api_n = "err"
        sql_n = (sql or {}).get(table, "-") if sql else "-"
        delta = ""
        if isinstance(api_n, int) and isinstance(sql_n, int):
            d = sql_n - api_n
            delta = "SQL +%d (trimmed)" % d if d > 0 else ("same" if d == 0 else "API +%d" % -d)
        print("   %-18s %10s %10s   %s" % (label, api_n, sql_n, delta))
    if sql_err:
        print("\n   (SQL side unavailable: %s - API figures above still stand)" % sql_err)

    rule("NOT AVAILABLE ON THIS ROUTE")
    print("named_client_license is a Unity SDK 25.x property. The OnBase 13")
    print("guest service returns only id/name/realName/email per account, so")
    print("per-user license class is NOT obtainable here. In the database it")
    print("survives as hsi.useraccount.licenseflag - use the SQL tab for that.")
    return 0


# ---------------------------------------------------------------- BU (locked)

def _bu_blocked():
    rule("BU ENVIRONMENT - blocked")
    print("%s '%s' is a BU Hyland Cloud environment (OnBase 25)." % (LOCK, ENV_KEY))
    print()
    print("Outbound connections to BU were disabled on 2026-08-06 at Renne's")
    print("instruction. Two independent gates:")
    print("   1. enabled=false in %s" % ENV_FILE.name)
    print("   2. ONBASE_API_PROBE_ENABLE=1 required, and the web runner never")
    print("      sets it - a browser button cannot opt in.")
    print()
    print("Gate 2 is currently %s." % ("OPEN" if ALLOW_BU else "CLOSED"))
    if ALLOW_BU:
        cfg = {}
        try:
            cfg = json.loads(ENV_FILE.read_text(encoding="utf-8-sig"))
        except Exception:
            pass
        env = (cfg.get("environments") or {}).get(ENV_KEY) or {}
        if env.get("enabled"):
            print("Gate 1 is ALSO open. Re-run through onbase_unity.test_connection")
            print("deliberately - this probe still declines, by design.")
        else:
            print("Gate 1 remains closed, so nothing was attempted.")
    print()
    print("Separately, this machine could not connect even if both gates opened:")
    print("the Unity Client is not installed, so the bridge cannot load")
    print("Hyland.Unity.dll, and no service-account credentials are present.")
    print()
    print("No network call was made.")
    return 3


def main():
    print("OnBase Licensing Probe - API route")
    print("Environment : %s" % ENV_KEY)

    if ENV_KEY in BU_ENVS:
        return _bu_blocked()
    if ENV_KEY != "onbase13":
        print("Unknown environment '%s'. Use onbase13, or one of: %s"
              % (ENV_KEY, ", ".join(sorted(BU_ENVS))))
        return 2

    rc = probe_onbase13()
    rule("DONE")
    print("Nothing here writes. The guest service holds one long-lived MANAGER")
    print("session for all callers, so this probe opened no new seat.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
