---
name: project-directory-policy
description: Root directory conventions for all Claude-created projects and documentation
metadata: 
  node_type: memory
  type: project
  originSessionId: c6c812de-32c1-428a-8244-b16bee1c844f
---

Root directories for all Claude work on this machine:

- **C:\AI** — primary root for Claude projects
- **C:\AI Temp** — temporary/scratch root for Claude projects
- **C:\AI\Projects** — where individual projects are created
- **C:\AI\Documentation** — Claude/agent-specific documentation (e.g., setup reports, reference docs)

**Why:** User-established convention to keep all Claude-generated work organized under a consistent root. Applies until further notice.

**How to apply:** Any time Claude creates a new project, defaults the working directory, or saves output files, use these paths. Never default to the Desktop, Downloads, or user home directory. When unsure which subdirectory to use, ask — but always root under C:\AI or C:\AI Temp.
