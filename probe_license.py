# -*- coding: utf-8 -*-
"""Read-only probe of OnBase 13 (Nautilus) licensing tables.

SELECT only. Certificate blobs are reported by length/shape, never dumped.
"""
import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pyodbc

# VMware NAT reassigns the guest address after a host reboot or network reset,
# so the host is overridable without editing this file.
HOST = os.environ.get("ONBASE_HOST", "192.168.251.128,1433")
PWD = os.environ.get("ONBASE_SA_PWD", "N@ut1lus")

CONN = ("DRIVER={SQL Server};SERVER=%s;"
        "DATABASE=Nautilus;UID=sa;PWD=%s" % (HOST, PWD))
print("Target: %s  db=Nautilus" % HOST)

cn = pyodbc.connect(CONN, timeout=15)
cur = cn.cursor()
cur.execute("SELECT DB_NAME(), @@SERVERNAME")
print("Connected:", cur.fetchone())
print("=" * 70)

TABLES = ["licensetable", "licensecontrol", "primarylic", "secondarylic",
          "liccertificate", "licensedproduct", "licensedproductcontrol",
          "licenseaffinity", "registereddevices", "registeredusers",
          "emaillicense"]

print("\n### ROW COUNTS")
for t in TABLES:
    try:
        cur.execute("SELECT COUNT(*) FROM hsi.[%s]" % t)
        print("  hsi.%-24s %s" % (t, cur.fetchone()[0]))
    except Exception as e:
        print("  hsi.%-24s ERR %s" % (t, str(e)[:80]))

def dump(sql, title, blobcols=()):
    print("\n### " + title)
    try:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        if not rows:
            print("  (no rows)")
            return
        for i, r in enumerate(rows):
            print("  -- row %d" % (i + 1))
            for c, v in zip(cols, r):
                if c.lower() in blobcols and v is not None:
                    s = str(v)
                    print("     %-22s <len=%d> prefix=%r" % (c, len(s), s[:48]))
                else:
                    print("     %-22s %r" % (c, v))
    except Exception as e:
        print("  ERR", str(e)[:200])

dump("SELECT * FROM hsi.licensedproduct ORDER BY producttype",
     "hsi.licensedproduct  (entitlements)")

dump("SELECT * FROM hsi.primarylic", "hsi.primarylic",
     blobcols=("liccertificate",))

dump("SELECT * FROM hsi.secondarylic", "hsi.secondarylic",
     blobcols=("liccertificate",))

dump("SELECT liccertificatenum, flags, dbvalid, installdate, licensetype, "
     "LEN(CAST(liccertificate AS varchar(max))) AS certlen FROM hsi.liccertificate "
     "ORDER BY liccertificatenum", "hsi.liccertificate (history)")

dump("SELECT * FROM hsi.licensedproductcontrol",
     "hsi.licensedproductcontrol", blobcols=("licensehash", "combinedhash"))

dump("SELECT * FROM hsi.licensecontrol", "hsi.licensecontrol")

dump("SELECT installid, serialnum, customernumber, dbversion, installdate, "
     "licenseflag, dbpatchctrl, exepatchctrl, dbusespaces "
     "FROM hsi.licensetable", "hsi.licensetable (non-PII columns only)")

dump("SELECT * FROM hsi.licenseaffinity", "hsi.licenseaffinity")
dump("SELECT * FROM hsi.registereddevices", "hsi.registereddevices")

# Does systemtableex really mirror the hash?
dump("SELECT licensehash FROM hsi.systemtableex", "hsi.systemtableex.licensehash",
     blobcols=("licensehash",))

# Are there PKs/indexes on these at all?
print("\n### PRIMARY KEYS / UNIQUE INDEXES on license tables")
cur.execute("""
SELECT t.name AS tbl, i.name AS idx, i.is_primary_key, i.is_unique, i.type_desc
FROM sys.indexes i JOIN sys.tables t ON i.object_id=t.object_id
WHERE schema_name(t.schema_id)='hsi'
  AND t.name IN ('licensetable','licensecontrol','primarylic','secondarylic',
                 'liccertificate','licensedproduct','licensedproductcontrol',
                 'registeredusers')
  AND i.type_desc <> 'HEAP'
ORDER BY t.name, i.name""")
rows = cur.fetchall()
if not rows:
    print("  (none - all heaps, no PK/index)")
for r in rows:
    print("  %-24s %-32s pk=%s uniq=%s %s" % (r[0], r[1], r[2], r[3], r[4]))

# Actual declared types (schema.json said int/char - verify)
print("\n### DECLARED TYPES (key columns)")
cur.execute("""
SELECT t.name, c.name, ty.name, c.max_length, c.is_nullable
FROM sys.columns c
JOIN sys.tables t ON c.object_id=t.object_id
JOIN sys.types ty ON c.user_type_id=ty.user_type_id
WHERE schema_name(t.schema_id)='hsi'
  AND t.name IN ('primarylic','licensedproduct','licensecontrol','liccertificate')
ORDER BY t.name, c.column_id""")
for r in cur.fetchall():
    print("  %-18s %-22s %-12s len=%-6s null=%s" % (r[0], r[1], r[2], r[3], r[4]))

cn.close()
print("\nDONE")
