# Gamez (gamez) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `C:\APPS\Gamez`
- Status: active
- Ports: api:8710, quant:8712
- Notes: Standalone betting/analytics tool. Shares the OpenRouter key from C:\APPS\QI\maia.db (like MapSnap). Packaged as a portable .exe for sharing.

## Brain
- Current state: status=active, phase=Correctness & data integrity (post-feature-complete)
  Feature set complete; this pass fixed AI-Analyst/Quant correctness: board grounding (no more deflection), survive-to-title precompute, the DEF/ATT line null bug (pos_group coarse labels) across all 48 WC teams, removal of the per-match-vs-title category error, and a server-side model-vs-market guard. Verified live on prod 8710; merged to main and pushed.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# Gamez — World Cup 2026 Betting-Window Dashboard
## What it is
> **Disclaimer (must always stay visible):** single-event betting is high variance and is NOT guaranteed profitable. Scores are a heuristic; they do not predict outcomes.

## Layout
## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Run
## Keys
- Keys live **server-side** (`proxy/config.json`) or in the browser's localStorage — never hardcoded in the HTML.
- OpenRouter key is shared from `C:\APPS\QI\maia.db` (like MapSnap); free-tier only → `:free` models.
- API-Football key is optional; without it players are clearly labelled **SAMPLE**. Verify a key with `python proxy/test_apifootball.py`.
## Service
## Public tunnel (static)
Exposed at **`https://worldcup.quiddityinnovations.com`** via the static named tunnel **`qi-gamez`** (service `QI_GamezTunnel` → localhost:8710). Hostname changed from `gamez` → `worldcup` on 2026-06-26 (the `gamez` hostname is reserved for a future Gamez hub). Part of the ecosystem-wide static-tunnel design; tooling and master map live in `C:\QIH\engine\tunnels\` (`tunnels.json`). Replaced the old random `*.trycloudflare.com` quick-tunnel scheme (migrated 2026-06-20 after `quiddityinnovations.com` was purchased on Cloudflare). Do NOT create quick tunnels for Gamez — add/adjust the ingress in `tunnels.json` instead.

## Entry points
`WC2026.html`, `build_exe.py`, `build_exe_onedir.py`
