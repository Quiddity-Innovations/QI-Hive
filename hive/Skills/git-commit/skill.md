# git-commit

Stage, commit, and push all session changes for the active QI project.

## When to use
- When Renne says "commit", "push", or "update all"
- At session end after session-summary is saved
- After any significant code change is complete

## Process

1. **Identify the project repo** from current working directory or context
2. **Check git status** — list staged and unstaged changes
3. **Check git diff** — understand what actually changed
4. **Read recent commit messages** — match the existing style
5. **Stage relevant files**:
   - Add all modified .py, .md, .json, .sql, .yaml files
   - Add DOCUMENTATION changes
   - Never add: .env, credentials, *.key, secrets.*
6. **Write commit message**:
   - Format: imperative mood, present tense
   - First line: 50 chars max summary
   - Body: brief "why" if needed
   - Always append: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`
7. **Commit and push** to origin

## Rules
- Never skip hooks (--no-verify)
- Never force push to main/master — warn user instead
- Never commit: .env, api keys, secrets, credentials
- Prefer specific file staging over `git add -A`
- Use HEREDOC for commit message to avoid encoding issues

## Example commit message format
```
feat: add 6-agent folder structure to Claude Manager

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
