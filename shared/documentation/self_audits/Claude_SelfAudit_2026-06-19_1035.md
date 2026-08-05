# Claude Self-Audit - 2026-06-19 10:35
Mode: REPORT-ONLY

## Needs your decision
- Orphaned MCP processes present (run guard -CleanOrphans)
- C:\QI: 4 worktrees to prune
- C:\EasyFlow: 13 worktrees to prune

## Process & lock hygiene
- [WARN] 12 orphaned MCP process(es) holding locks. Run -Clean before restart.

## Git worktrees
- C:\CLAUDE: 0 worktree(s)
- C:\QI: 4 worktree(s)
- C:\OC: 3 worktree(s)
- C:\EasyFlow: 13 worktree(s)

## ~/.claude.json hygiene
- 28 project entries, 0 stale worktree entries
- global mcpServers: claude-peers, git, qi-brain

## Working-dir footprint (review for dead weight)
- Dashboard: 8.2 MB

## Temp & backup files
- Temp files in C:\CLAUDE: 0
- Config backups (~/.claude): 3
