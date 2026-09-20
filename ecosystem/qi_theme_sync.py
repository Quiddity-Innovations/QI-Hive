#!/usr/bin/env python
"""
qi_theme_sync.py - stamp the QI shared theme into every surface that shows it.

QI_Theme.json is the authority. Nothing else in the ecosystem may hold a colour
value by hand. This tool renders that file into each consumer's own native form
and writes it between markers, so every project stays self-contained at runtime
(no project fetches CSS from another project's port) while drift stays mechanical
to detect and fix.

    python qi_theme_sync.py --check      # drift detector: exit 1 if anything is stale
    python qi_theme_sync.py --dry-run    # show what would change
    python qi_theme_sync.py              # write
    python qi_theme_sync.py --comfy-only # just re-emit the ComfyUI palette file

The ComfyUI palette is only WRITTEN here as a .json artefact. Installing it goes
through ComfyUI's own POST /api/settings (Media Studio's /api/theme/comfy does
this), because hand-editing comfy.settings.json under a running ComfyUI loses the
edit the next time the frontend saves.

Markers, per file kind:
    css     /* QI-THEME:BEGIN */ ... /* QI-THEME:END */
    gradio  # QI-THEME:BEGIN ... # QI-THEME:END   (inside a python string literal)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
THEME = HERE / "QI_Theme.json"

CSS_BEGIN = "/* QI-THEME:BEGIN */"
CSS_END = "/* QI-THEME:END */"
PY_BEGIN = "/* QI-THEME:BEGIN */"      # the gradio block is CSS inside a py string
PY_END = "/* QI-THEME:END */"


# ---------------------------------------------------------------- rendering

def _vars(d: dict, indent: str) -> str:
    return "\n".join(f"{indent}--{k}:{v};" for k, v in d.items() if not k.startswith("_"))


def render_css(t: dict) -> str:
    """The token block every HTML panel shares.

    Three-state theming: bare :root is light, prefers-color-scheme supplies dark
    unless the user pinned light, and [data-theme] wins over both. A token is
    never defined ONLY inside a media query - that is how a pinned theme ends up
    half-applied.
    """
    light, dark, fixed = t["modes"]["light"], t["modes"]["dark"], t["fixed"]
    ver = t["version"]

    def mode(d: dict, indent: str) -> str:
        # --card is an alias: Voice Studio's CSS says card where Media Studio says
        # panel. Emitting both means neither project has to be rewritten.
        body = _vars(d, indent)
        return body + f"\n{indent}--card:{d['panel']};"

    return f"""{CSS_BEGIN}
  /* QI Studio theme v{ver} - generated from C:\\QIH\\ecosystem\\QI_Theme.json
     by qi_theme_sync.py. Do not edit these values here; edit the authority and
     re-run the tool, or `--check` will report this file as drifted. */
  :root{{
    color-scheme:light;
{mode(light, "    ")}
    /* dark in both modes, on purpose: the nav rail and the cockpit */
{_vars(fixed, "    ")}
    --qi-ui:{t['type']['ui']};
    --qi-mono:{t['type']['mono']};
    --radius:{t['type']['radius']};
    --radius-sm:{t['type']['radius-sm']};
  }}
  @media (prefers-color-scheme:dark){{
    :root:not([data-theme="light"]){{
      color-scheme:dark;
{mode(dark, "      ")}
    }}
  }}
  :root[data-theme="dark"]{{
    color-scheme:dark;
{mode(dark, "    ")}
  }}
  :root[data-theme="light"]{{
    color-scheme:light;
{mode(light, "    ")}
  }}
{CSS_END}"""


def render_gradio(t: dict) -> str:
    """Gradio owns its own variable names. We map QI tokens onto them rather than
    restyling Gradio's components one by one - that survives a Gradio upgrade,
    a pile of `!important` selectors would not."""
    light, dark = t["modes"]["light"], t["modes"]["dark"]
    ver = t["version"]

    def block(m: dict, sel: str, indent: str = "") -> str:
        i = indent + "  "
        return f"""{indent}{sel} {{
{i}--body-background-fill: {m['bg']};
{i}--background-fill-primary: {m['panel']};
{i}--background-fill-secondary: {m['code']};
{i}--block-background-fill: {m['panel']};
{i}--block-label-background-fill: {m['code']};
{i}--block-border-color: {m['line']};
{i}--border-color-primary: {m['line']};
{i}--border-color-accent: {m['accent']};
{i}--body-text-color: {m['ink']};
{i}--body-text-color-subdued: {m['muted']};
{i}--block-label-text-color: {m['muted']};
{i}--block-title-text-color: {m['ink']};
{i}--color-accent: {m['accent']};
{i}--color-accent-soft: {m['accent-soft']};
{i}--link-text-color: {m['accent']};
{i}--link-text-color-hover: {m['accent']};
{i}--button-primary-background-fill: {m['accent']};
{i}--button-primary-background-fill-hover: {m['accent']};
{i}--button-primary-text-color: {m['accent-ink']};
{i}--button-primary-border-color: {m['accent']};
{i}--button-secondary-background-fill: {m['panel']};
{i}--button-secondary-text-color: {m['ink']};
{i}--button-secondary-border-color: {m['line']};
{i}--input-background-fill: {m['bg']};
{i}--input-border-color: {m['line']};
{i}--input-placeholder-color: {m['muted']};
{i}--checkbox-background-color-selected: {m['accent']};
{i}--checkbox-border-color-selected: {m['accent']};
{i}--slider-color: {m['accent']};
{i}--error-background-fill: {m['panel']};
{i}--error-text-color: {m['bad']};
{i}--panel-background-fill: {m['panel']};
{i}--table-odd-background-fill: {m['code']};
{i}--table-even-background-fill: {m['panel']};
{indent}}}"""

    return f"""{PY_BEGIN}
/* QI Studio theme v{ver} - generated from C:\\QIH\\ecosystem\\QI_Theme.json by
   qi_theme_sync.py. Do not edit by hand.

   Gradio sets .dark on <body> for its dark mode, and honours ?__theme=dark|light
   in the URL, so Media Studio switches this frame by reloading it with that
   param - there is no code here that decides the mode. */
{block(light, ":root, .gradio-container")}
{block(dark, ".dark, .dark .gradio-container")}
:root, .dark {{
  --radius-lg: {t['type']['radius']};
  --radius-md: {t['type']['radius-sm']};
  --font: {t['type']['ui']};
  --font-mono: {t['type']['mono']};
}}
{PY_END}"""


def render_comfy(t: dict) -> dict:
    """Two ComfyUI palettes, one per mode.

    Deliberately PARTIAL. ComfyUI merges a custom palette over its own built-in
    default for the matching mode, so every key we leave out keeps ComfyUI's
    value - and `node_slot` is left out entirely on purpose: those colours encode
    data types (MODEL, LATENT, VAE), which is ComfyUI's semantics, not QI
    branding. Recolouring them would make its own docs wrong.
    """
    out = {}
    for mode in ("dark", "light"):
        m = t["modes"][mode]
        canvas = "#0e1116" if mode == "dark" else "#e9ecf1"
        node_bg = m["panel"] if mode == "dark" else "#ffffff"
        node_title = "#232932" if mode == "dark" else "#eef0f4"
        out[f"qi_{mode}"] = {
            "id": f"qi_{mode}",
            "name": f"QI Studio ({mode.capitalize()})",
            "light_theme": mode == "light",
            "colors": {
                "litegraph_base": {
                    "CLEAR_BACKGROUND_COLOR": canvas,
                    "NODE_TITLE_COLOR": m["muted"],
                    "NODE_SELECTED_TITLE_COLOR": m["ink"],
                    "NODE_TEXT_COLOR": m["ink"],
                    "NODE_TEXT_HIGHLIGHT_COLOR": m["accent"],
                    "NODE_DEFAULT_COLOR": node_title,
                    "NODE_DEFAULT_BGCOLOR": node_bg,
                    "NODE_DEFAULT_BOXCOLOR": m["line"],
                    "NODE_BOX_OUTLINE_COLOR": m["accent"],
                    "NODE_ERROR_COLOUR": m["bad"],
                    "DEFAULT_SHADOW_COLOR": m["shadow"],
                    "WIDGET_BGCOLOR": m["code"],
                    "WIDGET_OUTLINE_COLOR": m["line"],
                    "WIDGET_TEXT_COLOR": m["ink"],
                    "WIDGET_SECONDARY_TEXT_COLOR": m["muted"],
                    "BADGE_FG_COLOR": m["accent-ink"],
                    "BADGE_BG_COLOR": m["accent"],
                },
                "comfy_base": {
                    "fg-color": m["ink"],
                    "bg-color": m["bg"],
                    "comfy-menu-bg": m["panel"],
                    "comfy-menu-secondary-bg": m["code"],
                    "comfy-input-bg": m["code"],
                    "input-text": m["ink"],
                    "descrip-text": m["muted"],
                    "drag-text": m["muted"],
                    "error-text": m["bad"],
                    "border-color": m["line"],
                    "tr-even-bg-color": m["panel"],
                    "tr-odd-bg-color": m["code"],
                    "content-bg": m["code"],
                    "content-fg": m["ink"],
                    "content-hover-bg": m["accent-soft"],
                    "content-hover-fg": m["ink"],
                    "bar-shadow": f"{m['shadow']} 0 0 0.5rem",
                },
            },
        }
    return out


# ---------------------------------------------------------------- stamping

def stamp(path: Path, block: str, begin: str, end: str) -> tuple[bool, str]:
    """Replace whatever sits between the markers. Returns (changed, note)."""
    if not path.exists():
        return False, f"MISSING  {path}"
    src = path.read_text(encoding="utf-8")
    i, k = src.find(begin), src.find(end)
    if i < 0 or k < 0:
        return False, (f"NO MARKERS  {path}\n           add {begin} / {end} "
                       f"around the block this tool should own")
    if k < i:
        return False, f"MARKERS REVERSED  {path}"
    new = src[:i] + block + src[k + len(end):]
    if new == src:
        return False, f"ok       {path}"
    return True, f"CHANGED  {path}"


def write(path: Path, block: str, begin: str, end: str, dry: bool) -> bool:
    changed, note = stamp(path, block, begin, end)
    print("   " + note)
    if changed and not dry:
        src = path.read_text(encoding="utf-8")
        i, k = src.find(begin), src.find(end)
        path.write_text(src[:i] + block + src[k + len(end):], encoding="utf-8")
    return changed


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report drift and exit 1 if any consumer is stale")
    ap.add_argument("--dry-run", action="store_true", help="show changes, write nothing")
    ap.add_argument("--comfy-only", action="store_true",
                    help="only re-emit the ComfyUI palette artefact")
    a = ap.parse_args()
    dry = a.dry_run or a.check

    t = json.loads(THEME.read_text(encoding="utf-8"))
    print(f"QI theme v{t['version']} ({t['updated']})  <- {THEME}")

    by_id = {c["id"]: c for c in t["consumers"]}
    changed = 0

    if not a.comfy_only:
        css = render_css(t)
        for cid in ("mediastudio", "voicestudio"):
            changed += write(Path(by_id[cid]["path"]), css, CSS_BEGIN, CSS_END, dry)
        changed += write(Path(by_id["avatarstudio"]["path"]),
                         render_gradio(t), PY_BEGIN, PY_END, dry)

    # The ComfyUI artefact lives next to the authority: it is not a project file,
    # it is what gets POSTed into ComfyUI's own settings.
    pal_path = HERE / "qi_comfy_palettes.json"
    pal = json.dumps(render_comfy(t), indent=2, ensure_ascii=False) + "\n"
    old = pal_path.read_text(encoding="utf-8") if pal_path.exists() else ""
    if pal != old:
        changed += 1
        print(f"   CHANGED  {pal_path}")
        if not dry:
            pal_path.write_text(pal, encoding="utf-8")
    else:
        print(f"   ok       {pal_path}")

    if a.check:
        if changed:
            print(f"\nDRIFT: {changed} consumer(s) stale. Run without --check to fix.")
            return 1
        print("\nNo drift - every surface matches the authority.")
        return 0
    if dry:
        print(f"\n{changed} file(s) would change. Nothing written.")
    else:
        print(f"\n{changed} file(s) written."
              "\nComfyUI is NOT updated by this tool: install the palette from Media"
              "\nStudio (Cockpit -> Appearance) so it goes through ComfyUI's own API.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
