# God's Eye View (godseye) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\Godseye`
- Status: live
- Ports: ui:8780
- Notes: 2026-09-10: installed, registered and fully activated. 6 of 8 providers keyed (Google Maps, OpenAI, Cesium ion, AISstream, NASA FIRMS, TomTom); OpenSky and Launch Library run on their anonymous tiers by choice. All 10 functional checks pass. Maintenance tooling at project root (Godseye.bat + *.mjs); Docker and portable-bundle paths available. Runbook: https://claude.ai/code/artifact/879e5e69-62f2-46a1-99db-98ef2e0da959

## Brain
- Current state: status=live, phase=Live â€” fully provisioned
  God's Eye View fully operational at C:\APPS\Godseye on port 8780 (loopback-only, no service, no tunnel). All 8 provider keys configured including OpenSky OAuth; all 10 functional checks pass with live data (Google place search resolving "Belo Horizonte", OpenAI realtime voice token minting, 6396 vessels, 164262 fire detections, 30.9KB TomTom flow tiles, 9505 aircraft, 2.6MB TLE, 800 cameras, 24 launches). Maintenance tooling built at project root: Godseye.bat menu plus maintain.mjs / verify-all.mjs / check-keys.mjs / set-key.mjs / make-portable.mjs, all syntax-verified. Two portability paths: a 23KB portable bundle with INSTALL.bat, and Docker/compose (node:24-bookworm-slim, runtime key injection, 127.0.0.1-bound ports). Runbook published at https://claude.ai/code/artifact/879e5e69-62f2-46a1-99db-98ef2e0da959. qi_validator 19/20.
- No project-scoped decisions recorded.

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

## Entry points
`Godseye.bat`, `index.html`, `vite.config.js`
