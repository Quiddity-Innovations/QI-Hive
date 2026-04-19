# QI Hive Reporting

Every QI project's `.claude` folder is wired to report activity back to
the Hive. This is how the Brain stays current and how other agents see
what siblings have been doing.

## Pieces

| Component | Path | Role |
|---|---|---|
| Reporter client | `C:\QIH\engine\common\hive_report.py` | Agents call this — drops JSON into inbox |
| Inbox | `C:\QIH\shared\reports\inbox\` | File-drop queue |
| Ingester | `C:\QIH\engine\hive\ingest\hive_ingest.py` | Reads inbox, updates `data/status.json`, archives |
| Archive | `C:\QIH\shared\reports\archive\` | Processed reports (audit trail) |
| Hookkit template | `C:\QIH\templates\claude_hookkit\` | What each project's `.claude` gets |
| Deployer | `C:\QIH\tools\deploy_hive_reporter.py` | Copies kit into every active project |

## Events

| Event | When | Automated? |
|---|---|---|
| `session_start` | Session opens | ✅ via SessionStart hook |
| `session_end` | Session closes | ✅ via Stop hook |
| `decision` | Significant judgment call | Manual — agent must run |
| `error` | Blocker / failure worth remembering | Manual — agent must run |

## Deploy

```bash
python C:\QIH\tools\deploy_hive_reporter.py
```

Safe to re-run. Merges into existing `.claude\settings.json` without
clobbering other hooks. Skips retired projects.

## Install ingester as a service

```bash
# Run as admin (or via elevation broker)
C:\QIH\engine\bin\nssm.exe install QI_HiveIngest ^
    C:\1-AI\APPS\PYTHON\python.exe ^
    C:\QIH\engine\hive\ingest\hive_ingest.py
C:\QIH\engine\bin\nssm.exe set QI_HiveIngest AppDirectory C:\QIH\engine\hive\ingest
C:\QIH\engine\bin\nssm.exe set QI_HiveIngest Description "QI Hive Ingester — absorbs agent reports into status.json"
C:\QIH\engine\bin\nssm.exe set QI_HiveIngest Start SERVICE_AUTO_START
C:\QIH\engine\bin\nssm.exe start QI_HiveIngest
```

## Verify

1. Drop a test report:
   ```bash
   python C:\QIH\engine\common\hive_report.py session_start --project QI_Hive --summary "smoke test"
   ```
2. Watch `C:\QIH\logs\hive\ingest.log` — should show ingestion within 2s.
3. Check `C:\QIH\data\status.json` → `hive_reports` array for the entry.
4. Original file should now be in `C:\QIH\shared\reports\archive\`.
