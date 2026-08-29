# Claude Self-Audit - 2026-08-28 09:00
Mode: AUTO-FIX safe items

## Auto-fixed this run
- Removed 1 clean git worktree(s)
- Pruned 3 dead .claude.json entries

## Needs your decision
- Large folder C:\APPS\CLAUDE\Tools (3831.9 MB) - confirm still in use

## Process & lock hygiene
- [OK] No orphaned MCP processes detected (live-session children are not orphans).
- AUTO-FIX: [OK] No orphaned MCP processes.

## Git worktrees
- C:\APPS\CLAUDE: 0 worktree(s)
- C:\OC: 3 worktree(s)
- C:\QIH: 3 worktree(s)
-    AUTO-FIX: removed 1 clean worktree(s)

## ~/.claude.json hygiene
- 55 project entries, 3 stale worktree entries
- global mcpServers: claude-peers, git, qi-brain, mapsnap, qi-registry, autopdf, qi-comfy
-    AUTO-FIX: pruned 3 dead entries (backup .bak-20260828-090004)

## Working-dir footprint (review for dead weight)
- Tools: 3831.9 MB
- Claude Voice: 29.1 MB
- Dashboard: 8.3 MB

## Temp & backup files
- Temp files in C:\APPS\CLAUDE: 0
- Config backups (~/.claude): 5

## AWS access-key age
- Could not list keys (CLI/permissions): 
aws: [ERROR]: An error occurred (AccessDenied) when calling the ListAccessKeys 
