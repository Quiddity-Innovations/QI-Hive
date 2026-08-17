# Quiddity Innovations — Project Standards (QI DNA)
*Every QI project inherits these conventions. No exceptions.*
*Last updated: 2026-04-05*

---

## 1. Project Root Naming

```
C:\<PROJECT_NAME_UPPERCASE>\
```

| Project | Root |
|---|---|
| Maia | `C:\APPS\QI\` |
| Naya | `C:\APPS\NAYA\` |
| NEXUS | `C:\APPS\NEXUS\` |
| OpenClaw | `C:\APPS\OC\` |
| FileHQ | `C:\FileHQ\` |
| Future | `C:\<NAME>\` |

---

## 2. Mandatory Folder Structure

Every QI project MUST have these folders at its root:

```
C:\<PROJECT>\
├── <PROJECT_NAME>_server.py      ← Main server entry point
├── main.py                       ← Alternative entry (NEXUS style)
├── CLAUDE.md                     ← Claude session instructions
├── requirements.txt              ← Python dependencies
├── .gitignore                    ← Must exclude secrets/, *.db, data/
│
├── Quiddity Innovations - <PROJECT> Documentation\
│   ├── User Documentation\
│   ├── Technical Documentation\
│   ├── Business Documentation\
│   ├── Cheatsheets\
│   └── Session Summaries\
│
├── config\                       ← All config files (.json)
├── shared\                       ← Cross-module utilities (db.py, config.py)
├── secrets\                      ← API keys, env files — NEVER committed
├── data\                         ← Runtime data (logs, exports, temp)
│   └── logs\
└── TOOLS\                        ← Utility scripts (optional)
```

---

## 3. Documentation Folder Naming Convention

**Pattern:** `Quiddity Innovations - <PROJECT_NAME> <DOC_TYPE>`

| Folder Name | Contents |
|---|---|
| `Quiddity Innovations - <P> Documentation` | Root documentation folder |
| `...\ User Documentation` | End-user guides, how-to, FAQ |
| `...\ Technical Documentation` | Architecture, API docs, DB schema |
| `...\ Business Documentation` | Proposals, pricing, roadmaps, decisions |
| `...\ Cheatsheets` | Quick reference cards, command lists |
| `...\ Session Summaries` | Auto-saved .docx session summaries |
| `...\ Meeting Minutes` | Decision logs, meeting notes |
| `...\ Implementation Log` | Build history, what was built and when |
| `...\ Version History` | Code version tracking |

**Example (NEXUS):**
```
Quiddity Innovations - NEXUS Documentation\
    User Documentation\
    Technical Documentation\
    Business Documentation\
    Cheatsheets\
    Session Summaries\
    Meeting Minutes\
    Implementation Log\
```

---

## 4. File Naming Conventions

### Documents (.docx)
```
<Project>_<DocType>_<YYYY-MM-DD>.docx
<Project>_Summary_<YYYY-MM-DD>_<HHMM>.docx     ← Session summaries
<Project>_Implementation_Log.docx
<Project>_Meeting_Minutes.docx
<Project>_Version_History.docx
```

Examples:
- `Maia_Summary_2026-04-05_1430.docx`
- `NEXUS_Implementation_Log.docx`
- `QI_Business_Roadmap_2026-04.docx`

### Python files
```
<project>_server.py       ← Main server
<project>_db.py           ← Database layer
<project>_gradio.py       ← UI (legacy style)
<module>.py               ← Feature module (lowercase, snake_case)
```

### Config files
```
<project>.json            ← Main config
providers.json            ← AI provider config (NEXUS/Maia)
<feature>_config.json     ← Feature-specific config
```

### Secrets
```
secrets/<project>.env     ← API keys (NEVER committed)
secrets/<project>.env.template  ← Template (committed, no values)
```

---

## 5. Port Naming Rule

See `qi_registry.json` for the definitive port registry.

**Rule:** Before assigning any new port, check `qi_registry.json`.
**Assign from your project's block.** Never pick a random available port.

### 5.1 Intra-machine HTTP: use `127.0.0.1`, never `localhost`

**Rule:** every service-to-service HTTP call on this machine must use
`http://127.0.0.1:<port>`. Never `http://localhost:<port>`.

**Why:** on this box, IPv6 loopback (`::1`) SYNs are silently **dropped**, not
refused. Windows resolves `localhost` to `::1` first, and Python's `urllib` /
`requests` try addresses **sequentially** — so a `localhost` URL burns its
entire `timeout=` value before falling back to IPv4, on every single call.

This is easy to misdiagnose. `curl` uses parallel Happy Eyeballs, so
curl-testing the same URL looks fast and the delay appears to be in your
application logic.

Verified 2026-08-13: `socket.create_connection(('::1', 9011), timeout=2)` →
`TimeoutError` after 2.007s; `('127.0.0.1', 9011)` → OK in 0.001s. Same on
ports 11434 and 18800.

**Real cost:** one `urlopen("http://localhost:8010/providers")` on the Hive
dashboard's root page cost **2.0s on every page load** and made the NEXUS panel
silently render an error row. Fixing the hostname took the page from 3.30s to
0.10s.

**Symptom to watch for:** an unexplained stall that is a suspiciously round
multiple of a `timeout=` value. Check the hostname before suspecting your code.

---

## 6. Code Standards (Python)

- **Encoding:** Always `encoding='utf-8'` on all file operations
- **stdout:** Always `sys.stdout.reconfigure(encoding='utf-8')` in scripts
- **Windows paths:** Always use raw strings `r"C:\path"` or forward slashes `"C:/path"`
- **DB:** SQLite via `sqlite3`, WAL mode, foreign keys ON
- **Config:** Never hardcode values — always read from DB or config files
- **Secrets:** Never hardcode API keys — always `os.environ.get()` from .env
- **Logging:** Always use `logging` module, never bare `print()` in server code
- **Entry point:** Always `if __name__ == "__main__":` guard

---

## 7. Git Standards

```
Remote:   github.com/Quiddity-Innovations/<PROJECT>  (org)
          or github.com/rennesan/<PROJECT>            (personal, until org repo created)
Branch:   main (or master for older repos)
Commit:   feat: / fix: / docs: / chore: / refactor:
          Always end with: Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**Never commit:**
- `secrets/` folder
- `*.db` files
- `data/logs/`
- `data/responses/`
- Any file named `*.env` (only `*.env.template` is allowed)

---

## 8. Session Summary Standard

Every session must auto-save a Word document:

```
Location:  C:\<PROJECT>\Quiddity Innovations - <PROJECT> Documentation\Session Summaries\
Filename:  Maia_Summary_YYYY-MM-DD_HHMM.docx
```

**Required sections:**
1. Date + session title
2. ✅ Completed This Session
3. 🔄 Next Up (3-5 items)
4. 🚀 In Development
5. 🌅 Future Enhancements
6. 📁 Documents Updated

---

## 9. QI DNA Traits (Every Project Inherits)

These traits must be present in every QI project, no matter what it does:

| Trait | Implementation |
|---|---|
| **API-first** | Every capability exposed via FastAPI REST endpoint |
| **Config-driven** | No hardcoded values — DB or JSON config |
| **Secrets-clean** | All keys in `secrets/*.env`, gitignored |
| **Schema-versioned** | DB has `schema_version` table |
| **QI-branded docs** | `Quiddity Innovations - <P> Documentation\` |
| **Session summaries** | Auto-saved `.docx` after every session |
| **Port registry** | Port declared in `qi_registry.json` before use |
| **CLAUDE.md** | Project instructions for Claude in root |
| **Graceful fallback** | If a dependency is down, degrade gracefully — don't crash |
| **Ecosystem-aware** | Knows its role in the family; can be called by other projects |

---

---

## 10. Shared Infrastructure Safety (NSSM + Cloudflare)

Multiple QI projects run on the same machine and share infrastructure tools (NSSM, cloudflared). Each project **must not harm the others**.

### NSSM Service Naming

Every project owns exactly two NSSM services, named after the project:

| Project | App Service | Tunnel Service |
|---|---|---|
| Maia | `QI_MaiaBot` | `QI_MaiaTunnel` |
| Naya | `QI_NayaBot` | `QI_NayaTunnel` |
| NEXUS | `QI_NEXUS` | `QI_NEXUSTunnel` |
| Dashboard | `QI_Dashboard` | `QI_DashboardTunnel` |
| Brain API | `QI_BrainAPI` | — |

**Rules:**
- A project's control script must only `start` / `stop` / `restart` **its own services**
- Never reference another project's service name in a control script
- Never set `DependOnService` to point at another project's service — use only your own app service as a tunnel dependency

### cloudflared — Never Kill by Process Name

`taskkill /f /im cloudflared.exe` kills **every** cloudflared process on the machine, destroying all running tunnels across all projects.

**❌ FORBIDDEN in any QI control script:**
```bat
taskkill /f /im cloudflared.exe
```

**✅ REQUIRED — kill only the specific tunnel process by PID:**
```bat
"%NSSM%" stop <ProjectTunnel>
for /f "tokens=2" %%p in ('sc queryex <ProjectTunnel> ^| findstr "PID"') do (
    if not "%%p"=="0" taskkill /f /pid %%p >nul 2>&1
)
```

This pattern stops the NSSM-managed service, then kills the specific process by PID — leaving all other cloudflared instances untouched.

### Tunnel Log Files

Each project writes its tunnel log to its **own** LOGS directory:

| Project | Tunnel log |
|---|---|
| Maia | `C:\APPS\QI\LOGS\tunnel_log.txt` |
| Naya | `C:\APPS\NAYA\LOGS\naya_tunnel.log` |
| NEXUS | `C:\APPS\NEXUS\LOGS\nexus_tunnel.log` |

Never point two services at the same log file.

### Checklist Before Writing Any Control Script

- [ ] Only managing my own services (`<MyProject>Service`, `<MyProject>Tunnel`)
- [ ] Using PID-based kill, not `taskkill /f /im cloudflared.exe`
- [ ] Log files go to my project's own `LOGS\` directory
- [ ] No `DependOnService` pointing at another project's service

---

*This document is the QI project constitution.*
*When in doubt about any convention, check here first.*
*When a new convention is established, update this document.*
