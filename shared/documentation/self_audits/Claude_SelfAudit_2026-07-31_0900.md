# Claude Self-Audit - 2026-07-31 09:00
Mode: AUTO-FIX safe items

## Auto-fixed this run
- Removed 1 clean git worktree(s)
- Pruned 3 dead .claude.json entries

## Needs your decision
- Large folder C:\CLAUDE\Tools (1912.4 MB) - confirm still in use

## Process & lock hygiene
- [OK] No orphaned MCP processes detected (live-session children are not orphans).
- AUTO-FIX: [OK] No orphaned MCP processes.

## Git worktrees
- C:\CLAUDE: 0 worktree(s)
- C:\QI: 4 worktree(s)
- C:\OC: 3 worktree(s)
- C:\NEXUS: 1 worktree(s)
-    AUTO-FIX: removed 1 clean worktree(s)
- C:\EasyFlow: 2 worktree(s)
- C:\QIH: 1 worktree(s)

## ~/.claude.json hygiene
- 39 project entries, 3 stale worktree entries
- global mcpServers: claude-peers, git, qi-brain
-    AUTO-FIX: pruned 3 dead entries (backup .bak-20260731-090004)

## Working-dir footprint (review for dead weight)
- Tools: 1912.4 MB
- Claude Voice: 28.1 MB
- Dashboard: 8.2 MB

## Temp & backup files
- Temp files in C:\CLAUDE: 0
- Config backups (~/.claude): 4

## AWS access-key age
- Could not list keys (CLI/permissions): 
aws: [ERROR]: An error occurred (AccessDenied) when calling the ListAccessKeys 
