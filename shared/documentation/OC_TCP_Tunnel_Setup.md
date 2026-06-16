# OpenClaw TCP Tunnel — Setup Path

**Status:** ⏳ NOT YET SET UP. Requires Renne's interactive Cloudflare account work.

**Context:** OpenClaw runs in WSL listening on `0.0.0.0:18789` as a non-HTTP TCP gateway. Cloudflare Quick Tunnels (`cloudflared tunnel --url http://...`) only support HTTP, so OC cannot be exposed the same way Maia/Naya/NEXUS/CogniBase/MapSnap are. TCP requires Cloudflare's Zero Trust private network feature.

## Why Quick Tunnel doesn't work

```powershell
& 'C:\Program Files (x86)\cloudflared\cloudflared.exe' tunnel --url http://localhost:18789
```

This wraps HTTP. OC speaks something else over TCP (handshake times out on HTTP probe). Cloudflare would receive HTTP requests from the public URL and try to forward them as HTTP to the local port — OC would reject them.

## What's actually needed

Cloudflare **Zero Trust private networking** with `cloudflared access tcp`. End-to-end:

### One-time setup (interactive — Renne does these)
1. `cloudflared tunnel login` — opens browser, auth against Cloudflare account, downloads cert to `%USERPROFILE%\.cloudflared\cert.pem`.
2. Sign up for **Cloudflare Zero Trust** (free tier covers up to 50 users).
3. Create named tunnel:
   ```
   cloudflared tunnel create qi-openclaw
   ```
4. In Cloudflare Zero Trust dashboard → **Networks → Tunnels**, configure the new tunnel's **Private Network** route: `10.0.0.0/24` (or wherever Renne's machine sits) on TCP port `18789`.
5. Install WARP client on every device that should reach OC (phone, laptop, etc.) and enroll them in the Zero Trust org.

### Service install (one-time, after #1–5 done)
NSSM service running:
```
cloudflared tunnel run qi-openclaw
```
With `~/.cloudflared/<tunnel-id>.json` credentials file.

### On the client side
`cloudflared access tcp --hostname openclaw.<your-domain> --url 127.0.0.1:18789` (or use WARP and connect directly to private IP).

## Alternative: skip TCP, expose a different OC interface

OpenClaw also has a Node HTTP supervisor at `127.0.0.1:18800` (Kaze config API, listed earlier). That IS HTTP and could be Quick-Tunneled today with the same pattern as the other 6 tunnels. But it's a partial surface — only Kaze admin, not the full agent gateway.

## Recommendation

Defer until Renne wants OC demoable from outside. The cost is mostly interactive (Cloudflare account work + WARP install), not technical. When ready, this doc has the steps.
