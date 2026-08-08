---
name: bu-hive-verify-without-password
description: "How to functionally verify BU Hive's gated pages without ever handling the user's password, and why a restart must always be confirmed."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cba8b7b4-eb7b-4563-8574-d1c063373228
  modified: 2026-08-03T16:32:56.421Z
---

Every BU Hive page sits behind a login, so verifying a change needs a session — but
never ask for or enter the password. Mint one server-side instead: `auth.start_session(1, ...)`
returns a token; pass it as the `bu_session` cookie (plus any `bu_csrf` value, since
CSRF is double-submit so cookie and form field only need to match each other). Works
with `fastapi.testclient.TestClient` in-process, with `httpx` against the live
`127.0.0.1:8730`, and in the browser pane via `document.cookie`. Revoke the probe
sessions from `auth_sessions` when finished.

**Why:** it gives real end-to-end verification of gated routes with zero credential
handling, and in-process TestClient results alone are not trustworthy — a fresh
process can pass while the long-running instance still serves stale code.

**How to apply:** after editing BU Hive, restart explicitly with
`scripts\BU-Hive-Service.ps1 -Action Restart` and re-check against the *live* port;
never assume auto-reload picked the change up. Read `data\hive-stderr.log` when the
background instance misbehaves. See [[bu-hive-governance-workflow]].
