# -*- coding: utf-8 -*-
r"""
pronounce.py — QI canonical spoken-pronunciation fixer (SHARED, reusable by every QI app).

Fixes how an app SAYS certain words/names without changing what it PRINTS or displays.
The owner's name "Renne" is spelled Renne but pronounced like the US name "Renee" (ruh-NAY);
neural TTS reads "Renee" correctly, so we substitute it in the spoken audio only.

Source of truth for the map:  C:\QIH\shared\voice\pronunciation.json  (+ built-in default).
Matching is whole-word and case-insensitive; the original word's capitalization is preserved.

ADOPT IN ANY APP (one line at every TTS call site):
    import sys; sys.path.insert(0, r"C:\QIH\shared\voice")
    import pronounce
    text_for_tts = pronounce.apply(text)        # then synth text_for_tts, print/display the original

Apps that bundle their own copy (offline / portable) can copy this file + pronunciation.json
next to their code; apply() still works if the JSON is missing (uses the built-in DEFAULT).
"""
import json
import os
import re

# Built-in fallback so apply() works even if the JSON is absent.
DEFAULT = {"Renne": "Renee", "Renné": "Renee", "Rene": "Renee"}
_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pronunciation.json")


def _load_map():
    table = dict(DEFAULT)
    try:
        with open(_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        table.update(data.get("map", {}) or {})
    except Exception:
        pass
    return table


def _match_case(src, repl):
    if src.isupper():
        return repl.upper()
    if src[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def apply(text, extra=None):
    """Return `text` rewritten for SPEECH only. `extra` = optional dict of extra
    {spelled: spoken} pairs (e.g. an app's config.voice.pronunciation)."""
    if not text:
        return text
    table = _load_map()
    if extra:
        try:
            table.update({k: v for k, v in extra.items() if isinstance(v, str)})
        except Exception:
            pass
    for word, say in table.items():
        if not word or word.startswith("_") or not isinstance(say, str):
            continue
        pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
        text = pattern.sub(lambda m, s=say: _match_case(m.group(0), s), text)
    return text


if __name__ == "__main__":
    import sys
    print(apply(" ".join(sys.argv[1:]) or "Hi Renne, did I say your name right, Renne?"))
