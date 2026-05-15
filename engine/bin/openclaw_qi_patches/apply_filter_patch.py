#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QI Hive — OpenClaw outbound filter re-injection (idempotent).

Re-applies the QI patch to OpenClaw's `filterEmptyTelegramTextChunks()` so that
agent replies matching placeholder / status-token / metadata-leak patterns are
silently dropped before reaching Telegram.

Run this AFTER any `npm update -g openclaw` (or any OpenClaw upgrade) that
overwrites node_modules. Idempotent: skips already-patched files.

Designed to run inside WSL — the OpenClaw install lives under hyosuke's home.
Usage (from Windows):
  wsl -d Ubuntu-24.04 -- python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py
Or use the .bat wrapper next to this file.
"""
import os, re, sys, glob, shutil, datetime, pathlib

MARKER = "QI Hive patch"
HOME = pathlib.Path(os.path.expanduser("~"))

# Discover targets by content, not by path — OpenClaw upgrades reshuffle
# bundle filenames (hash-based) and directory layout. We search recursively
# for any `delivery-*.js` containing the upstream function we care about.
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
            # Cheap content check before listing as a target.
            try:
                head = js.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "filterEmptyTelegramTextChunks" in head:
                found.append(js)
    return found

TARGETS = _discover_targets()

PATCH = r"""// QI Hive patch 2026-05-15 — also drop status-sentinel + session-metadata leaks
// before they reach Telegram. Source of leaks: small-LLM confabulation (gemma4:26b,
// qwen2.5:7b) emitting tokens like NO_OP / NO_RESPONSE / NO_RESPONSE_ERROR or
// summarising their own internal session metadata (Model: ollama/X, Tokens Used,
// Session Label: agent:...). Filtering at this single bottleneck catches all
// outbound agent text destined for any Telegram chat or topic.
// Re-apply with: python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py
const _QIHIVE_PLACEHOLDER_RE = /^\s*(NO[_\s][A-Z]{2,20}(?:[_\s][A-Z]{2,20}){0,3}|HEARTBEAT[_\s]?OK|\(silent\)|\[silent\]|STAY[_\s]SILENT|REMAIN[_\s]SILENT|NOTHING[_\s]TO[_\s](ADD|SAY)|NO[_\s]?COMMENT|\(no\s+response\)|\[no\s+response\]|\(no\s+reply\)|\[no\s+reply\])\s*[.!?]?\s*$/i;
// 2+ of these in one reply = treat as a metadata dump
const _QIHIVE_METADATA_PATTERNS = [
\t/Model:\s*ollama\//i,
\t/Session\s*Label:\s*agent:/i,
\t/Tokens?\s*Used:\s*\d/i,
\t/Context\s*Size:\s*\d+\s*tokens/i,
];
// ANY single match in this list = drop (agent is meta-commenting on its own context)
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
function _qihiveLooksLikeMetadataLeak(text) {
\tconst hits = _QIHIVE_METADATA_PATTERNS.reduce((n, re) => n + (re.test(text) ? 1 : 0), 0);
\tif (hits >= 2) return true;
\tfor (const re of _QIHIVE_META_COMMENTARY_PATTERNS) if (re.test(text)) return true;
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

def apply_to(target: pathlib.Path, ts: str) -> str:
    """Returns 'patched' | 'already' | 'missing' | 'pattern-not-found'."""
    if not target.exists():
        return "missing"
    src = target.read_text(encoding="utf-8")
    if MARKER in src:
        return "already"
    if not ORIGINAL_FN_RE.search(src):
        return "pattern-not-found"
    bak = target.with_name(target.name + f".bak-qihive-{ts}")
    shutil.copy2(target, bak)
    # Replacement string contains regex metacharacters (\s, etc.) — use lambda
    # so re.sub treats it as a literal substitution, not a backref template.
    literal = PATCH.replace("\\t", "\t")
    new = ORIGINAL_FN_RE.sub(lambda _m: literal, src, count=1)
    target.write_text(new, encoding="utf-8")
    return "patched"

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"QI Hive — apply_filter_patch.py @ {ts}")
    print(f"  HOME = {HOME}")
    print(f"  Targets: {len(TARGETS)}")
    counts = {"patched": 0, "already": 0, "missing": 0, "pattern-not-found": 0}
    for t in TARGETS:
        try:
            result = apply_to(t, ts)
        except Exception as e:
            print(f"  ERROR    {t}: {e}")
            counts.setdefault("error", 0)
            counts["error"] += 1
            continue
        counts[result] = counts.get(result, 0) + 1
        flag = {"patched": "✅ PATCHED ", "already": "·  already ",
                "missing": "?  missing ", "pattern-not-found": "⚠️  pattern-not-found"}[result]
        print(f"  {flag} {t}")
    print()
    print("Summary:", ", ".join(f"{k}={v}" for k, v in counts.items() if v))
    if counts.get("pattern-not-found"):
        print()
        print("⚠️  At least one target's pattern didn't match — OpenClaw upgrade may")
        print("    have renamed or restructured filterEmptyTelegramTextChunks().")
        print("    Inspect the file manually:")
        for t in TARGETS:
            print(f"      {t}")
        sys.exit(2)
    if counts.get("patched"):
        print()
        print("Patched files. Now restart gateways:")
        print("  systemctl --user restart openclaw-gateway openclaw-gateway-kaze")

if __name__ == "__main__":
    main()
