#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QI Hive — OpenClaw outbound filter re-injection (idempotent).

Re-applies the QI patch to OpenClaw's `filterEmptyTelegramTextChunks()` so that
agent replies matching placeholder / status-token / metadata-leak patterns are
silently dropped before reaching Telegram.

v4 (2026-05-15 late) — adds JSON-shape runtime-context dump detection. Tasuke
leaked a fenced JSON block with quoted keys ("chat_id", "sender_id", "model",
"runtime", "agent", "capabilities") that v3 regexes missed because they
expected unquoted `chat_id: -123` shapes.

This patcher is doubly idempotent: it detects v3 blocks and rewrites them to
v4 in place. Re-run safely after any OpenClaw upgrade.

Usage (from Windows):
  wsl -d Ubuntu-24.04 -- python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py
Or use the .bat wrapper next to this file.
"""
import os, re, sys, glob, shutil, datetime, pathlib

MARKER_V4 = "QI Hive patch v4"
MARKER_ANY = "QI Hive patch"  # matches v3 too
HOME = pathlib.Path(os.path.expanduser("~"))

def _discover_targets():
    roots = [
        HOME / ".npm-global/lib/node_modules/openclaw/dist",
    ]
    roots.extend(
        pathlib.Path(p) for p in
        glob.glob(str(HOME / ".openclaw/plugin-runtime-deps/openclaw-*/dist"))
    )
    found = []
    for root in roots:
        if not root.exists():
            continue
        for js in root.rglob("delivery-*.js"):
            try:
                head = js.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "filterEmptyTelegramTextChunks" in head:
                found.append(js)
    return found

TARGETS = _discover_targets()

PATCH = r"""// QI Hive patch v4 2026-05-15-late — drop status-sentinel, session-metadata,
// AND JSON-shape runtime-context dumps before they reach Telegram. v4 adds
// fenced-JSON detection after Tasuke leaked a quoted-key context dump that v3
// regexes (unquoted chat_id, Model:ollama/) missed entirely.
// Re-apply with: python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py
const _QIHIVE_PLACEHOLDER_RE = /^\s*(NO[_\s][A-Z]{2,20}(?:[_\s][A-Z]{2,20}){0,3}|HEARTBEAT[_\s]?OK|\(silent\)|\[silent\]|STAY[_\s]SILENT|REMAIN[_\s]SILENT|NOTHING[_\s]TO[_\s](ADD|SAY)|NO[_\s]?COMMENT|\(no\s+response\)|\[no\s+response\]|\(no\s+reply\)|\[no\s+reply\])\s*[.!?]?\s*$/i;
// 2+ of these in one reply = treat as a metadata dump (unquoted shapes)
const _QIHIVE_METADATA_PATTERNS = [
\t/Model:\s*ollama\//i,
\t/Session\s*Label:\s*agent:/i,
\t/Tokens?\s*Used:\s*\d/i,
\t/Context\s*Size:\s*\d+\s*tokens/i,
];
// ANY single match in this list = drop
const _QIHIVE_META_COMMENTARY_PATTERNS = [
\t/system[-\s]level\s+context\s+block/i,
\t/OpenClaw\s+orchestration\s+layer/i,
\t/\bagent:(?:main|kaze|tasuke-line|sentry|yubin)\b/,
\t/the\s+(?:provided|given)\s+text\s+is\s+a\s+system/i,
\t/this\s+(?:is|appears\s+to\s+be)\s+a\s+system[-\s]level\s+/i,
\t/orchestration\s+(?:layer|framework)\s+provides?\s+metadata/i,
\t/(?:internal|debug)\s+context\s+(?:block|metadata)/i,
\t/^(?:Below\s+is\s+a\s+)?summary\s+of\s+your\s+(?:current\s+)?context/i,
\t/\bruntime\s+context\b/i,
\t/system\s+context\s+provided\s+to\s+the\s+model/i,
\t/system\s+prompt[-\s]?style\s+notification/i,
\t/\bcontext\s+injection\b/i,
\t/\bmetadata\s+block\b/i,
\t/\bSession\s+Identifiers?\b/i,
\t/metadata\s+about\s+the\s+(?:incoming|current|user)/i,
\t/(?:I\s+(?:will|understand|recognize)\s+(?:this|the\s+provided\s+context)\s+as\s+(?:the\s+)?runtime|operational\s+metadata\s+used\s+to\s+maintain)/i,
\t/As\s+an\s+AI,?\s+I\s+(?:recognize|use\s+this\s+metadata)/i,
\t/chat_id\s*[:=]\s*-?\d/i,
\t/sender_id\s*[:=]\s*\d/i,
\t/\bmulti-agent\s+(?:or\s+complex\s+)?orchestration\s+framework\b/i,
\t/parse\s+session\s+metadata/i,
\t/preceding\s+message[.,]?\s+I\s+am\s+ready\s+to\s+proceed/i,
\t/keeping\s+this\s+internal\s+metadata\s+private/i,
];
// v4: JSON-shape runtime-context dump keys (each match counts toward threshold)
const _QIHIVE_JSON_KEY_PATTERNS = [
\t/"agent"\s*:\s*"(?:main|kaze|tasuke|tasuke-line|sentry|yubin)"/i,
\t/"runtime"\s*:\s*\{/i,
\t/"chat_id"\s*:\s*"?-?[\w:.-]*\d/i,
\t/"sender_id"\s*:\s*"?\d/i,
\t/"message_id"\s*:\s*"?\d/i,
\t/"model"\s*:\s*"?ollama\//i,
\t/"channel"\s*:\s*"(?:telegram|line|web)"/i,
\t/"account_id"\s*:\s*"/i,
\t/"chat_type"\s*:\s*"(?:group|supergroup|private|channel)"/i,
\t/"capabilities"\s*:\s*\[/i,
\t/"is_forum"\s*:\s*(?:true|false)/i,
\t/"is_group_chat"\s*:\s*(?:true|false)/i,
\t/"topic_id"\s*:\s*"?\d/i,
\t/"group_subject"\s*:\s*"/i,
\t/"sender"\s*:\s*"/i,
];
function _qihiveLooksLikeMetadataLeak(text) {
\tconst hits = _QIHIVE_METADATA_PATTERNS.reduce((n, re) => n + (re.test(text) ? 1 : 0), 0);
\tif (hits >= 2) return true;
\tfor (const re of _QIHIVE_META_COMMENTARY_PATTERNS) if (re.test(text)) return true;
\t// v4: JSON-shape runtime-context dump — 2+ telltale keys = drop. This catches
\t// fenced ```json blocks AND raw JSON object dumps.
\tconst jsonHits = _QIHIVE_JSON_KEY_PATTERNS.reduce((n, re) => n + (re.test(text) ? 1 : 0), 0);
\tif (jsonHits >= 2) return true;
\treturn false;
}
function filterEmptyTelegramTextChunks(chunks) {
\treturn chunks.filter((chunk) => {
\t\tconst trimmed = chunk.text.trim();
\t\tif (trimmed.length === 0) return false;
\t\tif (_QIHIVE_PLACEHOLDER_RE.test(trimmed)) {
\t\t\ttry { console.warn(`[qihive-filter] dropped placeholder: ${trimmed.slice(0, 60)}`); } catch {}
\t\t\treturn false;
\t\t}
\t\tif (_qihiveLooksLikeMetadataLeak(trimmed)) {
\t\t\ttry { console.warn(`[qihive-filter] dropped metadata leak: ${trimmed.slice(0, 80)}`); } catch {}
\t\t\treturn false;
\t\t}
\t\treturn true;
\t});
}"""

ORIGINAL_FN_RE = re.compile(
    r'function\s+filterEmptyTelegramTextChunks\(chunks\)\s*\{\s*'
    r'return\s+chunks\.filter\(\(chunk\)\s*=>\s*chunk\.text\.trim\(\)\.length\s*>\s*0\);\s*\}'
)

# Matches a previously-injected QI Hive patch block (v3 or other), from its
# leading comment marker through the closing `}` of filterEmptyTelegramTextChunks.
# Non-greedy on the body so we stop at the first function close.
PRIOR_PATCH_RE = re.compile(
    r'//\s*QI Hive patch[^\n]*\n'        # marker comment line
    r'[\s\S]*?'                           # everything up to ...
    r'function\s+filterEmptyTelegramTextChunks\(chunks\)\s*\{'
    r'[\s\S]*?'
    r'\n\}'                               # closing brace of function on its own line
)

def apply_to(target: pathlib.Path, ts: str) -> str:
    """Returns 'patched-v4' | 'upgraded-v4' | 'already-v4' | 'missing' | 'pattern-not-found'."""
    if not target.exists():
        return "missing"
    src = target.read_text(encoding="utf-8")
    if MARKER_V4 in src:
        return "already-v4"
    literal = PATCH.replace("\\t", "\t")
    bak = target.with_name(target.name + f".bak-qihive-{ts}")
    if MARKER_ANY in src:
        # v3 (or older) present — surgically replace the prior patch block.
        if not PRIOR_PATCH_RE.search(src):
            return "pattern-not-found"
        shutil.copy2(target, bak)
        new = PRIOR_PATCH_RE.sub(lambda _m: literal, src, count=1)
        target.write_text(new, encoding="utf-8")
        return "upgraded-v4"
    # Pristine upstream — replace the original one-liner function.
    if not ORIGINAL_FN_RE.search(src):
        return "pattern-not-found"
    shutil.copy2(target, bak)
    new = ORIGINAL_FN_RE.sub(lambda _m: literal, src, count=1)
    target.write_text(new, encoding="utf-8")
    return "patched-v4"

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"QI Hive — apply_filter_patch.py (v4) @ {ts}")
    print(f"  HOME = {HOME}")
    print(f"  Targets: {len(TARGETS)}")
    counts = {}
    for t in TARGETS:
        try:
            result = apply_to(t, ts)
        except Exception as e:
            print(f"  ERROR    {t}: {e}")
            counts["error"] = counts.get("error", 0) + 1
            continue
        counts[result] = counts.get(result, 0) + 1
        flag = {
            "patched-v4": "PATCHED  ",
            "upgraded-v4": "UPGRADED ",
            "already-v4": "already  ",
            "missing": "?missing ",
            "pattern-not-found": "PATTERN! ",
        }[result]
        print(f"  {flag} {t}")
    print()
    print("Summary:", ", ".join(f"{k}={v}" for k, v in counts.items() if v))
    if counts.get("pattern-not-found"):
        print()
        print("WARNING: At least one target's pattern didn't match. Inspect manually.")
        sys.exit(2)
    if counts.get("patched-v4") or counts.get("upgraded-v4"):
        print()
        print("Patched. Now restart gateways:")
        print("  systemctl --user restart openclaw-gateway openclaw-gateway-kaze")

if __name__ == "__main__":
    main()
