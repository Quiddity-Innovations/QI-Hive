# Gamez — World Cup 2026 Betting-Window Dashboard

## What is Gamez?

Gamez (app name **WC2026**) is a single-screen analytics and betting-window dashboard for the FIFA World Cup 2026, built by **Quiddity Innovations**. It is a small, focused tool: one self-contained HTML page (`WC2026.html`) backed by a small FastAPI proxy that fetches live data server-side and serves the page same-origin.

The page shows the live tournament — fixtures, scores, the 12-group standings and the real bracket as teams qualify — and marries a transparent player-strength heuristic with each team's actual form to produce a per-phase **betting window**: which round (Group / R32 / R16 / QF / SF / Final) offers the best information-vs-payout tradeoff. A built-in AI analyst ("The Quant") answers questions strictly from the on-screen panels.

## The Problem We Solve

- Live World Cup data (ESPN, Kalshi market odds) is CORS-blocked from a page opened off disk — the proxy fetches it server-side so the app just works.
- Single-event betting is high variance and easy to misjudge; a structural model makes the round-by-round tradeoff explicit.
- Squad strength is hard to read this far out — the 2026 squads aren't published yet — so the tool maps real EA FC 26 player ratings to national teams as a defensible stand-in.
- Sharing a tool like this normally needs a server; Gamez packages into a portable, self-contained desktop app so a friend can run it with no setup.

## Our Approach

Gamez is deliberately **small and transparent**. The betting math has a fixed, documented shape (`winProb = p^rounds`; `payout = 1/(winProb+fee)`; `value = info × min(1, (1/winProb − 1)/5)`) and the scoring is an openly-explained heuristic, not a black box. A loud disclaimer stays visible at all times: scores assist judgement, they do not predict outcomes, and betting is never guaranteed profitable.

All secrets (API-Football key, OpenRouter key, shared-AI password) live **server-side** in `proxy/config.json` or in the browser's localStorage — never hardcoded in the HTML. The OpenRouter key is shared from Maia's database, so on the owner's machine the AI works with zero extra config.

## Who Uses Gamez?

| Role | How they interact |
|---|---|
| **The owner (Renne)** | Runs the proxy locally (or as the `QI_GamezProxy` service); full access to live data, config editor, and the shared AI ungated. |
| **Friends (via tunnel)** | Open `https://gamez.quiddityinnovations.com`; use the app and the shared AI behind an optional access code, or plug in their own key / local Ollama. |
| **Portable-app users** | Run the bundled `.exe` — a native window that carries the proxy inside it; add their own key in Settings or use Ollama. |

## Current Build Status (June 2026)

Gamez is in **active** development. The core app, proxy, scoring engine and packaging are built and working; live market odds depend on Kalshi listing the markets (they open near the tournament).

| Area | Status |
|---|---|
| Single-file HTML app (`WC2026.html`) — board, matches, standings, bracket, stats, chat | ✅ Live |
| FastAPI proxy serving the app + data endpoints same-origin | ✅ Live |
| Live ESPN fixtures / scores / 12-group standings / real bracket | ✅ Live |
| Player → squad scoring (PPS → SSS), EA FC 26 default source | ✅ Live |
| Betting-window engine (`winProb=p^rounds`, payout, value) | ✅ Live |
| SSS × form marriage into per-match win probability | ✅ Live |
| Multi-provider AI analyst (Ollama / OpenRouter / Anthropic / OpenAI / Google / xAI / Azure / Custom) | ✅ Live |
| OpenRouter proxied server-side with free-model fallback chain | ✅ Live |
| Live Kalshi odds via proxy (public API, server-side) | ⚠️ Built — no WC markets listed by Kalshi yet |
| API-Football deep per-player stats | ⚠️ Built — optional key; 2026 squads not published yet |
| Shared-AI access-code gate (tunnel traffic only) | ✅ Live |
| Portable self-contained app (PyInstaller, windowed + onedir) | ✅ Live |
| Cross-OS CI build (Windows / macOS / Linux) | ✅ Live |
| `QI_GamezProxy` NSSM service + `QI_GamezTunnel` static tunnel | ✅ Live |
| API-Football live 2026 player stats feeding real PPS | 🗓️ Planned — when squads are published |
| GitHub repo (`github: TBD` in registry) | 🗓️ Planned |

## The Betting-Window Idea

The model never claims to predict a winner. It estimates a single per-match win probability `p` for a chosen team (from squad strength married with tournament form), then asks a structural question: to win a bet placed at a given phase, the team must survive a fixed number of rounds (`ROUNDS = Group 6 … Final 1`). `winProb = p^rounds` falls fast for early phases; `payout` rises; an information-quality weight (`INFO`, low at Group, ~1 at the Final) captures how much we actually know by then. The `value` term combines the two — and R16/QF is the structural sweet spot. It is a lens on the tradeoff, not a tip.

## Packaged to Share

The same codebase runs three ways: from `file://` (the HTML alone, degraded — no live data), served by the proxy at `http://localhost:8710/` (full, same-origin), or as a portable `.exe` that bundles the proxy and opens in its own native OS webview window. The bundled config is key-sanitized, and a friend without the shared key can paste their own or run a free local Ollama.

---
*This page is editable at `C:\Gamez\INTRO\status_intro.md` — save and click Refresh to update.*
