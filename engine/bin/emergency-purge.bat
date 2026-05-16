@echo off
REM QI Hive — emergency Telegram purge wrapper
REM Usage:
REM   emergency-purge.bat <chat_id> <start_msg_id> <end_msg_id>
REM   emergency-purge.bat -5161268852 900 1000
REM   emergency-purge.bat -1003942950097 1 100
REM
REM Runs inside WSL as hyosuke so the bot tokens in ~/.openclaw* resolve.

wsl.exe -d Ubuntu-24.04 -u hyosuke -- python3 /mnt/c/QIH/engine/bin/emergency_purge.py %*
