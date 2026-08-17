import csv, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8')
rows=list(csv.DictReader(open('rollback/services_before.csv', encoding='utf-8-sig')))
print("CSV columns:", rows[0].keys() if rows else None)
hits=[r for r in rows if '1-AI' in (r.get('Application') or '')]
print(f"\nServices with Application under C:\1-AI : {len(hits)}")
for r in hits:
    print("  ", r['Name'], "|", r.get('Start'), "|", r.get('Status'))
print(f"\nTotal QI_* services in dump: {len(rows)}")
others=[r for r in rows if '1-AI' not in (r.get('Application') or '')]
print(f"Non-1-AI services: {len(others)}")
for r in others:
    print("  ", r['Name'], "->", r.get('Application'))
