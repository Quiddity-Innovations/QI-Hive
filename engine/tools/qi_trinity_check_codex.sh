#!/bin/bash
# Companion to qi_trinity_check.py — runs inside WSL. Emits one JSON line.
# Kept in a file because $(...) inside an inline `wsl.exe bash -lc` string gets
# mangled on the Windows side (observed 2026-09-08: empty fields, false "0 stale").
CODEX=/home/hyosuke/.npm-global/bin/codex
ver=$($CODEX --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
login=$($CODEX login status 2>&1 | head -1)
total=0; stale=0
for p in $(pgrep -f 'codex mcp-server'); do
  exe=$(readlink /proc/$p/exe 2>/dev/null)
  case "$exe" in
    *codex*) total=$((total+1)); case "$exe" in *"(deleted)"*) stale=$((stale+1));; esac;;
  esac
done
cfg_model=$(grep -E '^\s*model\s*=' ~/.codex/config.toml 2>/dev/null | head -1 | sed -E 's/.*=\s*"([^"]+)".*/\1/')
cfg_sandbox=$(grep -E '^\s*sandbox_mode\s*=' ~/.codex/config.toml 2>/dev/null | head -1 | sed -E 's/.*=\s*"([^"]+)".*/\1/')
listed=$(python3 - <<'PY' 2>/dev/null
import json
d=json.load(open('/home/hyosuke/.codex/models_cache.json'))
ms=d.get('models',d)
ms=sorted([m for m in ms if m.get('visibility')=='list'],key=lambda m:m.get('priority',99))
print(','.join(m['slug'] for m in ms))
PY
)
printf '{"version":"%s","login":"%s","mcp_native_procs":%d,"mcp_stale_procs":%d,"config_model":"%s","config_sandbox":"%s","listed":"%s"}\n' \
  "$ver" "$login" "$total" "$stale" "$cfg_model" "$cfg_sandbox" "$listed"
