# -*- coding: utf-8 -*-
"""Probe 2: what IS the live licensing state, given the classic tables are empty."""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pyodbc

HOST = os.environ.get("ONBASE_HOST", "192.168.251.128,1433")
PWD = os.environ.get("ONBASE_SA_PWD", "N@ut1lus")

CONN = ("DRIVER={SQL Server};SERVER=%s;"
        "DATABASE=Nautilus;UID=sa;PWD=%s" % (HOST, PWD))
print("Target: %s  db=Nautilus" % HOST)
cn = pyodbc.connect(CONN, timeout=15)
cur = cn.cursor()

print("### systemtableex (full row, blobs by shape)")
cur.execute("SELECT * FROM hsi.systemtableex")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    for c, v in zip(cols, r):
        s = str(v)
        if v is not None and len(s) > 60:
            print("   %-24s <len=%d> %r..." % (c, len(s), s[:40]))
        else:
            print("   %-24s %r" % (c, v))

print("\n### OnBase version markers")
for sql, label in [
    ("SELECT TOP 3 * FROM hsi.dbversioncontrol", "dbversioncontrol"),
    ("SELECT TOP 5 * FROM hsi.version", "version"),
    ("SELECT dbversion FROM hsi.licensetable", "licensetable.dbversion"),
]:
    try:
        cur.execute(sql)
        cs = [d[0] for d in cur.description]
        for r in cur.fetchall():
            print("  %s: %s" % (label, dict(zip(cs, [str(x)[:40] for x in r]))))
    except Exception as e:
        print("  %s: ERR %s" % (label, str(e)[:70]))

print("\n### every hsi table whose NAME contains 'lic' or 'regist' - row counts")
cur.execute("""SELECT t.name FROM sys.tables t WHERE schema_name(t.schema_id)='hsi'
               AND (t.name LIKE '%lic%' OR t.name LIKE '%regist%') ORDER BY t.name""")
for (n,) in cur.fetchall():
    try:
        cur2 = cn.cursor()
        cur2.execute("SELECT COUNT(*) FROM hsi.[%s]" % n)
        print("   hsi.%-28s %s" % (n, cur2.fetchone()[0]))
    except Exception as e:
        print("   hsi.%-28s ERR" % n)

print("\n### tables with a license-ish COLUMN that actually hold rows")
cur.execute("""
SELECT DISTINCT t.name FROM sys.columns c
JOIN sys.tables t ON c.object_id=t.object_id
WHERE schema_name(t.schema_id)='hsi' AND c.name LIKE '%licens%' ORDER BY t.name""")
for (n,) in cur.fetchall():
    cur2 = cn.cursor()
    try:
        cur2.execute("SELECT COUNT(*) FROM hsi.[%s]" % n)
        print("   hsi.%-28s rows=%s" % (n, cur2.fetchone()[0]))
    except Exception:
        print("   hsi.%-28s ERR" % n)

print("\n### registeredusers (identifiers masked)")
cur.execute("SELECT registernum, registername, dateregistered, usernum, "
            "stationdesc, lastlogon, platformtype, machineid FROM hsi.registeredusers "
            "ORDER BY registernum")
for r in cur.fetchall():
    mid = (str(r[7]).strip() or "")
    print("   #%s name=%-14r user=%s station=%-14r last=%s plat=%s machine=%s" % (
        r[0], str(r[1]).strip(), r[3], str(r[4]).strip(), r[5], r[6],
        (mid[:6] + "..." if len(mid) > 6 else mid)))

print("\n### useraccount licenseflag distribution")
try:
    cur.execute("SELECT licenseflag, COUNT(*) FROM hsi.useraccount GROUP BY licenseflag ORDER BY 1")
    for r in cur.fetchall():
        print("   licenseflag=%-6s users=%s" % (r[0], r[1]))
except Exception as e:
    print("   ERR", str(e)[:100])

cn.close()
print("\nDONE")
