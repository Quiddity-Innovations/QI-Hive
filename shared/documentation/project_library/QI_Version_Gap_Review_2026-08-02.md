# QI Version-Gap Review — 2026-08-02

Companion to the [QI Component Inventory](QI_Component_Inventory_2026-08-02.md). Assessment of the ⬆️ flags: what's safe to take, what's risky, what to skip. Recommendation principle: upgrade only when a gap blocks work or carries a security fix — this is a POC-budget shop, stability wins.

## 🔴 Hold — breaking, upgrade only with a migration plan

| Component | Gap | Where it bites | Assessment |
|---|---|---|---|
| **ChromaDB** | 0.5.x → 1.5.9 | QI Brain (decisions/sessions/docs collections), Documentation Brain, MapSnap/Maia RAG plans | 1.x changed client APIs and storage format. A blind upgrade breaks the Brain. Migration = export collections, upgrade, re-embed. Only do this when a 1.x-only feature is actually needed. **Pin 0.5.x meanwhile.** |
| **transformers** | 4.44 (shared) → 5.14 | PersonalSong/AvatarStudio diffusers pipelines on the shared interpreter | v5 removed legacy APIs; diffusers 0.32 pins may conflict. Headroom already runs 5.2.0 **isolated in its own venv** — that isolation is the correct pattern. Do not bump the shared interpreter until diffusers/torch stack is retested together. |
| **TypeScript** | 5.6 → 7.0 | CypherMiner | TS7 = new native (Go) compiler. Big build-speed win but ecosystem tooling still settling. CypherMiner builds fine today — revisit in Q4. |
| **Vite** | 6.0 → 8.2 | CypherMiner | Two majors; plugin API churn. Bundle with the TS7 migration when it happens, not before. |

## 🟡 Take deliberately — minor friction possible

| Component | Gap | Assessment |
|---|---|---|
| **Gradio** | 6.14 → 6.22 | Same major, safe; theme/queue fixes. Take on next touch of each Gradio app. |
| **FastAPI / Uvicorn / Pydantic** | 0.115→0.141 / 0.34→0.52 / 2.x→2.13 | All same-major, well-behaved. Refresh floors (`>=`) at next per-project release; no urgent action. |
| **rich** | 13.9 → 15.0 | Major, but console-formatting only (one app). Take when convenient. |
| **yt-dlp** | pinned floor → 2026.7.4 | Site extractors rot fast — PlayDeck/TubeScout should track latest routinely. Add to monthly self-audit. |
| **cloudflared** | → 2026.7.3 | Tunnels auto-serviced; refresh binaries during the next maintenance window. |

## 🟢 Safe patch/minor bumps — batch anytime

Pillow 12.2→12.3 · rembg 2.0.75→2.0.77 · Ghostscript 10.07.0→10.07.1 · NAPS2 8.2.1→8.3.2 · soundfile 0.13.1→0.14 · Tesseract →5.5.3 · SortableJS 1.15.0→1.15.7 (vendored, replace file) · edge-tts already current (7.2.8) · Bootstrap Icons already current (1.13.1).

## ⚪ No action possible / not applicable

- **NSSM 2.24** — upstream dormant since 2014; still the standard. No newer version exists.
- **tabula-java** — dormant since 2021; works as bundled.
- **PyPDF2** — deprecated upstream; if touched again, move to **pypdf** (maintained successor).
- Model weights (SDXL, SVD, Kokoro, IP-Adapter, Seed-VC, Hallo2, LivePortrait) — no semver releases; upgrade only when a better model is chosen, not for currency.

## Standing rule

The monthly self-audit (QI_ClaudeSelfAudit) should diff in-use vs latest for the 🟡 tier and report — not auto-upgrade. The 🔴 tier only moves with an explicit migration session.
