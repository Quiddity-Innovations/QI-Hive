# Hive Reporting Obligation (applies to this project)

This project is part of the **QI Hive**. Every Claude session in this
project MUST report activity to the Hive so other agents and the Brain
stay current.

## What you must do

1. **At session start**, run:
   ```bash
   python C:\QIH\engine\common\hive_report.py session_start --project <PROJECT_ID> --summary "starting"
   ```

2. **When you make a significant decision** (architecture choice, trade-off,
   renamed service, dropped a feature), run:
   ```bash
   python C:\QIH\engine\common\hive_report.py decision --project <PROJECT_ID> --summary "<what + why>"
   ```

3. **At session end**, ALWAYS run:
   ```bash
   python C:\QIH\engine\common\hive_report.py session_end --project <PROJECT_ID> ^
       --summary "<1-2 sentence recap>" ^
       --json "{\"files_changed\": [...], \"next_steps\": [...]}"
   ```

4. **When an error or blocker surfaces** that future agents should know:
   ```bash
   python C:\QIH\engine\common\hive_report.py error --project <PROJECT_ID> --summary "<what broke>"
   ```

The SessionStart/SessionEnd hooks in `.claude/settings.json` of this
project automate #1 and #3 — you only need to run #2 and #4 manually
when they happen.

## Why

The Hive's Brain merges these reports into `C:\QIH\data\status.json`
and surfaces them on the dashboard. Without reports, other agents see
stale state and duplicate work. Skipping reports breaks the partnership.

## Reference
- Client: `C:\QIH\engine\common\hive_report.py`
- Inbox:  `C:\QIH\shared\reports\inbox\`
- Docs:   `C:\QIH\docs\QI_Hive_Reporting.md`
