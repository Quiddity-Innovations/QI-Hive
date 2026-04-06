# Claude Manager — Project Summary

Claude Manager is Renne's AI development environment — the infrastructure that makes building
all other QI projects faster, smarter, and better coordinated. It is not a product. It is the
workshop where the products are built.

## What it does
- Provides a team of 6 specialized AI agents (Architect, Builder, Scout, Scribe, Ops, Inspector)
- Runs a dashboard at http://localhost:8600 showing the health of all QI projects
- Runs health checks automatically: are services up? is code committed? are docs current?
- Maintains status.json — the live cross-project state file all agents read
- Houses skills that Claude uses to do recurring tasks consistently (session summaries, git commits, docs)
- Integrates claude-peers (agent-to-agent messaging) and OpenSpace (skill evolution) MCPs

## The 6 agents
| Agent | Job | Model |
|---|---|---|
| Architect | Designs features and systems before anyone builds | Sonnet (Opus for major decisions) |
| Builder | Writes the code and runs the scripts | Sonnet |
| Scout | Researches tools, APIs, and AI news | Haiku (fast + cheap) |
| Scribe | Writes all documentation and session summaries | Haiku |
| Ops | Monitors services, restarts things, checks logs | Haiku |
| Inspector | Reviews code and config for security and standards | Sonnet |

## How it works (simple version)
Think of Claude Manager as a fully staffed development office. When Renne has a task,
instead of one AI doing everything, the right specialist handles each part.
The Architect plans it, the Builder builds it, the Inspector checks it, and the Scribe documents it.
The dashboard is the office whiteboard — everyone can see what's happening across all projects.

## Current state
- Dashboard live at port 8600 (manual start — NSSM service pending admin install)
- All 6 agent folders built with soul, skills, and config
- 3 QI skills operational: session-summary, git-commit, doc-generator
- health-check skill operational: runs full ecosystem scan on demand
- claude-peers and OpenSpace MCPs registered

## Path & ports
- Code: C:\Claude\
- Dashboard: port 8600
- No project database (state lives in status.json)
