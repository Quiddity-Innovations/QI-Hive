# Kubernetes Foundations — k3s, Self-Healing, and the Multi-Bot Helm Chart
### Track C stages C3–C4 (milestones M4 + M6 core) · built live 2026-07-30

**Cluster:** k3s v1.36.2, single node (`powerspec` = this machine's WSL2 Ubuntu 24.04). $0 forever.
**Guardrail honored:** all bot drainers ship **parked** (`replicas: 0`); NSSM `QI_MaiaQueueDrain` remains production until the cluster earns primacy.

---

## 📊 What was built and proven
| Item | Status | Evidence |
|---|---|---|
| k3s cluster installed (`curl get.k3s.io \| sh`) | ✅ | node Ready in ~15 s |
| Drainer image imported into cluster runtime | ✅ | `docker save … \| k3s ctr images import -` |
| Deployment + CronJob manifests ([k8s/qi-relay.yaml](C:\QI\TOOLS\aws_relay\k8s\qi-relay.yaml)) | ✅ | applied to namespace `qi` |
| **Self-healing demo** | ✅ PASS | pod force-killed → replacement Running in **14 s**, zero human action |
| CronJob `qi-queue-report` (every 15 min → `C:\QI\LOGS\queue_report_k8s.log`) | ✅ | the Task-Scheduler→CronJob conversion example |
| Helm installed (v3.21) + **`qi-bot` chart** | ✅ | [helm/qi-bot/](C:\QI\TOOLS\aws_relay\helm\qi-bot\) |
| **Two bots, one chart:** releases `maia` + `demobot` deployed side by side | ✅ | differ ONLY in values-*.yaml |
| `maia-monitor` sidecar live in-cluster (queue depth + health watch) | ✅ | 1/1 Running |

## The concepts, in the order they bit us

**1. A Deployment is a promise, not a process.** You declare "1 replica of this container should exist"; the cluster makes it true, forever. Our kill test: delete the pod → 14 s later an identical one exists. Compare NSSM: restarts a crashed service, but nobody restarts a *deleted* one, and NSSM state lives outside git. Manifests ARE the environment.

**2. Parking = `replicas: 0`.** The full config exists in the cluster, inert. Activation is `kubectl scale --replicas=1` — which is also exactly how handover-from-NSSM and rollback work. One consumer at a time.

**3. hostPath volumes are the single-node cheat.** Secrets/creds/logs mount straight from the Windows filesystem (`/mnt/c/...`). Honest limitation, documented in-manifest: a real multi-node cluster needs Secrets objects + PersistentVolumes — that upgrade belongs to M9 (Oracle cloud cluster).

**4. Helm = the template engine.** The chart is "what a bot IS" (deployment shape, mounts, env contract); a values file is "which bot this one is" (name, queue, webhook, secret file, monitor on/off). `helm install <name> qi-bot -f values-<name>.yaml` stamps out a complete bot runtime. **Proven with two simultaneous releases.** A third bot (George, Nova…) = copy a values file + one command — *plus* its own LINE channel + SQS queue on the cloud side (deploy.py handles that).

## ⚠ Gotchas log (all hit live)
- **Helm can't see k3s by default:** k3s writes kubeconfig to `/etc/rancher/k3s/k3s.yaml`, not `~/.kube/config`. `export KUBECONFIG=/etc/rancher/k3s/k3s.yaml` before any helm command (bake into `.bashrc`).
- **Docker images are invisible to k3s:** k3s uses its own containerd, not Docker's store. Import after every rebuild: `docker save <img> | k3s ctr images import -`, and set `imagePullPolicy: Never`.
- **WSL2 cluster lifetime:** the WSL VM keeps running while k3s (systemd service) runs, but a Windows reboot does NOT auto-start WSL. If the cluster ever becomes production, add a login/boot task that runs `wsl -d Ubuntu-24.04 --exec true`. For a learning cluster: accept it.
- **Git-Bash mangles `/qi/...` arguments** (MSYS path conversion turned SSM parameter names into `C:/Program Files/Git/qi/...`). Fix: `export MSYS_NO_PATHCONV=1` or run through Python.
- (Inherited from Docker stage: container→Windows-host networking still routes via the Cloudflare tunnel; k3s doesn't change that on WSL2.)

## Operating reference
```bash
# cluster status / workloads
wsl -d Ubuntu-24.04 -u root -- k3s kubectl -n qi get all
# hand production to the cluster (and back)
wsl -d Ubuntu-24.04 -u root -- k3s kubectl -n qi scale deploy/maia-drainer --replicas=1   # after: nssm stop QI_MaiaQueueDrain
# upgrade a bot after values/chart edits
wsl -d Ubuntu-24.04 -u root -- bash -c 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml && helm upgrade maia /mnt/c/QI/TOOLS/aws_relay/helm/qi-bot -n qi -f /mnt/c/QI/TOOLS/aws_relay/helm/qi-bot/values-maia.yaml'
```

**Next in track C:** C5 GitOps (M7) — Actions builds the image, cluster syncs from git. **Done-criteria still open for M4:** CronJob observed on schedule for a week (runs started 2026-07-30).
