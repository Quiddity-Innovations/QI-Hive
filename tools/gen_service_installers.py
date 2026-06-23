# -*- coding: utf-8 -*-
"""
Generate per-app NSSM install scripts + a single master installer.

Decision (2026-06-15):
  - App SERVICE for: fidelityanalyzer, avatarstudio, personalsong, m2v, tubescout
  - Public TUNNEL only for: m2v, tubescout   (sensitive ones service-only)
  - tubescout already ships install_service_admin.bat -> reuse it
  - MQ skipped (scaffold)

DEPRECATED tunnel path (2026-06-23):
  Quick tunnels (random *.trycloudflare.com) are RETIRED. Public exposure now
  uses STATIC NAMED tunnels on quiddityinnovations.com — defined in
  C:\\QIH\\engine\\tunnels\\tunnels.json and provisioned by
  migrate_named_tunnels.py. M2V is now a named tunnel (qi-m2v -> m2v.
  quiddityinnovations.com), so every APP below is service-only here. The
  tunnel_bat() generator is kept ONLY for reference; do NOT generate new quick
  tunnels. To expose a new app, add an entry to tunnels.json and run:
      python C:\\QIH\\engine\\tunnels\\migrate_named_tunnels.py --only qi-<name>

Each per-app bat self-elevates; the master elevates once and `call`s each
(so the children see admin and don't re-prompt). One UAC click does everything.
"""
from pathlib import Path

NSSM = r"C:\QIH\engine\bin\nssm.exe"
CF   = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"

# app spec: service, appdir, python, params, ports(for echo), tunnel(port or None)
APPS = [
    dict(svc="QI_FidelityAnalyzer", dir=r"C:\FidelityAnalyzer",
         py=r"C:\1-AI\APPS\PYTHON\python.exe", params="main.py",
         desc="Fidelity Portfolio Analyzer - FastAPI :8504 + Gradio UI :7844 (single process).",
         tunnel=None),
    dict(svc="QI_AvatarStudio", dir=r"C:\1-AI\APPS\AvatarStudio",
         py=r"C:\1-AI\APPS\AvatarStudio\.venv\Scripts\python.exe", params="avatar_studio.py",
         desc="QI Avatar Studio - Gradio talking-head video pipeline :7862 (WSL2 render backends).",
         tunnel=None),
    dict(svc="QI_PersonalSong", dir=r"C:\PersonalSong",
         py=r"C:\PersonalSong\.venv\Scripts\python.exe", params="serve.py",
         desc="PersonalSong Studio - local AI song generator web app :8088 (acestep in .venv).",
         tunnel=None),
    dict(svc="QI_M2V", dir=r"C:\M2V",
         py=r"C:\M2V\.venv\Scripts\python.exe", params="main.py",
         desc="M2V Music-to-Video - FastAPI :8501 + Gradio UI :7841.",
         # tunnel=None: M2V is now a STATIC NAMED tunnel (qi-m2v) on
         # quiddityinnovations.com via tunnels.json, not a quick tunnel.
         tunnel=None),
]

ELEV = (
    "net session >nul 2>&1\n"
    "if %errorlevel% neq 0 (\n"
    "  echo Requesting Administrator access...\n"
    "  powershell -Command \"Start-Process '%~f0' -Verb RunAs\"\n"
    "  exit /b\n"
    ")\n"
)

def service_bat(a):
    return f"""@echo off
REM Install {a['svc']} as a persistent, independent Windows service. Double-click + approve UAC.
{ELEV}
set NSSM={NSSM}
set APPDIR={a['dir']}
if not exist "%APPDIR%\\logs" mkdir "%APPDIR%\\logs"

echo Removing any previous {a['svc']}...
"%NSSM%" stop {a['svc']} >nul 2>&1
"%NSSM%" remove {a['svc']} confirm >nul 2>&1

echo Installing {a['svc']}...
"%NSSM%" install {a['svc']} "{a['py']}" {a['params']}
"%NSSM%" set {a['svc']} AppDirectory "%APPDIR%"
"%NSSM%" set {a['svc']} DisplayName "{a['svc']}"
"%NSSM%" set {a['svc']} Description "{a['desc']}"
"%NSSM%" set {a['svc']} Start SERVICE_DEMAND_START
"%NSSM%" set {a['svc']} AppStdout "%APPDIR%\\logs\\service.log"
"%NSSM%" set {a['svc']} AppStderr "%APPDIR%\\logs\\service.log"
"%NSSM%" set {a['svc']} AppRotateFiles 1
"%NSSM%" set {a['svc']} AppRotateBytes 1048576
"%NSSM%" set {a['svc']} AppThrottle 5000
"%NSSM%" start {a['svc']}
timeout /t 4 >nul
"%NSSM%" status {a['svc']}
echo (log: %APPDIR%\\logs\\service.log)
"""

def tunnel_bat(a):
    tsvc = a["svc"] + "Tunnel"
    port = a["tunnel"]
    return f"""@echo off
REM DEPRECATED: quick tunnels (*.trycloudflare.com) are retired. Use a STATIC
REM NAMED tunnel instead — add this app to C:\\QIH\\engine\\tunnels\\tunnels.json
REM and run migrate_named_tunnels.py. This script is kept for reference only.
REM Install {tsvc} - independent public Cloudflare tunnel for {a['svc']} (:{port}). Double-click + approve UAC.
{ELEV}
set NSSM={NSSM}
set CF={CF}
set APPDIR={a['dir']}
if not exist "%APPDIR%\\logs" mkdir "%APPDIR%\\logs"

echo Removing any previous {tsvc}...
"%NSSM%" stop {tsvc} >nul 2>&1
"%NSSM%" remove {tsvc} confirm >nul 2>&1

echo Installing {tsvc}...
"%NSSM%" install {tsvc} "%CF%" "tunnel --protocol http2 --no-autoupdate --url http://localhost:{port}"
"%NSSM%" set {tsvc} AppDirectory "C:\\Program Files (x86)\\cloudflared"
"%NSSM%" set {tsvc} DisplayName "{tsvc}"
"%NSSM%" set {tsvc} Description "Cloudflare quick tunnel exposing {a['svc']} (localhost:{port}). URL in %APPDIR%\\logs\\tunnel.log"
"%NSSM%" set {tsvc} Start SERVICE_DEMAND_START
"%NSSM%" set {tsvc} AppStdout "%APPDIR%\\logs\\tunnel.log"
"%NSSM%" set {tsvc} AppStderr "%APPDIR%\\logs\\tunnel.log"
"%NSSM%" set {tsvc} AppRotateFiles 1
"%NSSM%" set {tsvc} AppRotateBytes 1048576
"%NSSM%" set {tsvc} AppThrottle 5000
"%NSSM%" start {tsvc}
timeout /t 6 >nul
echo Public URL (look for trycloudflare.com):
powershell -Command "Select-String -Path '%APPDIR%\\logs\\tunnel.log' -Pattern 'trycloudflare.com' | Select -Last 1 | ForEach-Object {{ $_.Line }}"
"""

written = []
for a in APPS:
    p = Path(a["dir"]) / "install_service.bat"
    p.write_text(service_bat(a), encoding="utf-8"); written.append(str(p))
    if a["tunnel"]:
        pt = Path(a["dir"]) / "install_tunnel.bat"
        pt.write_text(tunnel_bat(a), encoding="utf-8"); written.append(str(pt))

# Master installer — elevate once, call each child (incl. TubeScout's existing script)
master = Path(r"C:\QIH\tools\install_all_qi_app_services.bat")
calls = []
for a in APPS:
    calls.append(f'echo. & echo === {a["svc"]} === & call "{a["dir"]}\\install_service.bat"')
    if a["tunnel"]:
        calls.append(f'echo. & echo === {a["svc"]}Tunnel === & call "{a["dir"]}\\install_tunnel.bat"')
calls.append('echo. & echo === TubeScout (service + tunnel, existing script) === & call "C:\\TUBESCOUT\\install_service_admin.bat"')
# Honor "all on demand": flip TubeScout app service from AUTO_START to DEMAND_START.
calls.append(f'"{NSSM}" set QI_TubeScout Start SERVICE_DEMAND_START')
master.write_text(
    "@echo off\n"
    "REM ONE-CLICK installer for all missing QI app services + tunnels. Approve the single UAC prompt.\n"
    + ELEV +
    "\n".join(calls) +
    "\necho. & echo === ALL DONE === & pause\n",
    encoding="utf-8")
written.append(str(master))

print("Generated:")
for w in written: print("  ", w)
