@echo off
REM QI Hive — re-inject OpenClaw outbound filter patch after npm upgrade.
REM Runs the Python script inside WSL where the OpenClaw install lives.
echo Running QI Hive OpenClaw filter patch...
wsl -d Ubuntu-24.04 -- python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py
if errorlevel 1 (
    echo.
    echo Patch script reported a problem. Inspect output above.
    exit /b %errorlevel%
)
echo.
echo Restarting OpenClaw gateways...
wsl -d Ubuntu-24.04 -- bash -lc "systemctl --user restart openclaw-gateway openclaw-gateway-kaze && sleep 3 && systemctl --user is-active openclaw-gateway openclaw-gateway-kaze"
echo.
echo Done.
