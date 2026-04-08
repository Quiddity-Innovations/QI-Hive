# Skill: fetch-ai-news

## What it does
Fetches today's AI news digest from NEXUS and returns the top 5 items most relevant to QI projects.

## When to use
- User asks "what's happening in AI today?"
- Scouting for new tools, models, or frameworks
- Weekly AI briefing for the team

## How to execute

```python
import requests

# Pull from Claude Manager Dashboard (which proxies NEXUS)
r = requests.get("http://localhost:8600/api/scout/digest", timeout=15)
data = r.json()

if not data["ok"]:
    print(f"NEXUS unavailable: {data.get('error')}")
else:
    print(f"AI News — {data['date']} ({data['item_count']} items total)")
    print("Top 5 headlines:")
    for i, item in enumerate(data["top_5"], 1):
        print(f"  {i}. {item['title']}")
        print(f"     {item['url']}")
```

## Direct NEXUS call (fallback)
```python
import requests
r = requests.get("http://localhost:8010/scout/digest", timeout=10)
data = r.json()
# data["content_md"] contains full markdown digest
```

## Output format
```json
{
  "ok": true,
  "date": "2026-04-07",
  "item_count": 369,
  "top_5": [
    {"title": "...", "url": "..."},
    ...
  ]
}
```

## Relevant to QI
- LLM model releases → update Maia's LLM chain
- MCP server releases → evaluate for Claude Manager
- AI coding tools → evaluate for QI dev workflow
- RAG/vector store updates → relevant to Maia RAG roadmap
