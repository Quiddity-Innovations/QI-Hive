# session-summary

Automatically generate and save a session summary Word document for the active QI project.

## When to use
- At the end of any coding session
- When Renne says "save the session" or "update all"
- Automatically at session end per CLAUDE.md standing instructions

## Process

1. **Determine the active project** from context (Maia=C:\QI, Naya=C:\NAYA, NEXUS=C:\NEXUS, etc.)
2. **Gather session content**:
   - What was built or changed (from tool history and conversation)
   - Decisions made
   - Files modified
   - Next steps discussed
3. **Generate the .docx** using python-docx with this structure:
   - Heading 1: "{Project} Session Summary — {Date}"
   - Heading 2: "✅ Completed This Session"
   - Heading 2: "🔄 Next Up (Immediate Priority)"
   - Heading 2: "🚀 In Development"
   - Heading 2: "🌅 Future Enhancements"
   - Heading 2: "📁 Documents Updated"
4. **Save** to: `C:\{PROJECT}\DOCUMENTATION\Session Summaries\{Project}_Summary_{YYYY-MM-DD_HHMM}.docx`
5. **Update LATEST.md** at `C:\Claude\Session Summaries\LATEST.md` with handoff info
6. **Update status.json** — set last_session, last_updated

## Rules
- Use python-docx, Heading 1/2 styles, bold text, tables where appropriate
- Encoding: always UTF-8
- Never ask permission — just save it
- Print the full file path after saving

## Output
Saved: C:\{PROJECT}\DOCUMENTATION\Session Summaries\{Project}_Summary_{YYYY-MM-DD_HHMM}.docx
