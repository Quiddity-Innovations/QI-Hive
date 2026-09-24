"""
NEXUS rename wave - rewrite live references to the 3 NEXUS service names.

  QI_NEXUS       -> QI_NEXUS_Server
  QI_NEXUSTunnel -> QI_NEXUS_Tunnel
  QI_NexusMCP    -> QI_NEXUS_MCP

Only the files in FILES (reviewed 2026-09-24; history, logs, archives and
point-in-time reports are deliberately left alone). Whole-token, case-sensitive,
idempotent (new names never re-match). Encoding, BOM and line endings preserved.

  python apply_refs.py --dry-run
  python apply_refs.py --apply  --backup <dir>
  python apply_refs.py --revert --backup <dir>
"""
import argparse, json, re, shutil, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

MAP = {"QI_NEXUSTunnel": "QI_NEXUS_Tunnel", "QI_NexusMCP": "QI_NEXUS_MCP", "QI_NEXUS": "QI_NEXUS_Server"}
PAT = re.compile(r"(?<![A-Za-z0-9_])(QI_NEXUSTunnel|QI_NexusMCP|QI_NEXUS)(?![A-Za-z0-9_])")

FILES = [
    # NEXUS repo
    r"C:\APPS\NEXUS\NEXUS_Control.bat", r"C:\APPS\NEXUS\NEXUS_Fix_Service_Path.bat",
    r"C:\APPS\NEXUS\NEXUS_Install.bat", r"C:\APPS\NEXUS\NEXUS_Install_Tunnel.bat",
    r"C:\APPS\NEXUS\NEXUS_Restart.bat", r"C:\APPS\NEXUS\install.py", r"C:\APPS\NEXUS\uninstall.py",
    r"C:\APPS\NEXUS\nexus_mcp.py", r"C:\APPS\NEXUS\ui\tabs\settings.py",
    r"C:\APPS\NEXUS\config\mcp_gateway.json", r"C:\APPS\NEXUS\VERIFY_ClaudeMax.py", r"C:\APPS\NEXUS\CLAUDE.md",
    # QI Hive - operational
    r"C:\QIH\ecosystem\qi_registry.json", r"C:\QIH\engine\tunnels\tunnels.json",
    r"C:\QIH\engine\hive\dashboard\server.py", r"C:\QIH\engine\hive\health_check.py",
    r"C:\QIH\engine\hive\inspector\inspector.py", r"C:\QIH\engine\hive\tools\qi_restart_service.py",
    r"C:\QIH\engine\hive\tools\remove_legacy_services.py", r"C:\QIH\engine\launchers\nexus_mcp_launcher.py",
    r"C:\QIH\engine\gate\rollout_tunnels.py", r"C:\QIH\engine\tunnels\demo_day_startup.py",
    r"C:\QIH\engine\bin\qi_rename_displaynames.ps1", r"C:\QIH\landing\refresh-tunnels.py",
    r"C:\QIH\scripts\Brain_Cascade_Restart.bat", r"C:\QIH\tools\restart_brain_9011.py",
    r"C:\QIH\qi_session\qi_context_loader.py", r"C:\QIH\qi_session\create_missing_docs.py",
    # QI Hive - docs
    r"C:\QIH\ecosystem\QI_Service_Registry.md", r"C:\QIH\ecosystem\QI_Standards.md",
    r"C:\QIH\ecosystem\QI_Ecosystem_Map.md", r"C:\QIH\ecosystem\QI_Claude_Manager_Guide.md",
    r"C:\QIH\docs\QI_LLM_Hub.md", r"C:\QIH\engine\tunnels\README.md",
    r"C:\QIH\shared\documentation\project_library\NEXUS\source\status_documentation.json",
    r"C:\QIH\shared\documentation\project_library\NEXUS\source\status_features_business.json",
    r"C:\QIH\shared\documentation\project_library\NEXUS\source\status_features_dev.json",
    r"C:\QIH\shared\documentation\project_library\NEXUS\source\status_techstack.json",
    # CLAUDE tools
    r"C:\APPS\CLAUDE\health_check.py", r"C:\APPS\CLAUDE\gen_qih_overview.py",
    r"C:\APPS\CLAUDE\gen_qih_projects_append.py", r"C:\APPS\CLAUDE\Tools\techstack_data.json",
]


def rename_text(t: str) -> tuple[str, int]:
    return PAT.subn(lambda m: MAP[m.group(1)], t)


def load(p: Path):
    raw = p.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    return raw, bom, raw[3:].decode("utf-8") if bom else raw.decode("utf-8")


def backup_path(backup: Path, p: Path) -> Path:
    return backup / str(p).replace(":", "")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true"); g.add_argument("--apply", action="store_true")
    g.add_argument("--revert", action="store_true")
    ap.add_argument("--backup")
    a = ap.parse_args()
    if (a.apply or a.revert) and not a.backup:
        sys.exit("--backup <dir> is required")
    backup = Path(a.backup) if a.backup else None

    if a.revert:
        n = 0
        for f in FILES:
            b = backup_path(backup, Path(f))
            if b.exists():
                shutil.copy2(b, f); n += 1
        print(f"reverted {n} files from {backup}"); return

    total, errors, changed = 0, [], []
    for f in FILES:
        p = Path(f)
        if not p.exists():
            errors.append(f"missing: {f}"); continue
        try:
            raw, bom, text = load(p)
        except UnicodeDecodeError as e:
            errors.append(f"not utf-8: {f} ({e})"); continue
        new, n = rename_text(text)
        if not n:
            print(f"   0  {f}"); continue
        total += n; changed.append(f)
        print(f"  {n:2}  {f}")
        if a.apply:
            b = backup_path(backup, p); b.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, b)
            p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))
    print(f"{'applied' if a.apply else 'would change'}: {total} references in {len(changed)} files")
    if backup and a.apply:
        (backup / "changed_files.json").write_text(json.dumps(changed, indent=1), encoding="utf-8")
    if errors:
        print("ERRORS:\n  " + "\n  ".join(errors)); sys.exit(1)


if __name__ == "__main__":
    main()
