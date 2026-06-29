# Lottery Wiz — Covering-Design Play-Set Builder

## What is Lottery Wiz?

Lottery Wiz is a combinatorial play-set tool built by **Quiddity Innovations**, born as a deep
covering-design engine for the **Georgia Fantasy 5** lottery (pick 5 numbers from 42) and since
generalised into a **Universal** builder that works for almost any lottery in the world
(Powerball, Mega Millions, EuroMillions, Mega-Sena, Quina, Lotofácil and more).

You pick a reduced pool of numbers, choose how your tickets should cover the combinations inside
that pool, and Lottery Wiz builds the set — a **covering-design wheel** that mathematically
guarantees coverage ("if at least *t* of your pool numbers are drawn, at least one ticket shows a
*t*-match"), a feature-targeted **Structured** set, or a transparent **Curated** set scored by the
game's own historical shape. Every set can then be **backtested** against real draw history and run
through the **Brutal Ledger** — a cost-aware replay that tells you the honest financial truth.

## The Honest Premise

Lottery Wiz is built on one non-negotiable principle, stated everywhere in the app and in the AI's
own system prompt: **covering designs restructure how your tickets cover combinations — they do NOT
change the odds and CANNOT predict draws. The numbers are equiprobable.** The tool is for structure,
coverage, backtesting and brutal honesty about expected value, never for false hope.

## What You Can Do

- **Build a set** four ways: Covering-Wheel (guaranteed *t*-coverage), Structured (feature-targeted,
  low pair overlap), Hybrid (70% structured + 30% diversified), or Curated (drop past draws → drop
  statistical "edges" → score by profile → coverage-aware greedy pick).
- **Backtest** any set against thousands of real historical draws (best-ticket match rate per draw).
- **Run the Brutal Ledger** — replay a fixed set across every draw with real payout math: net P/L,
  ROI, equity curve, tier histogram, best draw, worst losing streak — then compare against thousands
  of random quick-picks (exact multinomial control) and get a blunt AI verdict.
- **Ask Wiz** — a built-in AI assistant (local Ollama or cloud) that can *drive the app*: it emits an
  action block the UI executes, so the AI's set is byte-identical to what the buttons produce.
- **Manage draw data** — auto-update from official feeds, add manually, import CSV, browse/search/delete.
- **Check winners**, **save sets**, **log plays**, and **export** to print / copy / CSV / Excel.
- **Latest Results** dashboard, **Scratch-off EV** tracker, and the **Super Sete** positional game.

## Who Uses Lottery Wiz?

| Role | How they interact |
|---|---|
| **Owner (Renné)** | Builds, backtests, runs the Ledger, edits preset game definitions (owner-key unlocked) |
| **Public visitors** | Use every game, build their own custom lotteries; preset game *definitions* are read-only |
| **Claude Desktop** | Drives Lottery Wiz over MCP (no paid API) via 11 tools in `mcp_server.py` |

## Current Build Status (June 2026)

Lottery Wiz is in **active** use. The Fantasy 5 deep app is fully built; the Universal/multi-game
expansion is largely live; a few games await reliable data sources.

| Area | Status |
|---|---|
| Fantasy 5 deep app (generators, backtest, probability) | ✅ Live |
| Covering-design wheel (guaranteed *t*-coverage) | ✅ Live |
| Curated "Build My Play Set" pipeline (funnel + profile + coverage) | ✅ Live |
| The Brutal Ledger (cost-aware replay + multinomial random control) | ✅ Live |
| Fantasy 5 draw history (4,222 draws, 2015→2026) | ✅ Live |
| Universal app — any-N/k covering wheel + bonus ball | ✅ Live |
| Universal curated builder (auto-derived per-game profile) | ✅ Live |
| Multi-game data (Powerball, Mega Millions, Mega-Sena, etc.) | ✅ Live |
| Live "Get latest results" (data.ny.gov, Caixa, FDJ, community) | ✅ Live |
| Latest Results dashboard (`/results`) + next-draw jackpots | ✅ Live |
| Super Sete positional game (`/supersete`) | ✅ Live |
| Scratch-off EV tracker (`/scratch`) | ✅ Live |
| Ask Wiz AI dock (Ollama local + cloud, SSE, action blocks) | ✅ Live |
| MCP server for Claude Desktop (11 tools) | ⚠️ Built — needs Claude Desktop restart |
| Owner-lock on preset game definitions | ✅ Live |
| Export (Print / Copy / CSV / Excel) | ✅ Live |
| QI_LotteryWiz NSSM service + Cloudflare tunnel | ⚠️ Built — user must run installers (UAC) |
| SuperEnalotto / EuroJackpot / UK Lotto / 6-49 data | 🗓️ Planned — need verified sources (CSV works) |
| Powerball / EuroMillions next-draw jackpot line | 🗓️ Planned — no reliable free feed found |

## Architecture in One Breath

A single FastAPI app (`server.py`, ~1,300 lines, port 8777) serves four browser apps (Fantasy 5,
Universal, Super Sete, Scratch) and ~45 JSON endpoints. The math lives in two pure-Python engines —
`engine_py.py` (Fantasy 5: pick 5 of 42) and `lottery_general.py` (any N/k + bonus ball) — shared
by the server, the browser (mirrored in `engine.js`), and the MCP server. Draw history is plain JSON
(`Fantasy5/draws_store.json` + per-game `data/draws/<id>.json`); plays, saved sets and scratch data
are SQLite. `live_sources.py` fetches fresh draws from official and community feeds.

## The Vision

One honest tool for every lottery: pick your pool, cover it well, backtest it against reality, and
see the brutal financial truth — with an AI that explains the math plainly and never pretends it can
predict the draw.

---
*This page is editable at `C:\Lottery Wiz\INTRO\status_intro.md` — save and click Refresh to update.*
