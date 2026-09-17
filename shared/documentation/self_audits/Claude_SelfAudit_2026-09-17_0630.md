# Claude Self-Audit - 2026-09-17 06:30
Mode: REPORT-ONLY

## Needs your decision
- 1 stale .claude.json worktree entries
- Large folder C:\APPS\CLAUDE\Tools (1919.2 MB) - confirm still in use
- 6 config backups accumulating - consider trimming oldest

## Process & lock hygiene
- [OK] No orphaned MCP processes detected (live-session children are not orphans).

## Git worktrees
- C:\APPS\CLAUDE: 0 worktree(s)
- C:\OC: 0 worktree(s)
- C:\QIH: 2 worktree(s)

## ~/.claude.json hygiene
- 65 project entries, 1 stale worktree entries
- global mcpServers: claude-peers, git, qi-brain, mapsnap, qi-registry, autopdf, qi-comfy, qi-gemini, codex

## Working-dir footprint (review for dead weight)
- Tools: 1919.2 MB
- Claude Voice: 28.9 MB
- Dashboard: 8.2 MB

## Temp & backup files
- Temp files in C:\APPS\CLAUDE: 0
- Config backups (~/.claude): 6

## AWS access-key age
- Could not list keys (CLI/permissions): 
aws: [ERROR]: An error occurred (NoCredentials): Unable to locate credentials. 
