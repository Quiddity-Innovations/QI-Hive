---
name: feedback-no-loose-scripts-ops-tab
description: Never hand Renne bare Python/CLI commands for operational actions — surface them as controls in the BU Hive Ops tab instead
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d456d9f1-65db-4e56-8649-20ea6b1ff772
  modified: 2026-08-06T23:45:02.429Z
---

Do not offer loose Python scripts or command-line invocations (`python foo.py --status`,
`schtasks ...`) as the way to run or check something operational. Renne runs operations
from the **BU Hive Ops tab** (control plane at 127.0.0.1:8730) — status checks, toggles,
service start/stop, and diagnostics belong there as labelled controls.

**Why:** the Ops tab is the intended Operations Control Panel. A CLI one-liner in chat is
undiscoverable a week later, doesn't survive being forgotten, and splits operational
surface across terminal and UI. Anything worth telling him to run is worth a button.

**How to apply:** when a feature needs an operator action (check status, toggle, restart,
preview output), build it into the Ops tab with a clear label and a plain-language state
readout, then point him at the tab. Keep the CLI path working for debugging, but don't
present it as the interface. Ops controls should be self-describing — a button's purpose
and current state readable without documentation.

Related: [[project-bu-hive]], [[project-claude-voice]], [[project-documentation-standard]]
