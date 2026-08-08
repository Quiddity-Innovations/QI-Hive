# Batch Standardization — Tier-2 (needs your naming call)

Generated 2026-06-23. Tier-1 (12 collision-free launchers) runs automatically Friday.
These need a human naming decision (collisions) or touch a scheduled task.
Approve / edit the **Proposed** column and I'll fold them into the Friday run or a follow-up.

## A. Collision groups (same Product_Role — disambiguated suggestion)

| Current file | Path | Proposed |
|---|---|---|
| install_meeting_service.bat | C:\CLAUDE\Claude Voice\install_meeting_service.bat | `ClaudeVoice_Install_Meeting.bat` |
| install_service.bat | C:\CLAUDE\Claude Voice\install_service.bat | `ClaudeVoice_Install.bat` |
| run_realtime.bat | C:\CLAUDE\Claude Voice\dist\ClaudeVoice_Portable\run_realtime.bat | `ClaudeVoice_Run_Realtime.bat` |
| run_line.bat | C:\CLAUDE\Claude Voice\run_line.bat | `ClaudeVoice_Run_Line.bat` |
| run_meeting.bat | C:\CLAUDE\Claude Voice\run_meeting.bat | `ClaudeVoice_Run_Meeting.bat` |
| run_realtime.bat | C:\CLAUDE\Claude Voice\run_realtime.bat | `ClaudeVoice_Run_Realtime.bat` |
| run_telegram.bat | C:\CLAUDE\Claude Voice\run_telegram.bat | `ClaudeVoice_Run_Telegram.bat` |
| run_webcall.bat | C:\CLAUDE\Claude Voice\run_webcall.bat | `ClaudeVoice_Run_Webcall.bat` |
| setup_named_tunnel.bat | C:\QI\TOOLS\setup_named_tunnel.bat | `Maia_Install_NamedTunnel.bat` |
| setup_service.bat | C:\QI\TOOLS\setup_service.bat | `Maia_Install.bat` |
| install_maia_services.bat | C:\QI\install_maia_services.bat | `Maia_Install.bat` |
| install_watchdog.bat | C:\QI\install_watchdog.bat | `Maia_Install_Watchdog.bat` |
| restart_maia.bat | C:\QI\TOOLS\restart_maia.bat | `Maia_Restart.bat` |
| restart_tunnel_and_update.bat | C:\QI\TOOLS\restart_tunnel_and_update.bat | `Maia_Restart_TunnelUpdate.bat` |
| restart_maiabot.bat | C:\QI\restart_maiabot.bat | `Maia_Restart_Bot.bat` |
| NEXUS_Setup.bat | C:\NEXUS\NEXUS_Setup.bat | `NEXUS_Install.bat` |
| install_nexus_service.bat | C:\NEXUS\install_nexus_service.bat | `NEXUS_Install.bat` |
| install_nexus_tunnel.bat | C:\NEXUS\install_nexus_tunnel.bat | `NEXUS_Install_Tunnel.bat` |
| Start_NEXUS.bat | C:\NEXUS\Start_NEXUS.bat | `NEXUS_Start.bat` |
| Start_NEXUS_Scout_Only.bat | C:\NEXUS\Start_NEXUS_Scout_Only.bat | `NEXUS_Start_ScoutOnly.bat` |
| run_queue.bat | C:\PersonalSong\run_queue.bat | `PersonalSong_Start_Queue.bat` |
| run_server.bat | C:\PersonalSong\run_server.bat | `PersonalSong_Start_Server.bat` |
| Start_TubeScout.bat | C:\TUBESCOUT\Start_TubeScout.bat | `TubeScout_Start.bat` |
| start_server.bat | C:\TUBESCOUT\start_server.bat | `TubeScout_Start_Server.bat` |

## B. Scheduled-task-referenced (task action must be updated too)

| Current file | Used by task | Proposed |
|---|---|---|
| run_bridge_health.bat | QI_ClaudeVoiceBridgeCheck | `ClaudeVoice_Run.bat` |
| start_meeting_room.bat | QI_ClaudeVoiceMeeting_8AM | `ClaudeVoice_Start.bat` |
| run_cycle.bat | QI_TubeScout_AM, QI_TubeScout_PM | `TubeScout_Start.bat` |