# -*- coding: utf-8 -*-
"""NSSM runner for QI_MapSnapBUSetup — executes MapSnap BU's setup_iis.ps1
elevated (the service runs as LocalSystem). One-shot semantics with an NSSM
twist: NSSM restarts exited apps, so after running once this script parks in a
sleep loop until the service is stopped.

Contract:
  args file : C:\\QIH\\engine\\launchers\\mapsnap_bu_iis_args.txt
              (PowerShell arguments for setup_iis.ps1, one line, e.g.
               -DeployJson C:\\path\\deploy.json  or  -Uninstall)
  log       : C:\\QIH\\logs\\mapsnap_bu_iis_setup.log   (overwritten per run)
  marker    : C:\\QIH\\logs\\mapsnap_bu_iis_setup.done  (exit code; a run only
              starts when the args file is NEWER than the marker)
To trigger a run: write/touch the args file, then (re)start QI_MapSnapBUSetup.
Dev-machine glue only — NOT shipped in the BU kit."""
import subprocess
import time
from pathlib import Path

ARGS = Path(r"C:\QIH\engine\launchers\mapsnap_bu_iis_args.txt")
LOG = Path(r"C:\QIH\logs\mapsnap_bu_iis_setup.log")
MARK = Path(r"C:\QIH\logs\mapsnap_bu_iis_setup.done")
SCRIPT = Path(r"C:\MapSnap\kit\setup_iis.ps1")
PS = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def should_run() -> bool:
    if not ARGS.exists() or not SCRIPT.exists():
        return False
    if not MARK.exists():
        return True
    return ARGS.stat().st_mtime > MARK.stat().st_mtime


if should_run():
    extra = ARGS.read_text(encoding="utf-8").strip()
    cmd = f'& "{SCRIPT}" {extra} *>&1 | Out-File -FilePath "{LOG}" -Encoding utf8'
    try:
        proc = subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass",
                               "-Command", cmd], timeout=3600)
        rc = proc.returncode
    except Exception as exc:  # noqa: BLE001
        rc = -1
        LOG.write_text(f"runner exception: {exc}", encoding="utf-8")
    MARK.write_text(f"{rc} @ {time.strftime('%Y-%m-%d %H:%M:%S')}", encoding="utf-8")

while True:  # park until the service is stopped
    time.sleep(300)
