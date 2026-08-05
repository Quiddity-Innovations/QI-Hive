# Bakeoff — Hermes vs OpenClaw Evaluation Rig

Side-by-side evaluation harness that answers one question: **which local agent harness should QI standardize on — Hermes Agent or OpenClaw?**

Both harnesses are driven against the **same brain** (gpt-oss-20b GGUF served by Ollama at 127.0.0.1:11434), the same task list, and the same rubric, so the only variable is the harness itself.

## How it works

| Piece | Role |
|---|---|
| `bakeoff.yaml` | Task list, runner config and scoring rubric (parsed with PyYAML) |
| `run_hermes.py` | Drives Hermes Agent natively on Windows (`hermes -z`, home `%LOCALAPPDATA%\hermes`) |
| `run_openclaw.py` | Drives OpenClaw inside WSL Ubuntu-24.04 via `wsl.exe` (`openclaw agent`) |
| `tools/domain_mcp.py` | QI-created stdlib-only RDAP domain-lookup MCP tool exposed to both harnesses |
| Audit log | Proves actual tool use per run (no hallucinated tool calls) |

## Status

- Smoke test: **10/10** both sides (2026-07-06)
- Renne runs the full suite and makes the final call
- Result feeds the QI MCP Gateway rollout backlog (native-MCP support check)
