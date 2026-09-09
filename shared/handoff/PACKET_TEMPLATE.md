---
from: claude
to: chatgpt        # chatgpt | gemini | other
created: 2026-01-01T00:00:00
task_type: code-review    # code-review | research | file-taxonomy | transcript | other
inputs:
  - path/to/file/or/description
expected_output: A short description of the artifact or answer expected back.
return_path: C:\QIH\shared\handoff\inbox\
redacted: true
---

## Goal

One or two sentences: what is this packet asking the assistant to do.

## Context

Background the assistant needs — links, prior decisions, relevant files
(paste content or summarize; do not paste secrets).

## Constraints

- Scope limits (e.g. read-only, worktree-write only, do not touch X)
- Anything the assistant must NOT do

## Acceptance

How Claude/Renne will know the answer is good enough to use — a test,
a checklist, or a specific format for the reply.
