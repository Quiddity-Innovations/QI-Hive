# -*- coding: utf-8 -*-
"""Curated Tier-2 batch rename map: collision + scheduled-task-referenced .bat
files given final, per-directory-unique <Product>_<Role>[_Qualifier].bat names.
Validates uniqueness + that no target already exists. 2026-06-23."""
import os, json, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")

# (path, new_name, [scheduled tasks whose Arguments reference this bat])
ENTRIES = [
    # --- Claude Voice (C:\CLAUDE\Claude Voice) ---
    (r"C:\CLAUDE\Claude Voice\run_line.bat",            "ClaudeVoice_Run_Line.bat",        []),
    (r"C:\CLAUDE\Claude Voice\run_meeting.bat",         "ClaudeVoice_Run_Meeting.bat",     []),
    (r"C:\CLAUDE\Claude Voice\run_realtime.bat",        "ClaudeVoice_Run_Realtime.bat",    []),
    (r"C:\CLAUDE\Claude Voice\run_telegram.bat",        "ClaudeVoice_Run_Telegram.bat",    []),
    (r"C:\CLAUDE\Claude Voice\run_webcall.bat",         "ClaudeVoice_Run_Webcall.bat",     []),
    (r"C:\CLAUDE\Claude Voice\run_bridge_health.bat",   "ClaudeVoice_Run_BridgeHealth.bat", ["QI_ClaudeVoiceBridgeCheck"]),
    (r"C:\CLAUDE\Claude Voice\start_meeting_room.bat",  "ClaudeVoice_Start_MeetingRoom.bat", ["QI_ClaudeVoiceMeeting_8AM"]),
    (r"C:\CLAUDE\Claude Voice\install_service.bat",     "ClaudeVoice_Install.bat",         []),
    (r"C:\CLAUDE\Claude Voice\install_meeting_service.bat", "ClaudeVoice_Install_Meeting.bat", []),
    # --- Maia (C:\QI and C:\QI\TOOLS) ---
    (r"C:\QI\restart_maiabot.bat",                      "Maia_Restart_Bot.bat",            []),
    (r"C:\QI\TOOLS\restart_maia.bat",                   "Maia_Restart.bat",                []),
    (r"C:\QI\TOOLS\restart_tunnel_and_update.bat",      "Maia_Restart_TunnelUpdate.bat",   []),
    (r"C:\QI\install_maia_services.bat",                "Maia_Install.bat",                []),
    (r"C:\QI\install_watchdog.bat",                     "Maia_Install_Watchdog.bat",       []),
    (r"C:\QI\TOOLS\setup_service.bat",                  "Maia_Setup.bat",                  []),
    (r"C:\QI\TOOLS\setup_named_tunnel.bat",             "Maia_Setup_NamedTunnel.bat",      []),
    # --- NEXUS (C:\NEXUS) ---
    (r"C:\NEXUS\Start_NEXUS.bat",                       "NEXUS_Start.bat",                 []),
    (r"C:\NEXUS\Start_NEXUS_Scout_Only.bat",            "NEXUS_Start_ScoutOnly.bat",       []),
    (r"C:\NEXUS\install_nexus_service.bat",             "NEXUS_Install.bat",               []),
    (r"C:\NEXUS\install_nexus_tunnel.bat",              "NEXUS_Install_Tunnel.bat",        []),
    # --- PersonalSong (C:\PersonalSong) ---
    (r"C:\PersonalSong\run_queue.bat",                  "PersonalSong_Start_Queue.bat",    []),
    (r"C:\PersonalSong\run_server.bat",                 "PersonalSong_Start_Server.bat",   []),
    # --- TubeScout (C:\TUBESCOUT) ---
    (r"C:\TUBESCOUT\Start_TubeScout.bat",               "TubeScout_Start.bat",             []),
    (r"C:\TUBESCOUT\start_server.bat",                  "TubeScout_Start_Server.bat",      []),
    (r"C:\TUBESCOUT\run_cycle.bat",                     "TubeScout_Run_Cycle.bat",         ["QI_TubeScout_AM", "QI_TubeScout_PM"]),
]

renames, tasks, problems = [], [], []
# per-directory uniqueness of target names
by_dir = {}
for path, new, tlist in ENTRIES:
    d = os.path.dirname(path).lower()
    by_dir.setdefault(d, []).append(new.lower())
    renames.append({"path": path, "current": os.path.basename(path), "new": new})
    if tlist:
        tasks.append({"path": path, "new": new, "tasks": tlist})

for d, names in by_dir.items():
    dup = [n for n, c in Counter(names).items() if c > 1]
    if dup:
        problems.append(f"DUPLICATE in {d}: {dup}")

# existence checks
for r in renames:
    if not os.path.exists(r["path"]):
        problems.append(f"MISSING source: {r['path']}")
    tgt = os.path.join(os.path.dirname(r["path"]), r["new"])
    if os.path.exists(tgt) and os.path.normcase(tgt) != os.path.normcase(r["path"]):
        problems.append(f"TARGET EXISTS: {tgt}")

out = {"generated": "2026-06-23", "tier": 2, "renames": renames, "task_updates": tasks}
json.dump(out, open(r"C:\QIH\tools\naming_standardization\batch_rename_tier2.json",
          "w", encoding="utf-8"), indent=2)

print(f"Tier-2 renames: {len(renames)}  | task-action updates: {len(tasks)}")
if problems:
    print("PROBLEMS:"); [print("  -", p) for p in problems]
else:
    print("OK: all names unique per-dir, all sources exist, no target clashes.")
for r in renames:
    print(f"   {r['current']:32} -> {r['new']}")
