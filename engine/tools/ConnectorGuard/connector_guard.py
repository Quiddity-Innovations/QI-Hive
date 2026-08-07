# AI-GENERATED BEGIN (Claude Code, 2026-08-06)
"""QI MCP Connector Guard — keeps local MCP servers registered in Claude Desktop.

Claude Desktop rewrites %APPDATA%\\Claude\\claude_desktop_config.json from its
in-memory model on save, which can drop the whole mcpServers block (observed
repeatedly on the BU work laptop, roughly every ~20 min of active use). Writing
the config once is therefore never a fix — this guard reconciles it on a
schedule.

Design rules (each one is a lesson from a real failure):
  * Manifest-driven (connectors.json) — ALL entries reconciled together, never
    a hardcoded single connector name (a one-name watcher silently loses every
    other connector).
  * A heartbeat file is stamped every cycle so --status can prove the guard
    itself is alive (an unsupervised watcher once died and left no trace).
  * Timestamped backup of the live config before every write; backups pruned.
  * Entries in the live config that are NOT in the manifest are left strictly
    alone, as is every non-mcpServers key (Desktop stores trusted-folder and
    UI state in this file).
  * requires:[] — if any listed path is missing, the entry is SKIPPED for the
    cycle (a registered-but-broken connector shows as permanently failed in
    Desktop, which is worse than absent).
  * {file:<path>} placeholders in args are replaced with the file's trimmed
    contents at register time, so a secret lives in exactly one place on disk.
  * Log is size-capped (real rotation — the BU version claimed rotation but
    only ever appended).

Usage:
  python connector_guard.py            # one reconcile cycle (what the task runs)
  python connector_guard.py --status   # manifest vs live diff + heartbeat age
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "connectors.json"
LIVE = Path(r"C:\Users\renne\AppData\Roaming\Claude\claude_desktop_config.json")
BACKUPS = HERE / "backups"
LOGS = HERE / "logs"
LOGFILE = LOGS / "guard.log"
HEARTBEAT = LOGS / "heartbeat.txt"
KEEP_BACKUPS = 20
LOG_CAP_BYTES = 512 * 1024


def log(msg: str):
    LOGS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with LOGFILE.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {msg}\n")
    if LOGFILE.stat().st_size > LOG_CAP_BYTES:
        lines = LOGFILE.read_text(encoding="utf-8").splitlines()
        LOGFILE.write_text("\n".join(lines[len(lines) // 2:]) + "\n", encoding="utf-8")


def expand_placeholders(args):
    out = []
    for a in args:
        m = re.fullmatch(r"\{file:(.+)\}", a)
        out.append(Path(m.group(1)).read_text(encoding="utf-8").strip() if m else a)
    return out


def desired_entries():
    """Manifest -> {name: desktop_entry}, honoring enabled + requires."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    desired, skipped = {}, []
    for name, spec in manifest.get("connectors", {}).items():
        if not spec.get("enabled", False):
            continue
        missing = [p for p in spec.get("requires", []) if not Path(p).exists()]
        if missing:
            skipped.append((name, missing))
            continue
        desired[name] = {
            "command": spec["command"],
            "args": expand_placeholders(spec.get("args", [])),
        }
    return desired, skipped


def backup_live():
    BACKUPS.mkdir(exist_ok=True)
    dest = BACKUPS / f"claude_desktop_config.{time.strftime('%Y-%m-%d_%H%M%S')}.json"
    shutil.copy2(LIVE, dest)
    old = sorted(BACKUPS.glob("claude_desktop_config.*.json"))
    for f in old[:-KEEP_BACKUPS]:
        f.unlink()
    return dest


def reconcile():
    desired, skipped = desired_entries()
    for name, missing in skipped:
        log(f"SKIP {name}: missing required paths {missing}")

    live = json.loads(LIVE.read_text(encoding="utf-8"))
    servers = live.get("mcpServers") or {}
    wrong = {n: e for n, e in desired.items() if servers.get(n) != e}
    if not wrong:
        HEARTBEAT.parent.mkdir(exist_ok=True)
        HEARTBEAT.write_text(time.strftime("%Y-%m-%d %H:%M:%S") + " ok\n", encoding="utf-8")
        return 0

    backup = backup_live()
    servers.update(wrong)  # only manifest entries; everything else untouched
    live["mcpServers"] = servers
    tmp = LIVE.with_name(LIVE.name + ".guard.tmp")
    tmp.write_text(json.dumps(live, indent=2, ensure_ascii=False), encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))  # sanity reparse before replace
    tmp.replace(LIVE)
    log(f"RESTORED {sorted(wrong)} (backup: {backup.name})")
    HEARTBEAT.parent.mkdir(exist_ok=True)
    HEARTBEAT.write_text(time.strftime("%Y-%m-%d %H:%M:%S") + f" restored {sorted(wrong)}\n",
                         encoding="utf-8")
    return len(wrong)


def status():
    desired, skipped = desired_entries()
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    servers = live.get("mcpServers") or {}
    print(f"manifest: {MANIFEST}")
    for name, entry in desired.items():
        state = "OK" if servers.get(name) == entry else (
            "WRONG" if name in servers else "MISSING")
        print(f"  {name:20s} {state}")
    for name, missing in skipped:
        print(f"  {name:20s} SKIPPED (requires missing: {missing})")
    unmanaged = sorted(set(servers) - set(desired))
    if unmanaged:
        print(f"  unmanaged entries preserved: {unmanaged}")
    if HEARTBEAT.exists():
        age = time.time() - HEARTBEAT.stat().st_mtime
        print(f"heartbeat: {HEARTBEAT.read_text(encoding='utf-8').strip()} ({age/60:.1f} min ago)")
        if age > 900:
            print("WARNING: heartbeat older than 15 min — is the scheduled task running?")
    else:
        print("heartbeat: NEVER — guard has not completed a cycle yet")


if __name__ == "__main__":
    if "--status" in sys.argv:
        status()
    else:
        try:
            reconcile()
        except Exception as exc:  # never crash silently — leave a trace
            log(f"ERROR {type(exc).__name__}: {exc}")
            raise
# AI-GENERATED END
