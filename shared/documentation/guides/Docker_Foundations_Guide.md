# Docker Foundations — Containerizing an Existing Service
### Track C, stages C1–C2 of the [QI Free Cloud Master Plan](QI_Free_Cloud_Master_Plan.md)

**Subject app:** the Maia queue drainer (`C:\APPS\QI\TOOLS\aws_relay\queue_drainer.py`) — chosen because containerizing an *existing, running* service is the most common real-world Docker task.
**Status:** C1 complete 2026-07-30 — image built, live event processed end-to-end by the container. NSSM remains the production runner until the k3s stage (M4) proves cluster operation.

---

## 📊 Progress
| Step | Status | Date |
|---|---|---|
| C1.1 Docker Engine installed in WSL2 (Ubuntu 24.04) | ✅ | 2026-07-30 |
| C1.2 Drainer parameterized via env vars | ✅ | 2026-07-30 |
| C1.3 Dockerfile + image build (246 MB) | ✅ | 2026-07-30 |
| C1.4 docker-compose deployment with volume-mounted secrets | ✅ | 2026-07-30 |
| C1.5 Live test: queued LINE event processed by container | ✅ PASS | 2026-07-30 |
| C2 Multi-service compose stack | ⏳ | |

## 🧩 Components added (BOM)
| Component | Install | Purpose |
|---|---|---|
| Docker Engine 29.x + compose v2 | `wsl -d Ubuntu-24.04 -u root -- apt-get install docker.io docker-compose-v2` | Container runtime inside WSL2 (no Docker Desktop needed; Desktop GUI can be added later independently) |
| WSL2 + Ubuntu 24.04 | already present | Linux environment on Windows 11 |

## The five Docker lessons this stage teaches

**1. Parameterize before you containerize.** Hardcoded paths (`C:\APPS\QI\secrets\...`) are meaningless inside a container. First change: every external touchpoint (queue URL, target webhook, secret file, log file) became an env var with the old value as default — the script still runs identically outside Docker.

**2. Images hold code, volumes hold state, env holds config.** The [Dockerfile](C:\APPS\QI\TOOLS\aws_relay\Dockerfile) copies ONLY the script and installs deps. Secrets (`maia.env`, AWS credentials) are mounted **read-only** at runtime by [docker-compose.yml](C:\APPS\QI\TOOLS\aws_relay\docker-compose.yml); logs mount to the normal QI log folder. **Never bake a secret into an image** — images get shared, exported, cached.

**3. `python:3.12-slim` + `pip install` + `COPY` + `CMD` is 90% of real Dockerfiles.** Result: 246 MB self-contained image, reproducible anywhere.

**4. Networking is where containers bite (two real gotchas, both hit live):**
- ⚠ **WSL2 Docker DNS:** first build failed — containers couldn't resolve any hostname (WSL's internal DNS proxy is unreachable from Docker's bridge). Fix: `/etc/docker/daemon.json` → `{"dns": ["8.8.8.8", "1.1.1.1"]}` + `systemctl restart docker`.
- ⚠ **Container → Windows-host access:** `host.docker.internal`/`host-gateway` points at the WSL VM, not Windows, and the firewall blocks the NAT path. Pragmatic route: the container calls Maia through her own **Cloudflare tunnel URL** (already public, already secured). The "proper" answer (host networking / mirrored mode) is deferred to the k3s stage where it's solved once for everything.

**5. The queue made the migration risk-free.** While the container had the wrong route, events simply **waited in SQS** through every retry — then delivered the moment a working consumer appeared. Decoupled architecture turns "deployment mistake" into "brief delay" instead of "lost data." This is why the relay was built first.

## Operating reference
```bash
# start containerized drainer (STOP the NSSM one first — one consumer at a time)
wsl -d Ubuntu-24.04 -u root -- docker compose -f /mnt/c/QI/TOOLS/aws_relay/docker-compose.yml up -d --build
# logs / stop
wsl -d Ubuntu-24.04 -u root -- docker logs qi-maia-drainer --tail 20
wsl -d Ubuntu-24.04 -u root -- docker compose -f /mnt/c/QI/TOOLS/aws_relay/docker-compose.yml down
```
Rule of the parallel-run guardrail: NSSM `QI_MaiaQueueDrain` is production; the container is the learning/staging twin. Both up simultaneously is harmless (each message processed once) but makes logs confusing — pick one.

---
*Next: C2 (add a second compose service), then M3 (cloud brain). Living document.*
