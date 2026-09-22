# God's Eye View (godseye) — L2 brief

_Generated 2026-09-21 02:35:54_

## Registry facts
- Path: `C:\APPS\Godseye`
- Status: live
- Ports: ui:8780
- Notes: 2026-09-10: installed, registered and fully activated. 6 of 8 providers keyed (Google Maps, OpenAI, Cesium ion, AISstream, NASA FIRMS, TomTom); OpenSky and Launch Library run on their anonymous tiers by choice. All 10 functional checks pass. Maintenance tooling at project root (Godseye.bat + *.mjs); Docker and portable-bundle paths available. Runbook: https://claude.ai/code/artifact/879e5e69-62f2-46a1-99db-98ef2e0da959

## Brain
- Brain offline or unreachable — skipped.

## CLAUDE.md rules
# God's Eye View — QI project notes
## ⚠️ This is VENDORED THIRD-PARTY CODE, not a QI-authored project
## Running it
## Ports and binding — do not widen this
- **Loopback only. Never tunnel this, never bind `0.0.0.0`.** Two reasons, both real:
[line redacted by qi_handoff secret-pattern filter]
[line redacted by qi_handoff secret-pattern filter]
- The app UI and its `/api/*` upstream proxies share **one origin** on purpose. Do not split
  them across ports — the client fetches its own proxy paths same-origin.

## Keys
## Standing constraints
## Max-capability tuning (applied 2026-09-10)
## Ecosystem references
### Accepted validator deviations
`.git/info/exclude`, which is **local-only and never conflicts on `git pull`** — chosen over
editing the tracked `.gitignore` precisely so upstream merges stay clean.

## Verifying camera behaviour in a headless/idle browser pane
`camera.flyTo` starts a tween that never moves. The camera then sits at its last position and
the app looks broken when it is not — this cost a full misdiagnosis on 2026-09-19, where
place-name search was written up as defective and was fine all along.
## Source-order tests need LF
working copy must stay LF — a script that rewrites a source file with CRLF silently breaks these
tests with "… is missing", which reads like a refactor error rather than a line-ending one.
Check with:
## Callsign index — `/api/flight-index`
and `DAL56` are one aeroplane. The IATA form is never stored — translation runs the other way,
and a query for `DL56` expands to `DAL56` on the way in.

   as "last seen N min ago", never as live tracking.

**Restore is cold-start only.** Reading the file is async while harvesting is not, so a poll

## Entry points
`Godseye.bat`, `index.html`, `vite.config.js`
