"""
QI NSSM Batch 1 — plan builder + stager (no admin needed, changes no service).

Rule (Renne, 2026-09-24): apps are independent but modular.
  * Every service that belongs to an app runs on <AppRoot>\\<App>_NSSM.exe.
  * Hive services run on C:\\QIH\\engine\\bin\\<Label>_NSSM.exe.
  * Display name = service name (drops "QI - " / "QI " forms). Service RENAMES
    (QI_<App>_<Function>) are Batch 2+, one app per wave, with code references.

Outputs batch1_plan.json (read by QI_NSSM_Batch1.ps1) and stages every
relabeled <App>_NSSM.exe copy (fresh copy of the shared nssm.exe + rcedit
FileDescription "<App> Service Manager (QI)"). Re-runnable.
"""
import json, shutil, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
SRC_NSSM = Path(r"C:\QIH\engine\bin\nssm.exe")
RCEDIT = Path(r"C:\QIH\engine\bin\rcedit.exe")
HIVE_BIN = Path(r"C:\QIH\engine\bin")

# label -> folder that holds <label>_NSSM.exe
APPS = {
    "AutoPDF": r"C:\APPS\AutoPDF",
    "AvatarStudio": r"C:\APPS\AvatarStudio",
    "ClaudeVoice": r"C:\APPS\CLAUDE\Claude Voice",
    "CogniBase": r"C:\APPS\CogniBase",
    "ComfyUI": r"D:\AI",
    "Connector": r"C:\APPS\QIP\Connector",
    "CypherMiner": r"C:\APPS\CypherMiner",
    "Decide": r"C:\APPS\QIP\Decide",
    "Gamez": r"C:\APPS\Gamez",
    "Headroom": r"C:\APPS\CLAUDE\Tools",
    "Kaze": r"C:\APPS\OC",
    "OC": r"C:\APPS\OC",
    "LotteryWiz": r"C:\APPS\Lottery Wiz",
    "Maia": r"C:\APPS\QI",
    "MapSnap": r"C:\APPS\MapSnap",
    "MQ": r"C:\APPS\MQ",
    "Naya": r"C:\APPS\NAYA",
    "NEXUS": r"C:\APPS\NEXUS",
    "NoosOrbis": r"C:\APPS\NoosOrbis",
    "RetirementAnalyzer": r"C:\APPS\Retirement Analyzer",
    "TubeScout": r"C:\APPS\TUBESCOUT",
    # Hive (stays in C:\QIH by design)
    "Brain": str(HIVE_BIN), "Hive": str(HIVE_BIN), "Elevate": str(HIVE_BIN),
    "Caddy": str(HIVE_BIN), "Gate": str(HIVE_BIN),
}
HIVE_LABELS = {"Brain", "Hive", "Elevate", "Caddy", "Gate"}

# service -> label. Order in the batch: apps first, Hive after, Elevate last.
OWNER = {
    "QI_AutoPDF": "AutoPDF", "QI_AutoPDFMCP": "AutoPDF", "QI_AutoPDFTunnel": "AutoPDF",
    "QI_AvatarStudio": "AvatarStudio",
    "QI_ClaudeVoiceControl": "ClaudeVoice", "QI_ClaudeVoiceLine": "ClaudeVoice",
    "QI_ClaudeVoiceTelegram": "ClaudeVoice", "QI_ClaudeVoiceTunnel": "ClaudeVoice",
    "QI_CogniBase": "CogniBase", "QI_CogniBaseTunnel": "CogniBase",
    "QI_ComfyUI": "ComfyUI",
    "QI_ConnectorMCP": "Connector", "QI_ConnectorTunnel": "Connector",
    "QI_CypherMinerUI": "CypherMiner", "QI_CypherMinerTunnel": "CypherMiner",
    "QI_Decide": "Decide",
    "QI_FileHQ": "Naya",  # FileHQ was merged into Naya
    "QI_GamezProxy": "Gamez", "QI_GamezQuantProxy": "Gamez", "QI_GamezTunnel": "Gamez",
    "QI_Headroom": "Headroom",
    "QI_KazeConfigAPI": "Kaze", "QI_KazeNewsTunnel": "Kaze",
    "QI_OCKeepalive": "OC",
    "QI_LotteryWiz": "LotteryWiz", "QI_LotteryWizTunnel": "LotteryWiz",
    "QI_MaiaBot": "Maia", "QI_MaiaGradio": "Maia", "QI_MaiaTunnel": "Maia", "QI_MaiaQueueDrain": "Maia",
    "QI_MapSnap": "MapSnap", "QI_MapSnapMCP": "MapSnap", "QI_MapSnapMCPBU": "MapSnap",
    "QI_MapSnapBUSetup": "MapSnap", "QI_MapSnapTunnel": "MapSnap",
    "QI_MQTunnel": "MQ",
    "QI_NayaBot": "Naya", "QI_NayaGradio": "Naya", "QI_NayaMCP": "Naya", "QI_NayaTunnel": "Naya",
    "QI_NEXUS": "NEXUS", "QI_NEXUSTunnel": "NEXUS", "QI_NexusMCP": "NEXUS",
    "QI_NoosOrbis": "NoosOrbis", "QI_NoosOrbisTunnel": "NoosOrbis",
    "QI_RetirementAnalyzer": "RetirementAnalyzer",
    "QI_TubeScout": "TubeScout", "QI_TubeScoutTunnel": "TubeScout",
    # Hive
    "QI_Caddy": "Caddy", "QI_Gate": "Gate", "QI_TaskHealth": "Hive",
    "QI_HiveApply": "Hive", "QI_HiveIngest": "Hive", "QI_HiveInspectorDrain": "Hive",
    "QI_DashboardTunnel": "Hive", "QI_Dashboard": "Hive", "QI_BrainAPI": "Brain",
    "QI_Elevate": "Elevate",
}
# Not touched in Batch 1, with the reason shown in the plan.
SKIP = {
    "QI_PlayDeck": "already independent (own C:\\APPS\\PlayDeck\\engine\\bin\\nssm.exe)",
    "QI_MaiaDemoTunnel": "retired 2026-06-20 and Disabled - candidate for removal (Renne's call)",
}
# Known-broken, flagged for Renne; binary still repointed (harmless) but not started.
FLAGS = {
    "QI_RetirementAnalyzer": "AppDirectory C:\\RetirementAnalyzer does not exist (app is at C:\\APPS\\Retirement Analyzer) - service cannot start today",
}


def services():
    ps = ("Get-CimInstance Win32_Service | Where-Object Name -match '^QI_' | "
          "ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.Name,$_.DisplayName,$_.State,$_.PathName }")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    for line in out.splitlines():
        n, d, s, p = line.split("|", 3)
        yield n, d, s, p.strip().strip('"')


def stage(label: str) -> Path:
    dest = Path(APPS[label]) / f"{label}_NSSM.exe"
    want = f"{label} Service Manager (QI)"
    if not dest.exists():
        shutil.copy2(SRC_NSSM, dest)
    ps = f"(Get-Item -LiteralPath '{dest}').VersionInfo.FileDescription"
    have = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip()
    if have != want:
        subprocess.run([str(RCEDIT), str(dest), "--set-version-string", "FileDescription", want], check=True)
    return dest


def main():
    plan, unknown = [], []
    for name, disp, state, binpath in services():
        if name in SKIP:
            plan.append(dict(name=name, action="skip", reason=SKIP[name], current_bin=binpath, display=disp, state=state))
            continue
        label = OWNER.get(name)
        if not label:
            unknown.append(name); continue
        target = stage(label)
        plan.append(dict(
            name=name, action="repoint", owner=label, hive=label in HIVE_LABELS,
            state=state, restart=(state == "Running" and name not in FLAGS),
            current_bin=binpath, target_bin=str(target),
            current_display=disp, target_display=name, flag=FLAGS.get(name, "")))
    order = lambda r: (r["action"] != "repoint", r.get("hive", False), r["name"] == "QI_Elevate", r["name"].lower())
    plan.sort(key=order)
    (HERE / "batch1_plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")

    rep = [r for r in plan if r["action"] == "repoint"]
    print(f"{len(rep)} to repoint ({sum(r['restart'] for r in rep)} restart), "
          f"{len(plan) - len(rep)} skipped, unknown={unknown}")
    for r in plan:
        if r["action"] == "skip":
            print(f"  SKIP {r['name']:24} {r['reason']}"); continue
        same = "same" if r["current_bin"].lower() == r["target_bin"].lower() else ""
        print(f"  {'H' if r['hive'] else 'A'} {r['name']:24} {r['state']:8} -> {r['target_bin']} {same} "
              f"| display '{r['current_display']}' -> '{r['target_display']}' {('!! ' + r['flag']) if r['flag'] else ''}")
    if unknown:
        sys.exit("Unmapped services - add them to OWNER or SKIP before running Batch 1")


if __name__ == "__main__":
    main()
