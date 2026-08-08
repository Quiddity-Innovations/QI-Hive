# Design Harvest: BU Hive "Information" view → QI Hive Library Graph

**Harvested:** 2026-08-08, from `D:\BU Edition\AI\BU Hive` before cleanup.
**Renne's directive:** the BU Hive System Information design is "100% a better design"
than QI Hive's Library Graph (plex) memory palace — port the design, **NOT the BU
color coding**.

## What makes it better (the ideas to port)

1. **One dataset, five lenses.** A single `/api/graph` payload rendered as:
   - **Map** (default) — interactive force-style graph, glossy 3D "bubble" spheres
     drawn with per-category radial gradients (`bu-graph.js`)
   - **Mind Map** — auto-laid-out tree with pan/zoom and node focus (`bu-info-views.js`)
   - **Outline** — collapsible hierarchical text
   - **Cards** — filterable card grid by category
   - **Full Content** — reading view of everything
   The lens switch is instant (no reload) and the chosen lens is **remembered per
   device** (`localStorage`). This is the core superiority over a single fixed
   graph: same knowledge, right altitude for the moment.

2. **Centralized category color system** (`bu-colors.js`, `BUCAT`): one small module
   owns category → color; every lens asks it. QI Hive should keep this *pattern* and
   substitute a QI palette — Renne explicitly does not want BU's colors.

3. **User appearance preferences** (`bu-settings.js`, `BUSET`): bubble style,
   label sizes etc. read through one accessor with sane fallbacks, shared by all
   lenses.

4. **Engineering qualities worth copying:** dependency-free vanilla JS, CSP-safe
   (no inline handlers), graceful fallbacks when sibling modules are absent,
   per-device persistence without a backend.

## Files harvested

| File | Role |
|---|---|
| `information.html` | The page shell + lens switcher markup |
| `bu-info-views.js` | Mind Map / Outline / Cards / Full lenses (609 lines) |
| `bu-graph.js` | The default interactive Map lens with bubble rendering (480 lines) |
| `bu-colors.js` | BUCAT category-color module (42 lines) — replace palette for QI |
| `bu-settings.js` | BUSET appearance preferences |
| `bu-hive.css` | Styling (614 lines) — mine for the lens-switch + card styles |
| `api_graph_endpoint.py` | The server side of `/api/graph` — the data contract the lenses consume |

## Porting into QI Hive

Target: `C:\QIH\engine\hive\dashboard` (the Library Graph / plex memory palace).
Approach: keep QI Hive's data source; adapt its payload to the `/api/graph` node/edge
shape in `api_graph_endpoint.py`; drop the five-lens front end on top; swap `BUCAT`'s
palette to QI colors. The lenses are backend-agnostic — they only know the JSON shape.

## Source disposition

The full BU Hive app source stays (slim, ~5 MB without .venv) at
`D:\BU Edition\AI\BU Hive` for deeper reference; its `.venv` (917 MB) and the
579 session transcripts (290 MB) were deleted as bulk with no design value.
