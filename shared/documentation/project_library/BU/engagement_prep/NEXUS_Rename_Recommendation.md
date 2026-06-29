# NEXUS Naming-Collision — Recommendation Memo
*Internal — Renne / Quiddity Innovations — 2026-06-27*

## The collision
BU's flagship AI-chat platform is named **"Nexus"** (`nexus-agent`, `nexus-admin`, `nexus-mcp-server` — see `nexus-platform-overview.pdf`). Quiddity has a registered project **NEXUS** at `C:\NEXUS` (id `nexus`, port 8010/7880, `active_development`).

**Why it matters (only for BU-facing contexts):** in any deck, doc, repo, or email shown to BU, "QI NEXUS" reads as either confusion ("is this their Nexus?") or presumption ("did they copy our platform name?"). It undercuts an otherwise strong, architecturally-aligned story.

**Why it does NOT matter internally:** within QI the name is fine and renaming a live project touches the registry, NSSM services (`QI_NEXUS`), ports, tunnels, docs, and Brain records — non-trivial. **Do not rename the project just for this.**

## Recommendation
**Do nothing to the project. Control the name only at the BU boundary.**

1. **Never present a QI artefact named "NEXUS" to BU.** When BU-facing material must reference the QI project, use a neutral descriptor (e.g. its function) instead of the bare word "NEXUS".
2. **Lead BU conversations with the product names that have no collision:** CogniBase, MapSnap, AutoPDF. These are the actual BU-relevant assets; QI-NEXUS is not part of the BU pitch.
3. **If/when QI-NEXUS itself ever goes outward**, consider a distinct external product name. Options to hold in reserve:
   - **QI Relay** · **QI Junction** · **QI Confluence** · **QI Conduit** · **Quiddity Mesh**
   (all evoke "connection/hub" without the BU collision).
4. **No registry change now.** Revisit only if QI-NEXUS becomes externally marketed.

## Net
A boundary-level naming discipline — not a refactor. Zero engineering cost, removes the only awkward note in the BU fit story.
