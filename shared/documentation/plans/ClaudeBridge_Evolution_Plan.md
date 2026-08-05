# 🌉 Claude Bridge — Evolution Plan (efficient · searchable · history)

**Date:** 2026-06-20 · **For:** Renne · **Today's state:** flat `inbox.jsonl` / `outbox.jsonl`, polled by
re-reading the whole file, `.read`/`.spoken` position markers.

## The guiding principle
**Don't make one store do two jobs.** A message bus needs an *ordered, routed queue*; recall needs
*semantic search*. So the bridge becomes **layers**, each the right tool — and the channels keep calling
the same `submit()` / `respond()` API, so nothing upstream changes.

| Layer | Job | Tool |
|---|---|---|
| Transport | move messages in/out, fast, routed, multi-process | **SQLite now → Redis at scale** |
| History | durable, queryable record of every turn | **SQLite (same DB)** → Postgres at scale |
| Search | recall by meaning ("what did we say about BU?") | **ChromaDB** (reuse QI Brain) |
| Resilience | offline queue, retry, local fallback | status column + a small daemon |
| Interface | how channels + the real Claude talk to it | a tiny service + **MCP** (for Claude Desktop) |

## Target schema (one `messages` table)
`id · channel(voice/telegram/line/meeting) · chat · user · direction(in/out) · text ·
status(pending/answered/delivered/failed) · ts · embedding_id`
→ indexed on `(status)` and `(channel,chat,ts)`. This single table is both the **queue** (poll
`WHERE status='pending'`) and the **history** (query by chat/date/person).

## Why each choice
- **SQLite (WAL)** replaces JSONL: transactional, multi-process safe, **indexed** polling (no full-file
  rescans), and it *is* the history — zero new infrastructure, one file. Biggest win for least risk.
- **ChromaDB** alongside: embed each turn on write; `search(query, chat?)` returns relevant past
  messages by meaning. Reuse the **QI Brain** vector store so memory is shared across the ecosystem.
- **Redis (Streams)** only when scaling to many users/the hub: true blocking reads (no polling at all),
  pub/sub, horizontal scale. Pair with **Postgres** for big history.
- **Status column** gives resilience: messages sit `pending` until the real Claude answers; a fallback
  can auto-answer with the local model after a timeout, and failed deliveries retry — no dead-end acks.
- **MCP wrapper**: expose `submit/poll/respond/search` as MCP tools so **Claude Desktop** (or any Claude
  surface) can be the brain, not just this CLI.

## Phased roadmap (low-risk → scale)
1. **Phase 1 — SQLite bus.** Swap JSONL → `bridge.db` (`messages` table, WAL). Indexed poll; add
   `status` + retry; keep the same `bus.submit/respond` API. *(Efficiency + history, instantly.)*
2. **Phase 2 — Semantic memory.** Embed every turn into ChromaDB (reuse QI Brain); add `bus.search()`
   so Claude/agents can recall relevant past context. *(Searchable.)*
3. **Phase 3 — Bridge daemon + MCP.** A small FastAPI service (claude_voice block, ~:8723) owning the DB,
   installed as NSSM `QI_ClaudeBridge`; offline queue + local-fallback-after-timeout; MCP tools for
   Claude Desktop. A simple `/history` + `/search` view to browse past conversations.
4. **Phase 4 — Scale (BU hub).** Redis Streams transport + Postgres history; per-room/SSO auth;
   behind IIS/nginx. This is the hub's foundation.

## Recommendation
Start with **Phase 1 + 2** — SQLite for the pipe & history, ChromaDB for search — which delivers
"efficient, searchable, with history" with almost no new infrastructure. Promote to daemon/MCP (Phase 3)
for always-on + Claude Desktop, and Redis/Postgres (Phase 4) only when BU scale demands it.
