"""One-shot reconciliation of the orphan C:\\Claude\\tasks.json into the live C:\\QIH\\data\\tasks.json."""
import json, shutil, sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

OLD = Path(r"C:\Claude\tasks.json")
NEW = Path(r"C:\QIH\data\tasks.json")

old_data = json.loads(OLD.read_text(encoding="utf-8"))
new_data = json.loads(NEW.read_text(encoding="utf-8"))

old_tasks = old_data.get("tasks", [])
new_tasks = new_data.get("tasks", [])

by_id = {t["id"]: t for t in new_tasks}
by_title = {t["title"].lower(): t for t in new_tasks}

added, updated, skipped = 0, 0, 0
for t in old_tasks:
    tid = t.get("id")
    title_key = t.get("title", "").lower()
    if tid in by_id:
        existing = by_id[tid]
        if existing.get("column") != "done" and t.get("column") == "done":
            existing["column"] = "done"
            updated += 1
        else:
            skipped += 1
    elif title_key in by_title:
        existing = by_title[title_key]
        if existing.get("column") != "done" and t.get("column") == "done":
            existing["column"] = "done"
            updated += 1
        else:
            skipped += 1
    else:
        new_tasks.append(t)
        by_id[tid] = t
        by_title[title_key] = t
        added += 1

new_data["tasks"] = new_tasks
backup = NEW.with_suffix(f".bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
shutil.copy2(NEW, backup)
NEW.write_text(json.dumps(new_data, indent=2, ensure_ascii=False), encoding="utf-8")

archive = OLD.with_suffix(f".archived-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
shutil.move(str(OLD), str(archive))

print(f"backup:   {backup}")
print(f"archived: {archive}")
print(f"added={added}  updated={updated}  skipped={skipped}  total={len(new_tasks)}")
