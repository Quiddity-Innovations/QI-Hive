"""One-shot forensic scan: how many real Claude Code sessions ever existed?

Each hive report references the transcript file it came from. Transcripts are
deleted by Claude Code's retention timer, but the references are not — so
deduping `transcript` across the report archive recovers an inventory of
sessions that no longer exist on disk.

Note: `session_id` in these records is a per-report UUID, not a session key --
several records can share one transcript. Dedupe on `transcript`.
"""
from __future__ import annotations

import collections
import os
import re
import sys

ARCHIVE = r"C:\QIH\shared\reports\archive"

_T = re.compile(r'"transcript":\s*"([^"]+)"')
_C = re.compile(r'"cwd":\s*"([^"]+)"')
_D = re.compile(r'"session_date":\s*"([^"]+)"')
_S = re.compile(r'"stubbed_at":\s*"([^"]+)"')


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    tx: dict[str, tuple[str, str]] = {}
    for f in os.listdir(ARCHIVE):
        try:
            s = open(os.path.join(ARCHIVE, f), encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = _T.search(s)
        if not m:
            continue
        t = m.group(1).lower()
        d = (_D.search(s).group(1) if _D.search(s) else "") or \
            (_S.search(s).group(1) if _S.search(s) else "")
        c = _C.search(s).group(1) if _C.search(s) else ""
        if t not in tx or (d and d < tx[t][0]):
            tx[t] = (d, c)

    print(f"DISTINCT TRANSCRIPT FILES (real sessions ever recorded): {len(tx):,}")

    proj = collections.Counter()
    mon = collections.Counter()
    for _t, (d, c) in tx.items():
        parts = [p for p in c.replace("/", "\\").split("\\") if p]
        proj[parts[-1] if parts else "?"] += 1
        if d[:7]:
            mon[d[:7]] += 1

    print("\nby project folder:")
    for k, v in proj.most_common(15):
        print(f"  {k:<28} {v:>5,}")
    print("\nby earliest-reference month:")
    for k in sorted(mon):
        print(f"  {k}  {mon[k]:>5,}")

    surviving = 0
    for t in tx:
        if os.path.exists(t):
            surviving += 1
    print(f"\nstill on disk: {surviving:,} / {len(tx):,}  "
          f"-> {len(tx)-surviving:,} transcripts deleted by retention")


if __name__ == "__main__":
    main()
