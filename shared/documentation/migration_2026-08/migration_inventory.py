"""Inventory every reference that a C:\\<app> -> C:\\APPS\\<app> move must rewrite.

Read-only. Produces the checklist the migration window works from, so the
window is spent moving files rather than discovering surprises.
"""
import json, os, re, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

NSSM = r"C:\QIH\engine\bin\nssm.exe"
REGISTRY = Path(r"C:\QIH\ecosystem\qi_registry.json")
CLAUDE_JSON = Path(os.path.expanduser("~/.claude.json"))

SYSTEM_DIRS = {
    "windows", "program files", "program files (x86)", "programdata", "users",
    "perflogs", "recovery", "msocache", "system volume information",
    "config.msi", "documents and settings", "onedrivetemp", "$recycle.bin",
    "$winreagent", "intel", "amd", "nvidia", "temp", "tmp",
}


def project_dirs():
    out = []
    for p in sorted(Path("C:/").iterdir()):
        try:
            if not p.is_dir():
                continue
        except OSError:
            continue
        if p.name.lower() in SYSTEM_DIRS or p.name.startswith("$"):
            continue
        out.append(p)
    return out


def nssm_services():
    """Every QI_* service and the paths baked into its configuration."""
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-Service QI_* | Select-Object -ExpandProperty Name"],
                             capture_output=True, text=True, timeout=60)
        names = [n.strip() for n in res.stdout.splitlines() if n.strip()]
    except Exception as exc:
        return [{"error": f"could not list services: {exc}"}]

    rows = []
    for name in names:
        entry = {"service": name}
        for key in ("Application", "AppDirectory", "AppParameters",
                    "AppStdout", "AppStderr", "Start"):
            try:
                r = subprocess.run([NSSM, "get", name, key],
                                   capture_output=True, timeout=30)
                # nssm pads its output with NULs rather than emitting real
                # UTF-16; decoding it as UTF-16 turns ASCII pairs into CJK.
                entry[key] = (r.stdout.replace(b"\x00", b"")
                              .decode("utf-8", "replace").strip())
            except Exception as exc:
                entry[key] = f"<error {exc}>"
        rows.append(entry)
    return rows


def scan_text_refs(paths, roots):
    """Find config/doc files mentioning a moving root path."""
    pattern = re.compile("|".join(re.escape(str(r)) for r in roots), re.I)
    hits = []
    for base in paths:
        for name in ("CLAUDE.md", "qi_registry.json", "QI_Ecosystem_Map.md",
                     "QI_Service_Registry.md", "QI_Standards.md"):
            f = base / name
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            found = sorted(set(m.group(0) for m in pattern.finditer(text)))
            if found:
                hits.append({"file": str(f), "refs": len(found),
                             "sample": found[:6]})
    return hits


def scheduled_tasks():
    ps = (r"Get-ScheduledTask | ForEach-Object { "
          r"$a = ($_.Actions | Where-Object { $_.Execute }) ; "
          r"foreach ($x in $a) { if ($x.Execute -match '^C:\\(?!Windows|Program)') { "
          r"[PSCustomObject]@{ Task=$_.TaskName; Exec=$x.Execute; Args=$x.Arguments } } } } "
          r"| ConvertTo-Json -Compress")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=120)
        data = json.loads(r.stdout.strip() or "[]")
        return data if isinstance(data, list) else [data]
    except Exception as exc:
        return [{"error": str(exc)}]


def main():
    dirs = project_dirs()
    print("=" * 72)
    print("C: ROOT FOLDERS  (candidates for C:\\APPS)")
    print("=" * 72)
    for d in dirs:
        git = "git" if (d / ".git").is_dir() else "   "
        print(f"  {git}  {d}")
    print(f"\n  total: {len(dirs)} folders\n")

    print("=" * 72)
    print("NSSM SERVICES — paths that must be rewritten")
    print("=" * 72)
    svcs = nssm_services()
    for s in svcs:
        if "error" in s:
            print("  ", s["error"])
            continue
        print(f"\n  {s['service']}  (start: {s.get('Start','?')})")
        for k in ("Application", "AppDirectory", "AppParameters", "AppStdout", "AppStderr"):
            v = s.get(k) or ""
            if v:
                print(f"      {k:<14} {v[:110]}")

    print("\n" + "=" * 72)
    print("QI REGISTRY — project paths")
    print("=" * 72)
    try:
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for p in reg.get("projects", []):
            print(f"  {str(p.get('id','?')):<22} {p.get('path','')}")
    except Exception as exc:
        print("  registry unreadable:", exc)

    print("\n" + "=" * 72)
    print("MCP SERVERS (~/.claude.json)")
    print("=" * 72)
    try:
        cj = json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
        for k, v in (cj.get("mcpServers") or {}).items():
            cmd = v.get("command", "") or v.get("url", "")
            args = " ".join(v.get("args", []) or [])
            print(f"  {k:<16} {cmd}")
            if args:
                print(f"  {'':<16}   args: {args[:100]}")
    except Exception as exc:
        print("  unreadable:", exc)

    print("\n" + "=" * 72)
    print("DOC / CONFIG FILES REFERENCING MOVING PATHS")
    print("=" * 72)
    roots = [d for d in dirs]
    for hit in scan_text_refs(dirs + [Path(r"C:\QIH\ecosystem")], roots):
        print(f"  {hit['refs']:>3} refs  {hit['file']}")
        print(f"           {', '.join(hit['sample'])}")

    print("\n" + "=" * 72)
    print("SCHEDULED TASKS pointing into C:\\ project folders")
    print("=" * 72)
    for t in scheduled_tasks():
        if "error" in t:
            print("  ", t["error"])
        else:
            print(f"  {t.get('Task')}: {t.get('Exec')} {(t.get('Args') or '')[:60]}")


if __name__ == "__main__":
    main()
