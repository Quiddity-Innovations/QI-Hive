# -*- coding: utf-8 -*-
"""
QI Gate — command-line administration.

    python gate_admin.py users                       list accounts
    python gate_admin.py adduser  <name> <pw> [role] create (role: admin|user)
    python gate_admin.py passwd   <name> <pw>        change a password
    python gate_admin.py hosts    <name> [h1,h2|all] show/set which hosts a
                                                     user may reach ("all" or
                                                     no list = every host)
    python gate_admin.py disable  <name>             disable + kill sessions
    python gate_admin.py enable   <name>
    python gate_admin.py deluser  <name>
    python gate_admin.py sessions                    who is currently signed in
    python gate_admin.py revoke   <handle>           kill one session
    python gate_admin.py revokeall                   kill ALL sessions (panic)
    python gate_admin.py log [n]                     last n access-log entries
    python gate_admin.py suspects [hours]            failed/denied activity summary

Run from anywhere; paths resolve off this file's location.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
GATE_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(GATE_DIR))

import gate_auth as ga  # noqa: E402

CFG = json.loads((GATE_DIR / "config" / "gate.json").read_text(encoding="utf-8"))
ACCESS_LOG = Path(CFG["gate"].get("access_log", str(GATE_DIR / "LOGS" / "access.log")))


def _find(name):
    for u in ga.list_users():
        if u["username"].lower() == name.lower():
            return u
    raise SystemExit(f"no such user: {name}")


def _ts(epoch):
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")


def cmd_users(_):
    users = ga.list_users()
    if not users:
        print("(no accounts yet — the gate will show its first-run setup screen)")
        return
    print(f"{'USER':<20} {'ROLE':<8} {'STATE':<10} {'LAST LOGIN':<20} "
          f"{'CREATED':<12} ACCESS")
    for u in users:
        state = "disabled" if u["disabled"] else "active"
        last = (u["last_login_at"] or "—")[:19].replace("T", " ")
        hosts = u.get("allowed_hosts") or []
        access = "all hosts" if not hosts else ", ".join(hosts)
        print(f"{u['username']:<20} {u['role']:<8} {state:<10} {last:<20} "
              f"{u['created_at'][:10]:<12} {access}")


def cmd_adduser(a):
    if len(a) < 2:
        raise SystemExit(
            "usage: adduser <name> <password> [admin|user] [host1,host2]\n"
            "  a host list scopes the account to those sites only;\n"
            "  omit it (or pass 'all') for estate-wide access")
    role = a[2] if len(a) > 2 else "user"
    hosts = a[3] if len(a) > 3 and a[3].lower() != "all" else ""
    if hosts:
        _warn_unknown_hosts(hosts)
    u = ga.create_user(a[0], a[1], role=role, allowed_hosts=hosts)
    scope = ", ".join(u["allowed_hosts"]) if u["allowed_hosts"] else "ALL hosts"
    print(f"[OK] created {u['username']} (role={u['role']}) -> {scope}")


def _warn_unknown_hosts(raw):
    """A typo'd hostname silently locks the account out of everything, so say so."""
    known = {h["host"].lower() for h in CFG.get("hosts", [])}
    unknown = [h.strip() for h in raw.split(",")
               if h.strip() and h.strip().lower() not in known]
    if unknown:
        print(f"[!!] not hosts this gate fronts: {', '.join(unknown)}")
        print("     the account will NOT be able to reach them — check the spelling")


def cmd_hosts(a):
    if not a:
        raise SystemExit("usage: hosts <name> [host1,host2 | all]")
    u = _find(a[0])
    if len(a) < 2:
        cur = u.get("allowed_hosts") or []
        print(f"{u['username']}: " + (", ".join(cur) if cur else "all hosts"))
        return
    raw = "" if a[1].lower() == "all" else a[1]
    if raw:
        _warn_unknown_hosts(raw)
    hosts = ga.set_allowed_hosts(u["id"], raw)
    print(f"[OK] {u['username']} -> " + (", ".join(hosts) if hosts else "ALL hosts"))
    print("     takes effect on their next request; no re-login needed")


def cmd_passwd(a):
    if len(a) < 2:
        raise SystemExit("usage: passwd <name> <newpassword>")
    u = _find(a[0])
    ga.set_password(u["id"], a[1])
    killed = 0
    for s in ga.list_sessions():
        if s["username"].lower() == u["username"].lower():
            killed += ga.revoke_by_handle(s["handle"])
    print(f"[OK] password changed for {u['username']}"
          + (f" ({killed} existing session(s) signed out)" if killed else ""))


def cmd_disable(a):
    u = _find(a[0]); ga.set_disabled(u["id"], True)
    print(f"[OK] {u['username']} disabled and signed out everywhere")


def cmd_enable(a):
    u = _find(a[0]); ga.set_disabled(u["id"], False)
    print(f"[OK] {u['username']} enabled")


def cmd_deluser(a):
    u = _find(a[0]); ga.delete_user(u["id"])
    print(f"[OK] deleted {u['username']}")


def cmd_sessions(_):
    ss = ga.list_sessions()
    if not ss:
        print("(nobody signed in)")
        return
    print(f"{'HANDLE':<14} {'USER':<16} {'IP':<16} {'SINCE':<18} {'EXPIRES':<18} AGENT")
    for s in ss:
        print(f"{s['handle']:<14} {s['username']:<16} {(s['client_ip'] or '?'):<16} "
              f"{_ts(s['created_at']):<18} {_ts(s['expires_at']):<18} "
              f"{(s['user_agent'] or '')[:40]}")


def cmd_revoke(a):
    if not a:
        raise SystemExit("usage: revoke <handle>   (see: sessions)")
    print(f"[OK] revoked {ga.revoke_by_handle(a[0])} session(s)")


def cmd_revokeall(_):
    print(f"[OK] revoked {ga.revoke_all_sessions()} session(s) — everyone must sign in again")


def _read_log():
    if not ACCESS_LOG.exists():
        return []
    out = []
    for line in ACCESS_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def cmd_log(a):
    n = int(a[0]) if a else 40
    rows = _read_log()[-n:]
    if not rows:
        print("(access log empty)")
        return
    print(f"{'TIME':<20} {'EVENT':<15} {'IP':<16} {'HOST':<38} URI")
    for r in rows:
        print(f"{r.get('ts','')[:19].replace('T',' '):<20} {r.get('event',''):<15} "
              f"{r.get('ip',''):<16} {r.get('host','')[:37]:<38} {r.get('uri','')[:40]}")


def cmd_suspects(a):
    """What an intrusion review actually wants: who is being turned away, from
    where, and how often."""
    hours = int(a[0]) if a else 24
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = []
    for r in _read_log():
        try:
            if datetime.fromisoformat(r["ts"]) >= cutoff:
                rows.append(r)
        except Exception:
            pass
    if not rows:
        print(f"(no gate activity in the last {hours}h)")
        return

    print(f"=== QI Gate activity — last {hours}h ({len(rows)} events) ===\n")
    print("By event:")
    for ev, n in Counter(r.get("event", "?") for r in rows).most_common():
        print(f"  {n:>6}  {ev}")

    bad = [r for r in rows if r.get("event") in
           ("login_fail", "login_locked", "login_blocked", "setup_blocked")]
    if bad:
        print(f"\nFailed / blocked attempts ({len(bad)}):")
        for ip, n in Counter(r.get("ip", "?") for r in bad).most_common(15):
            countries = {r.get("cf_country", "") for r in bad if r.get("ip") == ip}
            cc = ",".join(sorted(c for c in countries if c))
            print(f"  {n:>6}  {ip:<18} {cc}")
        print("\n  usernames tried:")
        for u, n in Counter(r.get("user", "") for r in bad if r.get("user")).most_common(10):
            print(f"  {n:>6}  {u}")
    else:
        print("\nNo failed or blocked attempts. ✅")

    ok = [r for r in rows if r.get("event") == "login_ok"]
    if ok:
        print(f"\nSuccessful sign-ins ({len(ok)}):")
        for r in ok[-15:]:
            print(f"  {r.get('ts','')[:19].replace('T',' ')}  {r.get('user',''):<14} "
                  f"{r.get('ip',''):<16} {r.get('cf_country','')}")

    denied = [r for r in rows if r.get("event") == "deny"]
    if denied:
        print(f"\nTop unauthenticated targets ({len(denied)} redirects to login):")
        for (h, u), n in Counter((r.get("host", ""), r.get("uri", ""))
                                 for r in denied).most_common(12):
            print(f"  {n:>6}  {h}{u}")


COMMANDS = {
    "users": cmd_users, "adduser": cmd_adduser, "passwd": cmd_passwd,
    "hosts": cmd_hosts,
    "disable": cmd_disable, "enable": cmd_enable, "deluser": cmd_deluser,
    "sessions": cmd_sessions, "revoke": cmd_revoke, "revokeall": cmd_revokeall,
    "log": cmd_log, "suspects": cmd_suspects,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        raise SystemExit(1)
    ga.init_db()
    COMMANDS[sys.argv[1]](sys.argv[2:])
