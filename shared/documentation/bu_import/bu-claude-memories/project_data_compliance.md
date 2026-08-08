---
name: project-data-compliance
description: "No student or staff data flows through BU Hive, ClaudeVoice, or any project; user will fully comply if that ever changes"
metadata: 
  node_type: memory
  type: project
  originSessionId: 28368428-30ce-461d-a0a6-2984c5c7a709
---

No **student or staff data** flows through BU Hive, ClaudeVoice, or any of the user's projects. Treat the cleartext `inbox.jsonl`/`outbox.jsonl` and similar local stores as carrying only non-sensitive content under current conditions.

**Why:** The user confirmed (2026-06-22) there is no FERPA/PII data in scope, so blanket compliance warnings are noise and should not be raised reflexively.

**How to apply:** Do not pepper responses with unsolicited FERPA/data-handling caveats. IF a real change ever introduces student/staff/PII data into a pipeline, flag it once and the user will comply and perform whatever steps maintain compliance. Compliance is a shared priority, not an afterthought.

Relates to [[project-bu-hive]], [[project-claude-voice]], [[user-qi-bu-context]].
