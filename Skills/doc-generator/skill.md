# doc-generator

Generate or update QI project documentation files.

## When to use
- When Renne says "update the docs", "update all", or "document this"
- After a significant feature is built
- When a new module, API endpoint, or config option is added

## Documents managed

### Implementation Log
File: `C:\{PROJECT}\DOCUMENTATION\{Project}_Implementation_Log.docx`
Format: dated table entries (Date | What Was Built | Files Changed | Status)

### Meeting Minutes
File: `C:\{PROJECT}\DOCUMENTATION\{Project}_Meeting_Minutes.docx`
Format: dated entries (Date | Attendees | Decisions | Next Steps)

### Version History
File: `C:\{PROJECT}\DOCUMENTATION\{Project}_Version_History.docx`
Format: version table (Version | Date | Change Summary | Type)
Version bump rules: patch for bug fixes, minor for features, major for breaking changes

## Process

1. **Determine which document(s)** need updating from context
2. **Read the existing file** (last 2 pages minimum) to match style and continuation
3. **Write a new dated entry** — never overwrite old entries
4. **Use python-docx** with proper Heading styles, bold headers, tables
5. **Save** with UTF-8 encoding

## Rules
- Always append, never overwrite
- Date entries with today's date
- Keep entries concise — 2-5 bullet points per entry
- For Version History: increment the patch version by default unless a minor/major change occurred
- Never document "nothing happened" — skip if there's nothing to record

## Output
Updated: C:\{PROJECT}\DOCUMENTATION\{filename}
