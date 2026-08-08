---
name: project-onbase-notetype-decoder
description: "OnBase Note Type genotype→phenotype decoding project — established facts, open bits, and the constraints that cost time to discover"
metadata: 
  node_type: memory
  type: project
  originSessionId: 300547ee-72de-4c14-afe6-73c1f51c8a93
  modified: 2026-08-06T22:54:20.564Z
---

Ongoing work (started 2026-08-06): decode `hsi.notetype` so OnBase documentation
can be generated from database values instead of opening dialogs one by one.
User's framing: genotype (raw row) → phenotype (what the Configuration module
shows). Assets in `C:\AI Temp\onbase-notetype-decoder\` — `notetype_dna.py`
(decoder), `calibrate.py` (14-save batch bit calibration + solver),
`RUN-ME-ON-SQL-BOX.md` (prompt for a SQL-connected box), `full_report.txt`.

**Why:** clicking through 100+ note type dialogs to write documentation is the
pain being eliminated. Related: [[project_documentation_standard]].

**How to apply — facts that cost real effort to establish:**

- `notetypenum` is **NOT portable across environments**. 31 of 112 shared names
  have different IDs in UT1_TEST vs UT2_DEV, and 35 IDs denote a *different*
  note type in each (e.g. #199 = GMS Note in DEV, BUPD Redaction in TEST).
  Always key documentation and joins on `notetypename`.
- `notecolor` is a Win32 COLORREF = **BGR**, not RGB: R=v&255, G=(v>>8)&255,
  B=(v>>16)&255. Proven 6–0 against colour-named note types.
- `notedisplayflag` is a bitmask; each option owns a distinct bit so the stored
  value is the sum. **bit 2 (4) = Use for Redaction is confirmed** (7/7 redaction
  types, zero false positives). bit 5 = Movable and bit 15 = Repeat on All
  Revisions are strong. bits 0/7/8/9 inferred. bits 1,4,10,11,12,13,17,20 unknown
  — 4/17/20 are written by the Medical Records / Signature Deficiencies module,
  not the standard Attributes dialog.
- **Hyland publishes the dialog but never the bit values** — not in the Database
  Reference Guide, not on docs.hyland.com. Don't go looking again; the mapping
  must come from seeded note types or measurement.
- Hyland *seeds* note types (`Post-It-Note Green` = #113, `Redaction Pen`,
  `Stamp - Approved`) and the Configuration Module guide screenshots their exact
  attribute state — that documentation is the answer key, no clicking required.
- `hsi.notetype` has 15 columns; the user's original extract had 10 (missing
  `fontnum`, `linestyle`, `linewidth`, `sanntype`, `switchnotetypenum`).
  Security is separate: `hsi.usergnotetype.notetypeprivs`, a 4-bit mask (15=all).
- Never let an export decode `noteflavor` to text — the first extract did, which
  destroyed the raw integers. Export raw.

**MapSnap channel limits (checked, don't retry blindly):** UT1_TEST and UT2_DEV
are Hyland Cloud — no SQL port, config API returns only num+name. `ONBASE` and
`ONBASE13_POC` are live SQL but `mapsnap_table_data` returns 403 (row egress
off); POC profiling JSON at `MapSnapV3\Product\ONBASE13_POC\profile.json` still
holds per-column value distributions. POC is OnBase **13**; production is 25, so
treat its findings as version-suspect. Reflecting over the local Hyland .NET
assemblies for note constants found nothing — they wrap native code.

See [[project_bu_hive]] and [[user_qi_bu_context]] for surrounding context.
