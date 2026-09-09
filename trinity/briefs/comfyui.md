# ComfyUI (QI Media Engine) (comfyui) — L2 brief

_Generated 2026-09-09 02:38:45_

## Registry facts
- Path: `D:\AI`
- Status: active
- Ports: api:8740
- Notes: Generation is gated behind an explicit trigger: Claude renders only on a 'RENDER:' or '/comfy' message, never inferred. Rules in D:\AI\CLAUDE.md. SFW and NSFW both in scope. Workflows exist twice on purpose: API format in D:\AI\workflows (what Claude queues) and editor twins prefixed 'QI - ' in the ComfyUI user folder (what Renne clicks). They are copies, not links — changing one does not change the other. Registered 2026-08-10.

## Brain
- Current state: status=active, phase=Active â€” media engine operational
  Local image/video generation engine on D:\AI, port 8189, driven by Claude via the qi-comfy MCP server and directly usable in its own web UI at http://127.0.0.1:8189.

14 workflows verified working: t2i_fast (Z-Image Turbo, ~8s), t2i_sdxl, t2i_lora (SDXL + nudify_xl_lite, the NSFW route), t2i_lora_sd15 (Realistic Vision 5.1 for the three SD 1.5 LoRAs), t2i_ideogram (only engine rendering legible text), i2i, describe2img (Gemma 4 in-graph captioning), t2v_minimax (DEFAULT video â€” 1344x768 WITH stereo audio, ~75s), t2v_wan, i2v_wan, plus video_enhance_av / video_enhance / video_smooth / video_upscale.

Generation is gated: Claude renders only on an explicit RENDER: or /comfy trigger, never inferred. SFW and NSFW both in scope; no real identifiable people, no minors.

Every workflow exists twice â€” API format for Claude, editor twins prefixed "QI - " in the ComfyUI sidebar for Renne. They are copies, not links.

Engine selection and defaults live in D:\AI\workflows\_video_backends.json. Docs: CLAUDE.md (rules), CHEATSHEET.md (daily), RENDER_TEMPLATES.md (5 worked examples doubling as a regression suite), HOW_TO_RUN_IT_YOURSELF.md (GUI steps).

Deliberately not integrated: in-graph Ollama/Cloudflare nodes (NEXUS covers both). Exposes POST /free for VRAM release, already consumed by voice_studio.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# ComfyUI — how Claude works with it
| this file | the rules Claude follows |
| `CHEATSHEET.md` | day-to-day reference |
| `RENDER_TEMPLATES.md` | 5 worked examples + component matrix + regression suite |
it; don't assume they match.

---
## 🎬 THE TRIGGER (the rule that matters most)
Renne generates pictures and video **through ComfyUI on this machine** — never
through any other image tool, and never as a side effect of ordinary
conversation. Two triggers, exactly equivalent:

**Without a trigger** → do NOT generate anything. Talk about it: refine the
idea, write the prompt, suggest a workflow, discuss lighting or composition.
Wait to be asked. Discussing an image is not a request to make one.
leaves the conversation and hits the GPU. Never infer it. If a request looks
like it wants a render but carries no trigger, ask — one line — or just answer
in text.
### Reading a triggered request
Pick a sensible workflow and go. Don't interrogate. State which one you chose
and why in one line, then run it. Pass a fresh random `seed` each time unless
Renne is iterating on a specific image — then hold the seed and change one
### SFW and NSFW
## Running things
ComfyUI must be up first: `D:\AI\Start_ComfyUI.bat` → <http://127.0.0.1:8740>.
Check with `comfy_status`. Either order is fine — start ComfyUI first or open
Claude first; just start ComfyUI before the first render.
**Video**: always `wait=false`, then poll `comfy_result(prompt_id)`.
A Wan clip takes minutes; a blocking MCP call that long risks the stdio host.
Same reason as the one-MCP-call-per-turn rule in the global CLAUDE.md.

Outputs land in `D:\AI\output\`. Read the PNG back and show it — don't just
report a path.

### Feeding a graph an input image
renamed by ComfyUI rather than overwritten — always use the `reference` it
returns, never the name you sent.

### Sweeping a parameter
### Handing the card back
## The workflows
### Generation
Z-Image runs at **cfg 1.0**, so its negative prompt is inert by design. Don't
try to fix a Z-Image result with a negative prompt; change the positive one or
switch to `t2i_sdxl`.
### Video post-processing (built 2026-08-08)
### Sensible defaults
- **Video**: 832×480, `length` 49 ≈ 3 s at 16 fps. `length` must be
  4n+1 (33, 49, 65, 81). Raise `fps` only if you also raise `length`.
- **Video length is the VRAM knob.** 17 GB total against a ~15 GB fp8 model.
### `i2i` denoise — the only dial that matters
## Text in images — use Ideogram
the schedule disagree, quality quietly degrades. Don't rewire them apart.

## LLMs inside ComfyUI
## Choosing a video engine — `_video_backends.json`
Rules for using it:

- No `[engine=…]` → use `default` from the file.
- `requires` lists params that must be supplied (e.g. `wan_i2v` needs `image`).
- **Adding a backend never removes one.** `wan` stays even though `minimax`
  beats it on every measured axis: different model family, different motion
  character, and it is the fallback if MiniMax regresses.
## MiniMax-H3 — installed and working (`t2v_minimax`)
   They are never resident together, so both fitting individually is enough.

The graph decodes one latent twice — `VAEDecode` for frames,
## Wan video — backend status and escalation ladder
### The ladder (Renne's decision, 2026-08-09)
⚠️ **If we go past step 1, the backends must become switchable — not a
one-way migration.** Renne's requirement: all three coexist and get turned on
or off per project, per intention, per need. Concretely that means keeping
than editing the existing graphs in place. Never delete a working backend to
make room for a new one.

## Model reality on this machine
## Adding a workflow found online

## Entry points
`Free_ComfyUI_Memory.bat`, `Start_ComfyUI.bat`, `install_QI_ComfyUI_service.bat`
