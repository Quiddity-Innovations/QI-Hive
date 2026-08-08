---
name: bu-hive-single-user-scope
description: "BU Hive is Renne's personal single-user dev tool on his own laptop — don't apply multi-user security ceremony or approvals gating to local-only changes"
metadata: 
  node_type: memory
  type: project
  originSessionId: 558dbd34-199c-4c73-93ab-59e061fc7686
  modified: 2026-08-05T22:50:34.039Z
---

BU Hive (`C:\AI\BU Hive`) is Renne's own development, built for himself. He is the
**only** user, and is always the developer and administrator both of BU Hive and of
the laptop it runs on. As of 2026-08-05 there are no other users and no other
machines.

**Why:** I had been treating local-only work — auto-start at logon, admin endpoints
that start/stop OS processes, an Ops tab with restart controls — as a capability
increase needing an `/approvals` proposal and a disabled-by-default flag. For a
single-user tool on the owner's own admin machine that ceremony buys nothing: he
already has full shell and admin rights on everything the endpoint could touch.

**How to apply:** For changes scoped to this laptop, just build them and turn them
on — no approvals proposal, no "behind a flag until you approve", no threat-model
writeup about a browser session controlling local processes. Keep ordinary
engineering hygiene (loopback-only binds, look commands up from the registry by
slug rather than executing client-supplied strings) because it is better code, not
because it is a gate.

This **narrows** [[bu-hive-governance-workflow]] rather than replacing it. That
memory still governs anything touching BU's environment — IIS deployment,
connecting OnBase/SQL data sources, activating committees, inviting real peers.
Those remain BU-gated. The distinction is *local-only* vs *reaches BU*.

Renne flagged the condition to revisit: **if BU Hive ever becomes an app used
across other groups**, that is a conversation to have with him at the time — don't
silently switch postures in either direction. At that point the multi-user concerns
(real authz, threat modelling, approvals on capability changes) come back on the
table. Until he says that has changed, assume single-user.
