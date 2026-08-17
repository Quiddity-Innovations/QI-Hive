# Cloud Brain (M3) — Scaffolded & Awaiting Activation
### Maia's degraded-but-alive mode · scaffold built 2026-07-30

**State:** all code + cloud plumbing exists; **deployment deliberately deferred** until the owner supplies API keys and decides the privacy policy. Nothing here consumes quota or money while dormant.

## Already built (dormant, $0)
| Piece | Where |
|---|---|
| 5-rung provider adapter chain (desktop-tunnel → Workers AI → OpenRouter → Gemini/Groq → honest static fallback) | [C:\APPS\QI\TOOLS\aws_relay\cloud_brain\providers.py](C:\APPS\QI\TOOLS\aws_relay\cloud_brain\providers.py) |
| Brain Lambda (queue-poll → chain → LINE push → DynamoDB memory) | [C:\APPS\QI\TOOLS\aws_relay\cloud_brain\brain_lambda.py](C:\APPS\QI\TOOLS\aws_relay\cloud_brain\brain_lambda.py) |
| Conversation store `qi-bot-conversations` (DynamoDB, on-demand, always-free 25 GB) | AWS |
| SSM key slots (all `PENDING_RENNE`): `/qi/llm/openrouter_key`, `gemini_key`, `groq_key`, `cf_workers_ai_token`, `desktop_ollama_url` | AWS SSM |
| Privacy default wired: `LOCAL_ONLY=1` → third-party rungs are skipped even if keys exist | code |

## ☑ Renne's activation checklist (each item ~5 min, all free)
1. **Privacy decision (gates everything):** may Maia use third-party LLMs (Cloudflare/OpenRouter/Google/Groq) when the desktop is offline? If NO → only items 5–6 matter.
2. OpenRouter: create account → API key → `aws ssm put-parameter --name "/qi/llm/openrouter_key" --type SecureString --value <KEY> --overwrite`
3. Google AI Studio: create API key → same command with `/qi/llm/gemini_key`
4. Groq Cloud: create account → key → `/qi/llm/groq_key`
5. Cloudflare: dashboard → Workers AI → API token → `/qi/llm/cf_workers_ai_token` (plus account ID for env `QI_CF_ACCOUNT_ID`)
6. Desktop rung: we create an authenticated tunnel exposing Ollama (Claude does this WITH you — it touches your Cloudflare DNS) → URL into `/qi/llm/desktop_ollama_url`
7. Say "activate cloud brain" → Claude deploys the Lambda (reusing the deploy.py pattern), wires the CloudWatch queue-age alarm (fires when the home drainer stops draining ≥2 min), tests by stopping the drainer and messaging Maia.

## Design notes (for the review session)
- The brain wakes ONLY when the queue goes stale (alarm on `ApproximateAgeOfOldestMessage`) — zero cost and zero interference while the home drainer is healthy.
- Conversation memory in DynamoDB is shared ground truth: home brain and cloud brain can each continue a conversation the other started (home-side read/write of the table is a small M3 follow-up in `maia_server.py`).
- Rung 5 today is an honest "I'm in emergency mode" message — the tiny-CPU-model-in-Lambda experiment can replace it later without touching the chain interface.
