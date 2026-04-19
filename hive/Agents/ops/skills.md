# Ops — Skills

## Core Skills

### health-check
Check if a QI service is running.
Input: service name or port
Output: running/stopped, PID, uptime, last log line

### restart-service
Restart an NSSM service.
Input: service name
Rules: always confirm service name in qi_registry.json first; log the restart

### check-ports
List all QI ports and confirm no conflicts.
Reference: C:\QI\ECOSYSTEM\qi_registry.json
Output: port table with status (open/closed/conflict)

### run-nightly-sync
Execute MaiaNightlySync manually if the scheduler failed.
Command: python C:\QI\TOOLS\maia_nightly_sync.py

### check-logs
Read the last N lines of a service log.
Input: service name, line count (default 50)
Output: log tail with timestamp

### disk-check
Report disk usage on C:\ with per-folder breakdown for QI paths.

## Trigger Phrases
- "check if X is running"
- "restart ..."
- "what's the status of ..."
- "run the nightly sync"
- "check the logs for ..."
