# -*- coding: utf-8 -*-
"""
QI Claude Brain — reusable, CONFIG-DRIVEN "Claude as a chat model" for any QI app.

Companion to qi_mcp_gateway.py, opposite direction:
  * qi_mcp_gateway  = INBOUND  — external AIs use the app as MCP tools
  * qi_claude_brain = OUTBOUND — the app uses real Claude as one of its chat
    brains, WITHOUT an Anthropic API key: headless `claude -p` on Renne's
    subscription (the Claude Voice-proven claude_cli pattern, one-shot).

An adopting app stores in ITS OWN settings:

  "claude_cli": {
    "enabled": true,
    "bin": "C:\\Users\\renne\\.local\\bin\\claude.exe",   // optional; PATH otherwise
    "env_file": "C:\\CLAUDE\\Claude Voice\\secrets\\claude_voice.env",
    "timeout": 150
  },
  "claude_profiles": [                      // one chat-picker entry per profile
    {"id": "dba", "name": "Claude · Senior DBA", "model": "sonnet",
     "enabled": true, "system_prompt": "..."}
  ],
  "show_in_chat": {"claude_cli": true}      // common visibility convention

and routes chat model ids of the form  claude/<profile_id>  to ask_claude().

EGRESS NOTE for adopters: this is a CLOUD call (prompt + context go to
Anthropic). Route it through the app's egress guardrail exactly like any other
cloud model. Never send row data unless the profile's data policy allows cloud.
"""
import os
import shutil
import subprocess
import tempfile

DEFAULT_TIMEOUT = 150


def load_env_file(path: str):
    """KEY=VALUE lines -> os.environ (setdefault). No dependency, no error if missing."""
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def resolve_bin(cfg: dict) -> str:
    """The claude executable: cfg['bin'] if valid, else PATH lookup."""
    b = (cfg or {}).get("bin")
    if b and os.path.exists(b):
        return b
    return shutil.which("claude") or ""


def cli_status(cfg: dict) -> dict:
    """Quick health check for a Settings panel: binary found? version? token set?"""
    load_env_file((cfg or {}).get("env_file", ""))
    claude = resolve_bin(cfg or {})
    if not claude:
        return {"ok": False, "error": "claude CLI not found (set claude_cli.bin or add to PATH)"}
    try:
        pr = subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=20)
        ver = (pr.stdout or pr.stderr or "").strip()[:60]
    except Exception as exc:
        return {"ok": False, "error": f"claude --version failed: {exc}"}
    return {"ok": True, "bin": claude, "version": ver,
            "token_set": bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))}


def ask_claude(system_prompt: str, user_prompt: str, cfg: dict,
               model: str = "sonnet") -> str:
    """One-shot real-Claude answer via headless `claude -p` (subscription, free).
    Raises RuntimeError with a human-readable message on any failure."""
    cfg = cfg or {}
    load_env_file(cfg.get("env_file", ""))
    claude = resolve_bin(cfg)
    if not claude:
        raise RuntimeError("claude CLI not found — set claude_cli.bin in settings")
    args = [claude, "-p", "--output-format", "text",
            "--no-session-persistence", "--model", model or "sonnet"]
    # Windows CreateProcess caps the whole command line at ~32K chars
    # (WinError 206). App-assembled system prompts include schema/doc context
    # and easily exceed that, so only SHORT system prompts ride argv; big ones
    # are embedded in the stdin payload instead (bitten 2026-07-31, MapSnap
    # Schema Explainer on a large profile).
    ARGV_SYSTEM_MAX = 6000
    if system_prompt and len(system_prompt) <= ARGV_SYSTEM_MAX:
        args += ["--append-system-prompt", system_prompt]
    elif system_prompt:
        user_prompt = ("<system-instructions>\n" + system_prompt +
                       "\n</system-instructions>\n\nFollow the system instructions "
                       "above for the conversation below.\n\n" + (user_prompt or ""))
    # NOT --bare: --bare forces ANTHROPIC_API_KEY and would bypass the free
    # subscription token (same reasoning as Claude Voice backends.py).
    try:
        proc = subprocess.run(args, input=user_prompt or "(no message)",
                              capture_output=True, text=True,
                              timeout=int(cfg.get("timeout", DEFAULT_TIMEOUT)),
                              cwd=tempfile.gettempdir())
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Claude CLI timed out after {cfg.get('timeout', DEFAULT_TIMEOUT)}s")
    blob = (proc.stdout or "") + (proc.stderr or "")
    if "Not logged in" in blob or "/login" in blob:
        raise RuntimeError("claude CLI not authenticated headless — run `claude setup-token` "
                           "and put CLAUDE_CODE_OAUTH_TOKEN in the env_file")
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError(f"claude CLI returned nothing (rc={proc.returncode}): "
                           f"{(proc.stderr or '')[:200]}")
    return out


def messages_to_prompts(messages: list) -> tuple:
    """Split a chat-style messages list into (system_prompt, conversation_text)."""
    system = "\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
    convo = []
    for m in messages:
        if m.get("role") == "system":
            continue
        who = "User" if m.get("role") == "user" else "Assistant"
        convo.append(f"{who}: {m.get('content', '')}")
    return system, "\n".join(convo) if convo else "(no message)"
