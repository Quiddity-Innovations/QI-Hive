@echo off
REM One-click wrapper — wires Tasuke + Kaze to Cloudflare Workers AI.
REM Runs the bash setup script inside WSL Ubuntu-24.04.

echo Wiring OpenClaw (Tasuke + Kaze) to Cloudflare Workers AI...
echo (If 'expect' needs to be installed, you may be prompted for sudo password.)
echo.
wsl -d Ubuntu-24.04 -- bash /mnt/c/QIH/engine/bin/openclaw_qi_patches/wire_openclaw_cloudflare.sh
echo.
echo Done. Check output above for status.
pause
