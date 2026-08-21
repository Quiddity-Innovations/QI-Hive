# -*- coding: utf-8 -*-
"""
Claude Voice — whole-stack power switch.

    python claudevoice_power.py off     # take the entire stack down
    python claudevoice_power.py on      # bring it all back

Written 2026-08-20 for Renne's troubleshooting window: the stack goes off
today and a scheduled task calls `on` on 2026-09-19.

Covers all three layers, because "Claude Voice" is not one process:
  1. Four NSSM services (QI_ClaudeVoiceLine/Telegram/Tunnel/Control)
  2. Two scheduled tasks (BridgeCheck, Meeting_8AM)
  3. Desktop processes in the logged-on session (responder, mic loop,
     session trigger) — driven through the app's own session_watch.py

Services are AUTO_START by default, so `off` also flips them to
DEMAND_START. Without that a reboot during the window would quietly
revive the public LINE and Telegram bots. `on` restores AUTO_START.

Service actions go through the QI_Elevate broker (C:\\QIH\\commands),
so this script does NOT need to run elevated.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"C:\QIH")
from engine.common.qi_elevate_client import run_elevated  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

APP = Path(r"C:\APPS\CLAUDE\Claude Voice")

# The kill switch that makes `off` actually hold. Claude Voice registers a
# GLOBAL Claude Code SessionStart hook (~/.claude/settings.json ->
# session_hook.py start), so every new Claude Code session in any project
# re-armed the stack within seconds of it being killed. Stopping services
# never touched that path. session_hook.py and speak_response.py both check
# this file and no-op while it exists.
DISABLED_FLAG = APP / "data" / "VOICE_DISABLED"

# Stop order is the reverse of start order: the tunnel and bridges come
# down before the control API they report to, and go up after it.
SERVICES_STOP_ORDER = [
    "QI_ClaudeVoiceTunnel",
    "QI_ClaudeVoiceLine",
    "QI_ClaudeVoiceTelegram",
    "QI_ClaudeVoiceControl",
]
SERVICES_START_ORDER = list(reversed(SERVICES_STOP_ORDER))

TASKS = ["QI_ClaudeVoiceBridgeCheck", "QI_ClaudeVoiceMeeting_8AM"]


def _elev(args: list[str]) -> str:
    """One brokered nssm call. Never raises — this is an ops switch, so a
    single failed step must not abandon the remaining ones half-done."""
    try:
        r = run_elevated("nssm", args, submitted_by="claudevoice_power", timeout=60)
        status = r.get("status", "?")
        detail = (r.get("stdout") or r.get("stderr") or "").strip().replace("\x00", "")
        return f"{status} {detail[:90]}".strip()
    except Exception as exc:  # broker down, timeout, bad rule
        return f"ERROR {exc}"


def _task(action: str, name: str) -> str:
    verb = {"enable": "/CHANGE /ENABLE", "disable": "/CHANGE /DISABLE"}[action]
    p = subprocess.run(f'schtasks /TN "{name}" {verb}',
                       shell=True, capture_output=True, text=True)
    return "ok" if p.returncode == 0 else f"ERROR {(p.stderr or p.stdout).strip()[:90]}"


def _kill_meeting_room() -> None:
    """meeting_server.py (:8722) is launched by QI_ClaudeVoiceMeeting_8AM via a
    .bat, so it detaches — disabling the task leaves a running instance behind.
    Nothing else reaps it, so `off` has to."""
    ps = ("Get-CimInstance Win32_Process | "
          "Where-Object {$_.CommandLine -match 'meeting_server|ClaudeVoice_Start_MeetingRoom'} | "
          "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -EA SilentlyContinue; $_.ProcessId }")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
        hit = " ".join((p.stdout or "").split())
        print(f"  meeting room (:8722)    : {'killed ' + hit if hit else 'not running'}")
    except Exception as exc:
        print(f"  meeting room (:8722)    : ERROR {exc}")


def _desktop(action: str) -> None:
    """The mic loop / responder / trigger live in the interactive session.
    Only meaningful when this runs as the logged-on user."""
    if not APP.is_dir():
        print(f"  desktop      : SKIP (missing {APP})")
        return
    argv = {"off": [["session_watch.py", "down"], ["session_watch.py", "stop"]],
            "on":  [["session_watch.py", "up"], ["session_watch.py", "start"]]}[action]
    for a in argv:
        try:
            p = subprocess.run([sys.executable, *a], cwd=str(APP),
                               capture_output=True, text=True, timeout=120)
            out = (p.stdout or p.stderr or "").strip().splitlines()
            print(f"  {' '.join(a):24s}: {out[-1] if out else 'done'}")
        except Exception as exc:
            print(f"  {' '.join(a):24s}: ERROR {exc}")


def off() -> None:
    print("Claude Voice -> OFF\n")

    # Order matters: the flag goes down BEFORE anything is killed. Otherwise a
    # Claude Code session opening mid-shutdown re-arms the stack behind us.
    DISABLED_FLAG.parent.mkdir(parents=True, exist_ok=True)
    DISABLED_FLAG.write_text(
        "Claude Voice is deliberately disabled.\n"
        "Remove this file (or run: claudevoice_power.py on) to re-enable.\n",
        encoding="utf-8")
    print(f"Kill switch : {DISABLED_FLAG} written")
    print("              (Claude Code session hooks will no longer re-arm the voice stack)\n")

    print("Desktop processes:")
    _desktop("off")
    _kill_meeting_room()

    print("\nScheduled tasks:")
    for t in TASKS:
        print(f"  {t:26s}: {_task('disable', t)}")

    print("\nServices (stop, then pin to DEMAND_START so a reboot won't revive them):")
    for s in SERVICES_STOP_ORDER:
        stop = _elev(["stop", s])
        mode = _elev(["set", s, "Start", "SERVICE_DEMAND_START"])
        print(f"  {s:26s}: stop={stop} | start_mode={mode}")

    print("\nDone. Public LINE + Telegram bots are now offline.")


def on() -> None:
    print("Claude Voice -> ON\n")
    if DISABLED_FLAG.exists():
        DISABLED_FLAG.unlink()
        print(f"Kill switch : {DISABLED_FLAG.name} removed — session hooks may re-arm again\n")

    print("Services (restore AUTO_START, then start):")
    for s in SERVICES_START_ORDER:
        mode = _elev(["set", s, "Start", "SERVICE_AUTO_START"])
        start = _elev(["start", s])
        print(f"  {s:26s}: start_mode={mode} | start={start}")

    print("\nScheduled tasks:")
    for t in TASKS:
        print(f"  {t:26s}: {_task('enable', t)}")

    print("\nDesktop processes:")
    _desktop("on")

    print("\nDone. Verify: http://127.0.0.1:8720/health")


def status() -> None:
    """Read-only truth about the stack. Exists because the dashboard's Ops
    launcher is unreliable (its writes 403 through the tunnel), so there has to
    be one place that reports real state without depending on that UI."""
    import urllib.request

    print("Claude Voice — STATUS\n")
    print(f"Kill switch : {'ENGAGED — stack is held down' if DISABLED_FLAG.exists() else 'off — hooks may arm the stack'}\n")
    print("Services:")
    for s in SERVICES_START_ORDER:
        state = _elev(["status", s]).replace("ok ", "")
        print(f"  {s:26s}: {state or 'unknown'}")

    print("\nScheduled tasks:")
    ps = ("Get-ScheduledTask -TaskName 'QI_ClaudeVoice*' | "
          "ForEach-Object { $_.TaskName + ' = ' + $_.State }")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=60)
        for line in (p.stdout or "").strip().splitlines():
            print(f"  {line.strip()}")
    except Exception as exc:
        print(f"  ERROR {exc}")

    print("\nDesktop processes:")
    # Name -eq 'python.exe' is load-bearing: without it the powershell process
    # running this very query matches its own regex and reports itself.
    ps2 = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
           "Where-Object {$_.CommandLine -match "
           "'realtime\\.py|bridge_responder\\.py|session_watch\\.py|meeting_server\\.py'} | "
           "ForEach-Object { $m=[regex]::Match($_.CommandLine,"
           "'(realtime|bridge_responder|session_watch|meeting_server)\\.py'); "
           "'  ' + $m.Value.PadRight(22) + ' pid ' + $_.ProcessId + '  session ' + $_.SessionId }")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-Command", ps2],
                           capture_output=True, text=True, timeout=60)
        out = (p.stdout or "").strip()
        print(out if out else "  none running")
    except Exception as exc:
        print(f"  ERROR {exc}")

    print("\nHealth:")
    for label, url in (("control  :8720", "http://127.0.0.1:8720/health"),
                       ("meeting  :8722", "http://127.0.0.1:8722/")):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                print(f"  {label}: HTTP {r.status}")
        except Exception as exc:
            print(f"  {label}: down ({type(exc).__name__})")


if __name__ == "__main__":
    action = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    if action not in ("on", "off", "status"):
        sys.exit("usage: claudevoice_power.py [on|off|status]")
    {"off": off, "on": on, "status": status}[action]()
