import sys, docx
sys.stdout.reconfigure(encoding='utf-8')
d = docx.Document(r"C:\QIH\shared\documentation\session_summaries\QIH_Migration_Summary_2026-08-08_2250.docx")
for p in d.paragraphs:
    t = p.text.strip()
    if t: print(("## " if p.style.name.startswith("Heading") else "") + t)
for tb in d.tables:
    for r in tb.rows:
        print(" | ".join(c.text.strip() for c in r.cells))
