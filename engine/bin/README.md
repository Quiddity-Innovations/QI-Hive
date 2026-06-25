# engine/bin — tooling binaries

These are **runtime tooling binaries**. With one exception they are **git-ignored**
(`.gitignore` → `engine/bin/*.exe`) and must live on disk, not in source control —
they bloat history permanently and are freely re-downloadable. This file documents
what each one is and where to get it, so an ignored binary is never a mystery.

| Binary | Purpose | Source | In git? |
|---|---|---|---|
| `nssm.exe` | Non-Sucking Service Manager — the **standardized** manager for every `QI_*` Windows service (see CLAUDE.md). | https://nssm.cc/download | ✅ tracked (sanctioned, stable) |
| `caddy.exe` | Caddy web server / reverse proxy (~51 MB). Used by `engine/proxy/`. | https://caddyserver.com/download | ❌ ignored |
| `rcedit.exe` | Electron `rcedit` — sets the Windows `FileDescription` resource on the per-product NSSM copies (so the UAC prompt names the product, not "nssm"). | https://github.com/electron/rcedit/releases | ❌ ignored |
| `*_NSSM.exe` | Per-product renamed copies of `nssm.exe` (Maia_NSSM, Brain_NSSM, …). Generated from `nssm.exe` by setting `FileDescription` with `rcedit`. Part of the service-naming-standardization work. | Generated locally from `nssm.exe` | ❌ ignored |

## Regenerating the per-product NSSM copies
The `*_NSSM.exe` copies are produced from `nssm.exe` + `rcedit.exe`; see
`tools/naming_standardization/` for the generator. They are disposable — if missing,
re-run the generator rather than restoring from git.
