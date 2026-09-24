"""After Batch 1 (verified 2026-09-24): update QI_Service_Registry.md NSSM rows from
the plan, then commit each app's <App>_NSSM.exe in its own repo. Re-runnable."""
import json, re, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
REG = Path(r"C:\QIH\ecosystem\QI_Service_Registry.md")
plan = {r["name"]: r for r in json.loads((HERE / "batch1_plan.json").read_text(encoding="utf-8"))}

# 1. Registry: rewrite every "NSSM binary" row under a ### QI_* heading
lines = REG.read_text(encoding="utf-8").split("\n")
cur, changed, missing = None, 0, set()
for i, line in enumerate(lines):
    m = re.match(r"^###\s+(QI_[A-Za-z0-9_]+)\s*$", line)
    if m:
        cur = m.group(1); continue
    if cur and line.startswith("| **NSSM binary** |"):
        r = plan.get(cur)
        if r and r["action"] == "repoint":
            new = f"| **NSSM binary** | `{r['target_bin']}` (own relabeled copy, Batch 1 2026-09-24) |"
        elif cur == "QI_MaiaDemoTunnel":
            new = "| **NSSM binary** | REMOVED 2026-09-24 (retired). Recreate: `C:\\QIH\\tools\\naming_standardization\\batch1\\batch1_removed_QI_MaiaDemoTunnel.cmd` |"
        else:
            missing.add(cur); continue
        if lines[i] != new:
            lines[i] = new; changed += 1
text = "\n".join(lines)
banner_old = re.compile(r"> ## ⏳ PENDING — Per-product NSSM.*?(?=\n\n)", re.S)
banner_new = ("> ## ✅ DONE — Per-app NSSM (Batch 1, 2026-09-24)\n"
              "> Every `QI_*` service runs on its own relabeled NSSM copy: app services on\n"
              "> `<AppRoot>\\<App>_NSSM.exe`, Hive services on `C:\\QIH\\engine\\bin\\<Label>_NSSM.exe`,\n"
              "> so the UAC popup names the product and no app depends on `C:\\QIH` to start.\n"
              "> Display name = service name. App→QI_BrainAPI boot dependencies removed (NEXUS, Maia, Naya).\n"
              "> 58 services, 0 rollbacks, verified by `verify_batch1.py`. Plan / rollback / result:\n"
              "> `C:\\QIH\\tools\\naming_standardization\\batch1\\`. The shared `nssm.exe` is kept only as the source\n"
              "> for new copies. Next: renames to `QI_<App>_<Function>` (`..\\batch2\\name_map.json`), one app per wave.")
text, n = banner_old.subn(lambda _m: banner_new, text, count=1)
text = text.replace("**Last updated:** 2026-06-20 (static named-tunnel migration)",
                    "**Last updated:** 2026-09-24 (Batch 1: per-app NSSM, display names, MaiaDemoTunnel removed)")
REG.write_text(text, encoding="utf-8")
print(f"registry: {changed} NSSM rows updated, banner replaced={n}, sections without plan entry: {sorted(missing)}")

# 2. Commit each app's NSSM copy in its own repo (Hive copies live in C:\QIH, committed there)
MSG = ("chore(ops): ship own relabeled {exe} (per-app NSSM, QI Batch 1)\n\n"
       "The app's Windows services now run on this copy instead of the shared\n"
       "C:\\QIH\\engine\\bin\\nssm.exe, so the app starts without the QI Hive and the\n"
       "UAC popup names the app. Verified 2026-09-24.\n\n"
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
done = set()
for r in plan.values():
    if r["action"] != "repoint" or r.get("hive"):
        continue
    exe = Path(r["target_bin"])
    if exe in done:
        continue
    done.add(exe)
    root = subprocess.run(["git", "-C", str(exe.parent), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if root.returncode:
        print(f"  no repo   {exe}"); continue
    tracked = subprocess.run(["git", "-C", str(exe.parent), "ls-files", "--error-unmatch", exe.name], capture_output=True).returncode == 0
    if tracked:
        print(f"  tracked   {exe}"); continue
    add = subprocess.run(["git", "-C", str(exe.parent), "add", "-f", "--", exe.name], capture_output=True, text=True)
    com = subprocess.run(["git", "-C", str(exe.parent), "commit", "-q", "-m", MSG.format(exe=exe.name), "--", exe.name],
                         capture_output=True, text=True)
    print(f"  {'committed' if com.returncode == 0 else 'COMMIT FAIL'} {exe}  {com.stderr.strip()[:120]}")
