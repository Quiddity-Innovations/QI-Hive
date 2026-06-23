# QI Static (Named) Cloudflare Tunnels

**Created:** 2026-06-20 · **Domain:** `quiddityinnovations.com` (Cloudflare) · **Owner:** Renne / Quiddity Innovations

This folder migrates every QI **quick tunnel** (random `*.trycloudflare.com` URL that
changes on every restart) into a **static named tunnel** bound to a permanent subdomain
of `quiddityinnovations.com`.

## Design — hybrid, fault-isolated
One named tunnel **per product**, so a tunnel failure only takes that product offline.
The single consolidation is Maia's two endpoints (bot + demo) sharing `qi-maia`, because
they are the same product. See `tunnels.json` for the authoritative map.

| Tunnel | Service | Public hostname(s) → local port |
|---|---|---|
| qi-maia | QI_MaiaTunnel | maia → 8001, maia-demo → 7860 |
| qi-naya | QI_NayaTunnel | naya → 7861 |
| qi-nexus | QI_NEXUSTunnel | nexus → 7880 |
| qi-hive | QI_DashboardTunnel | hive → 8600 |
| qi-autopdf | QI_AutoPDFTunnel | autopdf → 6969 |
| qi-cognibase | QI_CogniBaseTunnel | cognibase → 8650 |
| qi-mapsnap | QI_MapSnapTunnel | mapsnap → 9876 |
| qi-lotterywiz | QI_LotteryWizTunnel | lottery → 8777 |
| qi-cypherminer | QI_CypherMinerTunnel | cypher → 7842 |
| qi-kaze | QI_KazeNewsTunnel | kaze → 18800 |
| qi-tubescout | QI_TubeScoutTunnel | tubescout → 8503 |
| qi-gamez | QI_GamezTunnel *(new)* | gamez → 8710 |

### Second domain — `quiddam.com` (Maia Quiddam / MQ)
| Tunnel | Service | Public hostname(s) → local port |
|---|---|---|
| qi-mq | QI_MQTunnel *(new)* | quiddam.com (apex) → 7840 · api → 8500 · dev → 7849 *(reserved)* · maia → 8599 *(reserved)* |

**Multi-domain support:** a tunnel entry may set `"domain": "quiddam.com"` to override the
default domain, and a hostname of `"@"` means the **zone apex** (the bare domain). One toolchain,
any number of domains on the account.

`QI_MaiaDemoTunnel` is **retired** (stopped + disabled) — its 7860 endpoint is now an
ingress rule inside `qi-maia`.

## How to run (two manual steps only)

1. **Authenticate once** — in a normal (non-elevated) terminal, as yourself:
   ```
   cloudflared tunnel login
   ```
   A browser opens → select **quiddityinnovations.com** → writes `%USERPROFILE%\.cloudflared\cert.pem`.

2. **Run the migration** — double-click **`RUN_MIGRATION.bat`** (it self-elevates to admin).
   Or from an elevated terminal:
   ```
   python migrate_named_tunnels.py
   ```

Preview without changing anything:
```
python migrate_named_tunnels.py --dry-run
```

## Files
| File | What |
|---|---|
| `tunnels.json` | Master map — the single source of truth. Edit here to add/change a tunnel. |
| `migrate_named_tunnels.py` | Idempotent migrator: create tunnel → route DNS → write config → reconfigure NSSM. |
| `verify_named_tunnels.py` | Health check: tunnel exists, DNS resolves, service running, HTTPS responds. |
| `RUN_MIGRATION.bat` | Self-elevating one-click runner (migrate + verify). |
| `configs/<name>.yml` | Generated ingress config per tunnel (cloudflared `--config`). |
| `creds/<name>.json` | Tunnel credentials, copied from `~/.cloudflared` so LocalSystem services can read by absolute path. |

## Notes
- Idempotent: re-running skips existing tunnels, re-routes DNS with `--overwrite-dns`, rewrites configs.
- The NSSM services run as **LocalSystem** and only need `tunnel run` (reads `creds/<name>.json`
  by absolute path). They do **not** need `cert.pem` — only the management commands (create/route) do.
- Add a project: append an entry to `tunnels.json`, then `python migrate_named_tunnels.py --only <name>`.
- Consumers that previously read a quick-URL file (Hive dashboard `status/tunnel.json`,
  Kaze `news-tunnel-url.txt`) are rewritten with the static `https://<host>.quiddityinnovations.com` URL.
