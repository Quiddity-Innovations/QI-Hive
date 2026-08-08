---
name: mapsnap-onbase-query-capability
description: "MapSnap's MCP gateway on :8651 can query live OnBase TEST/DEV config — check it before saying OnBase is unreachable."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 1987bd7d-0955-459d-a051-5fdb129ec1dc
  modified: 2026-08-03T20:49:08.787Z
---

**Claude can query BU's live OnBase TEST and DEV through MapSnap's MCP gateway.** Do not answer "I have no OnBase access" without checking it first — that was wrong on 2026-08-03 and cost the user two turns to correct.

Gateway: `http://127.0.0.1:8651` (Windows service `MapSnapBU_MCP`; health = `GET /health` → `{"status":"ok"}`). It proxies `MapSnapBU_Web` on `:9876`. Tokens in `C:/MapSnap/config/secrets/` — `mcp_bearer_token.txt` (Claude Code, `Authorization: Bearer`) and `mcp_path_token.txt` (Desktop, rides in the URL as `/c/<token>/mcp`). Never print a token.

**Why it looks absent in a BU Hive session:** `mapsnap-bu` is registered in `~/.claude.json` **project-scoped to `C:/MapSnap` only**, so it does not bind when cwd is `C:/AI/BU Hive`, and it is **not** a plugin (`~/.claude/plugins/repos` is empty). Grepping the BU Hive repo finds nothing and proves nothing. Reach it anyway with direct loopback `POST /mcp` + the bearer header. The user does **not** want mapsnap registered inside BU Hive — do not `claude mcp add` it there.

Profiles: `ONBASE` `ONBASE_UT1_TEST` `ONBASE_UT2_DEV` `ONBASE13_POC` `JENZABAR` `BU_JENZABAR` `DB_REFERENCE_DOCUMENTS`. Tools: `mapsnap_profiles`, `mapsnap_schema`, `mapsnap_ask`, `mapsnap_table_data`, `mapsnap_onbase_documents`, `mapsnap_onbase_config`. `mapsnap_schema`/`mapsnap_table_data` take **`folder`** (not `profile`) — a wrong arg name returns a pydantic validation error.

**These environments are Hyland Cloud — no SQL engine.** The schema lists ~11,450 tables but only 7 are readable live (`LIVE_TABLE_MAP` in `C:/MapSnap/Application/onbase_unity.py`): `customquery`, `filetype`, `itemtype`, `itemtypegroup`, `keytypetable`, `notetype`, `usergroup`. Anything else returns `unavailable` + HTTP 404 — that is by design, **not** a permission block and not a broken service.

For configuration objects prefer **`mapsnap_onbase_config`** with `kind` ∈ doctypes, doctypegroups, keytypes, autofills, customqueries, **useraccounts**, usergroups, notetypes, filetypes. That is the supported way to list OnBase users (UT1_TEST had 89 on 2026-08-03) — `hsi.useraccount` is *not* in `LIVE_TABLE_MAP`, so `mapsnap_table_data` 404s on it even though the pull caches the collection. Use `mapsnap_onbase_documents` for document counts (`hsi.itemdata` is unreadable).

Row values are gated by three independent checks (gateway `tools.table_data`, `allow_row_data` in `config/deploy.json`, and per-profile `ai.data_policy`=`cloud_with_agreement` + `ai.allow_row_egress`); `ONBASE_UT1_TEST` passes all three. Even so, `guardrail.filter_rows_for_egress()` redacts tagged columns and detected PII — email-formatted usernames come back `[REDACTED]`. **Route row data through that guardrail rather than reading `onbase_live_config.json` raw**, so the user's own policy applies instead of being bypassed.

Registering it in Claude Desktop is [[bu-hive-mcp-desktop]]; PII exports still follow [[bu-hive-governance-workflow]].
