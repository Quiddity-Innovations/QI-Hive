---
name: project-claude-env-setup
description: "Claude env setup on BU laptop (2026-06-19) — toolchain installed via winget (Scoop blocked), control panel + LLM harness built, all approval-gated items disabled"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0e237849-d68c-493a-8141-011338ec2302
---

Claude working environment was set up on the BU laptop IST-APP-WL-0436 on 2026-06-19 (see `C:\AI\Sessions\code\Claude-Env-Setup_2026-06-19.md`).

Durable, non-obvious facts:
- **Scoop is blocked** by the managed security policy ("Security error" on its bootstrap). Use **winget** for installs on this machine — it is the sanctioned, working path. The installer kit's Scoop-first steps (10/50) fall back to/were replaced by winget.
- **Node** is via nvm-windows; node/npm/pnpm/claude resolve through `C:\nvm4w\nodejs`, which was added to **User PATH** (nvm couldn't add it without elevation). `nvm use` needs an elevated shell.
- **Control panel + LLM harness** built under `scripts/claude-env/control-panel/` and `scripts/claude-env/llm-harness/` in the `claude-env-setup` project. All LLM providers (local Ollama/LM Studio + cloud OpenRouter/Anthropic/OpenAI/Azure/Bedrock/Vertex), dev services, and the Claude CLI are **installed/wired but DISABLED**.
- Runtime toggles + any API keys live at `%USERPROFILE%\.claude-env\feature-flags.json` (gitignored, outside the shareable kit). Prefer the `*Env` env-var fields over plaintext keys.
- **Claude Code CLI 2.1.183** is installed but disabled — blocked pending BU IT written confirmation of coverage (open decision G).
- Latent kit bug: standalone installers ignore `-Yes` for `Confirm-Action` (reads unset `$script:AssumeYes`); affects steps 70/90 run directly.

Git guardrails were already live and were preserved (merge, never overwrite). Relates to [[project-bu-laptop-setup]] and [[user-qi-bu-context]].
