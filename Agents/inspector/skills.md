# Inspector — Skills

## Core Skills

### review-code
Review Python code for correctness, security, and QI standards.
Output: APPROVED / NEEDS-REVISION / BLOCKED + line-level findings

### review-config
Review JSON or config files for hardcoded secrets, wrong paths, invalid ports.
Output: finding list with severity (low/medium/high/critical)

### review-design
Review an Architect's design before build starts.
Output: approved / send-back + specific concerns

### security-scan
Scan a file or directory for common vulnerabilities.
Checks: SQL injection, command injection, hardcoded secrets, insecure ports, missing input validation

### standards-check
Verify a file or folder follows QI_Standards.md naming and structure conventions.
Reference: C:\QI\ECOSYSTEM\QI_Standards.md

### run-validator
Execute the QI compliance checker.
Command: python C:\QI\ECOSYSTEM\qi_validator.py --project <id>

## Trigger Phrases
- "review ..."
- "check ..."
- "is this safe ..."
- "does this follow standards"
- "approve ..."
