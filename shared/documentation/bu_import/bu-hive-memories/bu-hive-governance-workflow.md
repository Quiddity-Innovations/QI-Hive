---
name: bu-hive-governance-workflow
description: "How to operate on BU Hive — proceed on low-risk work, route risky/unclear tasks to the Approvals board, never deploy/activate until BU approves"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cc2de692-ea7a-4eb3-bf1e-d64858c196f0
  modified: 2026-08-05T22:50:44.681Z
---

On the BU Hive project (`C:\AI\BU Hive`), Renne wants me to work continuously on
tasks that do **not** risk BU systems, networks, infrastructure, employees, Renne,
or the machine BU Hive runs on. Anything risky or "not so clear" goes to the
in-app **Approvals board** (`/approvals`, admin-only) instead of being actioned —
each item gets **Approve (green) / Deny (red) / Discuss (orange)** buttons. ("Discuss"
is the agreed short label for the old "Need more Discussion".)

**Why:** mirrors the QI Hive governance model; keeps Renne in control of anything
that could touch BU's environment while letting me make progress on safe work.

**How to apply:** Seed flagged tasks via `db.upsert_approval(...)`; informational/
done items use `needs_input=False, status='done'`. Treat **IIS deployment,
activating committees, inviting real peers, and connecting OnBase/SQL data sources**
as BU-gated — *prepare and harness only, never migrate/activate until BU gives the
OK*. See [[bu-hive-architecture]].

**Scope limit (added 2026-08-05):** this applies to work that could reach BU's
environment. It does **not** apply to local-only changes on Renne's own laptop —
see [[bu-hive-single-user-scope]]. Don't route single-user local work to /approvals.
