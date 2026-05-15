# QI Hive — OpenClaw patches

OpenClaw is a third-party npm package (`openclaw@2026.4.26` and newer). Any
`npm update -g openclaw` wipes `node_modules` and reinstalls fresh upstream
files, losing local edits. The scripts in this directory re-inject QI-specific
patches that are required for our bots to behave well.

## Patches included

| File | What it does | First applied |
|---|---|---|
| `apply_filter_patch.py` | Re-injects the `filterEmptyTelegramTextChunks()` rewrite that drops status-token sentinels (NO_OP, NO_RESPONSE, NO_INPUT, NO_CONTEXT, NO_RESPONSE_ERROR, etc.) and OpenClaw session-metadata leaks (Model: ollama/X + Tokens Used + Session Label) before they reach Telegram. | 2026-05-15 |

## How to run

After ANY OpenClaw upgrade:

```bat
C:\QIH\engine\bin\openclaw_qi_patches\apply_filter_patch.bat
```

Or directly inside WSL:

```bash
python3 /mnt/c/QIH/engine/bin/openclaw_qi_patches/apply_filter_patch.py
systemctl --user restart openclaw-gateway openclaw-gateway-kaze
```

The Python script is **idempotent** — running it twice on an already-patched
install is a no-op (logged as `already`).

## What the script does, step by step

1. Locates every active `delivery-*.js` in:
   - `~/.npm-global/lib/node_modules/openclaw/dist/extensions/telegram/`
   - `~/.openclaw/plugin-runtime-deps/openclaw-*/dist/extensions/telegram/` (one per cached version)
2. Skips files already containing the `QI Hive patch` marker.
3. For unpatched files: backs up to `<file>.bak-qihive-<YYYYMMDD-HHMMSS>`, then replaces the body of `filterEmptyTelegramTextChunks()` with the QI version.
4. Reports a summary: `patched=N, already=M, missing=O, pattern-not-found=P`.
5. Exit code `0` on success, `2` if any target's source pattern didn't match
   (means OpenClaw renamed or restructured the function — inspect manually).

## When the pattern-not-found warning fires

The script searches for the exact upstream body of `filterEmptyTelegramTextChunks`:

```js
function filterEmptyTelegramTextChunks(chunks) {
    return chunks.filter((chunk) => chunk.text.trim().length > 0);
}
```

If OpenClaw modifies this function in a future release (renames, restructures,
or moves it), the regex won't match, and the script will refuse to touch
the file. In that case:

1. Read the file manually:
   `\\wsl$\Ubuntu-24.04\home\hyosuke\.npm-global\lib\node_modules\openclaw\dist\extensions\telegram\delivery-*.js`
2. Find the new equivalent function (likely still named similarly and located
   near `deliverTextReply`).
3. Update the regex in `apply_filter_patch.py` (`ORIGINAL_FN_RE`) to match the
   new pattern.
4. Re-run.

## Adding new patches over time

Whenever a new OpenClaw quirk requires a node_modules edit, add a sibling
script in this directory following the same idempotent pattern, and document
it in the table above. The `.bat` wrapper can chain multiple patch scripts.
