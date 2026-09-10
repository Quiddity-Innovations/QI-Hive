# -*- coding: utf-8 -*-
r"""RETIRED 2026-09-10. This script promoted D:\Dev\<X> -> C:\APPS\<X>.

That direction no longer exists.

The owner ruled on 2026-09-10 that `C:\APPS\<App>` is the app he runs AND the
development source: defects are found in use and fixed in place, git lives
there, sessions open there. `D:\Dev\<App>` is a plain clone of the same remote,
kept as a backup and as the source for deploying to another machine. It is
never edited, so there is nothing in it to promote.

Refreshing a backup is now just:

    git -C D:\Dev\<App> pull

This file was written earlier the SAME DAY, under the retired model, and was a
duplicate of C:\APPS\CLAUDE\Tools\qi_promote.py even then. It is left here as a
refusing stub rather than deleted, because a stub that explains itself is worth
more than a missing file to whatever still calls this path. The original 228
lines are preserved at:

    D:\Dev\_retired\qi_promote_QIH_duplicate_2026-09-10\qi_promote.py

Deploying to a DIFFERENT machine is still a real need, and
`C:\APPS\CLAUDE\Tools\qi_promote.py` is the tool for it.

See section 1.1 of C:\QIH\ecosystem\QI_Standards.md for the tier model.
"""
from __future__ import annotations

import sys

MESSAGE = __doc__


def main() -> int:
    sys.stderr.write(MESSAGE.rstrip() + "\n\n")
    sys.stderr.write(
        "REFUSING TO RUN: there is no D:\\Dev -> C:\\APPS promotion any more.\n"
        "  - to update the backup:      git -C D:\\Dev\\<App> pull\n"
        "  - to deploy to another box:  C:\\APPS\\CLAUDE\\Tools\\qi_promote.py\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
