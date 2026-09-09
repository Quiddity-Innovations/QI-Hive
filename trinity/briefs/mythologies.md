# World Mythologies (mythologies) — L2 brief

_Generated 2026-09-08 17:56:10_

## Registry facts
- Path: `C:\APPS\Mythologies`
- Status: live
- Notes: No ports and no service - deployed to Vercel from site/. Ship with: python packs/ship.py --deploy

## Brain
- No current_state recorded.
- Last decisions:
  - Hive currency pass 2026-09-08: registry brought to 42 projects; C:\APPS stays the registered path even where git history lives only in D:\Dev; QI-RELAY is a Maia component, not a project (2026-09-08 21:51:31)
  - Trinity health is inspected daily without calling an assistant; every assistant run is recorded in Agent HR as trial evidence (2026-09-08 21:37:12)
  - Codex calls always name the model; CLI default pinned to gpt-5.6-terra; ladder luna â†’ terra â†’ sol, astra only with a stated reason (2026-09-08 21:37:00)

## CLAUDE.md rules
# World Mythologies — project instructions
The two repos are **separate and do not move together.** Commit to whichever you
touched. There is no repo at the project root.

## Ship with one command
`?v=<hash of that file>`, and it must run **before** `build_pages.py` because
the 37 per-pack pages are cut from `index.html`. That stamp is what makes it
safe for `/js` and `/css` to be served `immutable` for a year. Never hand-edit a
`?v=` and never mark an unstamped path `immutable` — on 2026-08-22 the hub
shelves rendered unstyled for returning visitors only, because `/js` was cached
for a day at a stable URL while `index.html` and `style.css` revalidated every
**Verify a deploy by `content-type`, never by status code.** The catch-all
rewrite returns 200 with HTML for every path, including files that do not exist.
A real portrait returns `image/webp`.

## The five audits
repoint the dataset, or drop `/portraits` to `must-revalidate` for one deploy.

## Conventions that are not obvious from the code
- **Hindu is the one pack with no drawn frame** — never run `frame_portraits.py`
  on it.

## Rendering
Renne — never infer one.** Always test-render six figures and look at a contact
sheet before a full run; every pack so far has needed at least one correction.

## Editorial standard
## Held, and not to be built autonomously
if he says go the honest build is text-only or medallion, never generated
portraits.

## Place in the QI ecosystem
never inside this folder.

## Entry points
`Hindu-Mythology-Interactive-Map.html`
