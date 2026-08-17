# 📋 Review Checklist — QI Free Cloud Program
### The item-by-item walkthrough agenda · prepared 2026-07-30
Mark each ☐ as we review together; corrections get applied to the doc on the spot. Suggested order = learning order.

## Session A — The AWS relay (done & live)
- ☐ [AWS_Free_Tier_Setup_Guide.md](AWS_Free_Tier_Setup_Guide.md) — Part 0 architecture · Part 1 account hygiene · Part 2 cloud side · Part 3 home side & cutover · gotchas log
- ☐ Live resources walkthrough in AWS console: Lambda `qi-maia-webhook`, queue `qi-maia-events.fifo`, SSM params, IAM role/user, budget alarm
- ☐ [lambda_function.py](C:\APPS\QI\TOOLS\aws_relay\lambda_function.py) — signature verification line by line
- ☐ [deploy_lambda.py](C:\APPS\QI\TOOLS\aws_relay\deploy_lambda.py) — idempotent deploy pattern + the dual-permission fix
- ☐ [queue_drainer.py](C:\APPS\QI\TOOLS\aws_relay\queue_drainer.py) — long-poll, verdicts, poison handling
- ☐ Maia patches: `channels/line.py` `_tok()` freshness logic · `make_push_sender()` in maia_server.py · `_line_webhook_url` cutover constant + rollback
- ☐ Bats: [Step 1.7 grant](AWS_Setup_Step_1_7_GrantRolePolicy.bat) · [Part 2 deploy](AWS_Setup_Part_2_DeployRelay.bat)
- ☐ Ops entries: QI_Service_Registry.md `QI_MaiaQueueDrain` · qi_registry.json `shared_infrastructure.aws`
- ☐ 48 h observation results (due ≈ 2026-08-01) + **the human test: Renne messages Maia from his phone**

## Session B — Containers & Kubernetes (done & proven)
- ☐ [Docker_Foundations_Guide.md](Docker_Foundations_Guide.md) — 5 lessons, 2 gotchas
- ☐ [Dockerfile](C:\APPS\QI\TOOLS\aws_relay\Dockerfile) + [docker-compose.yml](C:\APPS\QI\TOOLS\aws_relay\docker-compose.yml) (drainer + monitor sidecar)
- ☐ [queue_monitor.py](C:\APPS\QI\TOOLS\aws_relay\queue_monitor.py) — the C2 sidecar & its ALERT logic
- ☐ [K8s_Foundations_Guide.md](K8s_Foundations_Guide.md) — k3s, self-healing demo, parking pattern, gotchas
- ☐ [k8s/qi-relay.yaml](C:\APPS\QI\TOOLS\aws_relay\k8s\qi-relay.yaml) — Deployment + CronJob anatomy
- ☐ [helm/qi-bot chart](C:\APPS\QI\TOOLS\aws_relay\helm\qi-bot\) — chart vs values; `maia` + `demobot` releases = the template engine
- ☐ Check `C:\APPS\QI\LOGS\queue_report_k8s.log` — has the CronJob been firing every 15 min?

## Session C — Cloud brain scaffold (dormant, needs your decisions)
- ☐ [Cloud_Brain_M3_Activation.md](Cloud_Brain_M3_Activation.md) — **DECISION: privacy / local_only**
- ☐ [providers.py](C:\APPS\QI\TOOLS\aws_relay\cloud_brain\providers.py) — the adapter pattern, rung by rung
- ☐ [brain_lambda.py](C:\APPS\QI\TOOLS\aws_relay\cloud_brain\brain_lambda.py) — wake-on-stale-queue architecture
- ☐ DynamoDB table design (`chat_id` + `ts`) & shared-memory implications
- ☐ Activation checklist items 2–6 (the accounts only you can create)

## Session D — Strategy & vision docs
- ☐ [QI_Free_Cloud_Master_Plan.md](QI_Free_Cloud_Master_Plan.md) — milestones, deliverables standard, decisions table
- ☐ [Free_PolyCloud_Blueprint.md](Free_PolyCloud_Blueprint.md) — 5-rung chain, desktop→cloud map, Track C
- ☐ [Video 1 storyboard](video_storyboards/Video1_Your_Bot_Never_Misses_A_Message.md) — approve scenes before production

## Session E — The universal kit (shareable product, v0.1)
- ☐ [universal/README.md](universal/README.md) + [universal/GUIDE.md](universal/GUIDE.md) — neutral guide quality check
- ☐ [universal/config.env.example](universal/config.env.example) — is every parameter there?
- ☐ universal code files (lambda_function.py, deploy.py, queue_drainer.py, teardown.py, Dockerfile, compose, grant bat + policy template) — QA'd + clean-room certified 2026-07-30
- ☐ Decide: publish where? (GitHub repo under Quiddity-Innovations?)

## Open items carried by this checklist
| # | Item | Owner |
|---|---|---|
| 1 | Real LINE message from phone (closes M1 human test) | Renne |
| 2 | Privacy decision → gates M3 activation | Renne |
| 3 | Provider accounts/keys (OpenRouter, Gemini, Groq, CF token) | Renne |
| 4 | M4 week-long CronJob observation | time |
| 5 | Video 1 production (after storyboard approval) | Claude |
| 6 | M7 GitOps (needs GitHub remotes/tokens decision) | both |
| 7 | Universal kit publish decision (clean-room test ✅ PASSED 3/3 on 2026-07-30; teardown.py added) | Renne |
| 8 | Run AWS_Tighten_CLI_Policy.bat (replaces PowerUserAccess with program-scoped policy; rollback documented in bat) | Renne |
