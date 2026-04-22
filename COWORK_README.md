# QI Hive & QI Brain — the 60-second answer for CoWork

*(Read this once per session. It tells you what exists, where it lives, and how to report to it.)*

## 1. What is it?

**QI Hive** and **QI Brain** are a **custom local system** Renne built. Not a SaaS, not a note-taking app. Two pieces:

| Component | What it is | Runs as | Port |
|---|---|---|---|
| **QI Brain** | FastAPI + SQLite + ChromaDB memory store — logs every decision, feature, session across all QI projects | Windows service `QI_BrainAPI` | `http://127.0.0.1:9010` |
| **QI Hive Dashboard** | FastAPI + AdminLTE web UI over QI Brain — the human view of everything | Windows service `QI_Dashboard` | `http://127.0.0.1:8600` |

Everything lives on disk under **`C:\QIH\`**. Source: https://github.com/Quiddity-Innovations/QI-Hive.

## 2. How does CoWork report to it?

Three options, pick whichever fits your tooling:

### Option A — HTTP POST to the Brain (preferred)

```
POST http://127.0.0.1:9010/api/inbox
Content-Type: application/json

{
  "source":     "cowork",
  "type":       "session",
  "project_id": "<project-this-session-was-about>",
  "payload": {
    "session_title": "F: drive dupe scan",
    "summary":       "Scanned F:, found X dupes totalling Y GB. Recommended actions in next_steps.",
    "next_steps":    "Delete confirmed dupes in F:\\_DUPES_QUARANTINE after Renne reviews."
  }
}
```

Valid `type` values: `session`, `decision`, `brain_update`, `state_update`, `task_create`, `scope_drop`, `note`.

### Option B — Drop a JSON file into the inbox

Write a file to **`C:\QIH\shared\reports\inbox\cowork_<timestamp>.json`** with the same payload. The `QI_HiveIngest` service watches that folder and auto-forwards everything to the Brain.

### Option C — Save a Word summary (the universal fallback)

If all else fails, write `CoWork_Summary_YYYY-MM-DD_HHMM.docx` to:

**`C:\UNIVERSAL\DOCUMENTATION\Session_Summaries\`**

(Being migrated to `C:\QIH\shared\documentation\session_summaries\` — write to whichever exists; `robocopy` keeps them in sync.) Renne reads from that folder directly.

## 3. What about QI Brain from CoWork's side?

CoWork **does not need** to install anything. No SDK, no MCP, no auth. Just `curl`/`Invoke-WebRequest` to the HTTP endpoint above when you want to report something. If port 9010 is unreachable, fall back to Option B or C.

## 4. Quick test that Brain is alive

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:9010/health
# → {"status":"ok","service":"qi_brain","port":9010,"version":"001"}
```

## 5. What CoWork sessions should always do

1. On session start: **skip** calling QI Brain. Just work the task.
2. On session end: **POST one session record** to `/api/inbox` per option A (1 request, <1s).
3. If Renne makes a decision during the session worth remembering, also POST a `decision` record.

That's it. You now know everything you need.

---

**Renne's paste-me line for CoWork (save this in CoWork's persistent instructions if possible):**

> Read `C:\QIH\COWORK_README.md` before answering "what is QI Hive" or "how do I report to it". It contains the full definition, endpoints, and fallback paths.
