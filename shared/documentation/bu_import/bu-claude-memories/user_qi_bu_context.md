---
name: user-qi-bu-context
description: User works at both Boston University (IT/OnBase) and runs Quiddity Innovations — two separate contexts with strict IP separation
metadata: 
  node_type: memory
  type: user
  originSessionId: 815d365b-c45b-41b0-8e56-d6310c70b7a6
---

User (Renne Santiago) operates in two distinct professional contexts that must be kept separate:

**Boston University (BU):**
- Role: IT staff, working with OnBase (Hyland ECM), content management, project management
- Machine: IST-APP-WL-0436 (this laptop) — BU-owned, domain-joined, monitored
- Email: rennesan@bu.edu
- Primary tools: OnBase REST API, Postman, Python/Node.js apps, Claude Code

**Quiddity Innovations (QI) — personal/company:**
- Mature personal dev ecosystem called the "QI Hive": sub-agents, QI Brain (port 9011), MCP servers, QI memory files
- Personal GPU workstation (not this laptop)
- Products include MapSnap, AutoPDF
- QI IP must NOT appear on the BU laptop

**For Claude Code assistance on this laptop:**
- Always assume BU context unless explicitly told otherwise
- All work goes under C:\BU\
- Never reference or suggest copying QI ecosystem files
- OnBase is production data — read-only by default
- No local LLMs — cloud API only
- Guardrails (CLAUDE.md + PreToolUse hooks) are in place and non-negotiable

See [[project-bu-laptop-setup]] for the full technical architecture.
