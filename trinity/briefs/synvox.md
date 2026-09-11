# SynVox (synvox) — L2 brief

_Generated 2026-09-10 02:35:09_

## Registry facts
- Path: `C:\APPS\SynVox`
- Status: active_development
- Ports: api:8751, ai_router:8753
- Services: QI_SynVoxAPI
- Notes: Sibling tier - a product in its own right, not a tool of another project. Composes existing QI apps as engines: NEXUS (multi-model synthesis of results), EasyFlow/MailBrain (email-campaign simulation), Maia (multilingual conversational layer for chatbot evals), CogniBase (RAG store for ingested market reports). Reached through the QI Connector rather than owning its own MCP server in Phase 0-1; port block 8750-8759 is reserved for the Phase 5 standalone surface. Registered 2026-08-16.

## Brain
- Current state: status=active, phase=Phase 4 â€” evidence layer / reality check; monetisation deferred
  Session 12 (continued). Owner deferred monetisation: SynVox charges nobody, it is an internal tool for Renne and Urcil, and only enough endpoint surface was to be reserved for a future pricing model. Done and closed â€” synvox/billing.py holds the contract with no implementation, four routes (GET /v1/billing/plans, /account, /usage, POST /v1/billing/subscribe) answer 501 capability_disabled, capability_flags.billing is False, and all four were verified live. Nothing had to be moved: SynVox never had customer-billing code, and the two things that wear the word "price" â€” the pre-run cost gate and the Van Westendorp/Gabor-Granger instruments â€” are not billing and are now asserted untouched. The hard part is recorded rather than solved: on the subscription lane SynVox cannot measure money at all, so billing.METERABLE marks runs/personas/inference-calls countable and provider cost and tokens not, so nobody designs a plan on a number that reads zero for subscription-lane customers.

Acting on that led into /v1/capabilities, where three statements had been false for four sessions: the reality_check flag said the matcher was not built after D1..D6 built it, the honesty block asserted a FIXED reality-check status (wrong shape for a per-verdict outcome), and the note â€” rendered on two UI screens â€” told users grade A was unreachable until a layer that had already shipped. All three were pinned by two tests and a route-walk check, which is why nobody noticed. Fixed, and an over-broad guard that asserted on a whole file while claiming to be about evidence routes was narrowed.

D6b then attempted a second coverage gap and closed none, on the evidence: GitHub release-download velocity (cumulative counts with no timestamps make "latest > previous" near-structural), Open Collective cancellations (updatedAt is dominated by the platform's own billing sweep â€” 40 of 146 in the 00:00 UTC hour, busiest minutes 00:03 on the 21st of five months), and share-shift measures (attention moving between products is not people moving). The generalisation is the deliverable: a count can be dominated by the system rather than the users it describes â€” three instances now â€” and the test is "would this number move if no user did anything?". The follow-up audit of every change producer found nothing else and is closed.

Suite 1202 -> 1219 passed / 0 failed; reality_coverage unchanged at 2 of 6 (deliberately); every gate PASS; end-to-end study graded 3/3 in 105s at $0; 11/11 mutations caught.
- No project-scoped decisions recorded.

## CLAUDE.md rules
# SynVox — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
## Which session prompt is live (added 2026-08-21, Session 7)
never to decide what to do next.

Three rules that follow, and the reason each exists:

1. **Never edit a prompt after a session has started on it.** Session 6 read
   `SESSION_6_PROMPT.md` at 01:00; two owner decisions — the four-model lineup and the
   statistical-data scout brief — were appended to that same file at 08:38. The session
   finished against a document that no longer existed and never saw either decision.
   Mid-session material goes in `docs\Session_<N>_Open_Items.md`, or into the chat.
2. **Do not name a file as though it is permanently current.** `HANDOFF_NEXT_SESSION.md`
   was written at the close of Session 3 and its name kept claiming otherwise through
   five subsequent sessions.
## What SynVox is
## Layout
- `engine\matraix` — the MatrAIx repo (MIT). **Upstream code — do not edit it.** Our work
  goes in `tools\`, `tasks\` and `cohorts\`, or upstream as a PR.
- `engine\matraix\.venv` — uv-managed Python 3.12. Always run through it:
  `uv run --project engine\matraix python …`
- `engine\matraix\persona\datasets\matraix-persona-1m\release` — 999,847 personas,
  10 Zstd Parquet shards, 4.17 GB. Never commit it, never copy it around.
- `tools\persona_explore.py` — free segment profiler (no LLM calls).
- `logs\` — one master log per bootstrap run. Every success **and** failure.
## Ports
Block **8750-8759** is reserved for SynVox in `qi_registry.json`. Do not take a port outside
that block. Phase 2 tools live on the QI Connector (:9030), not on a new service.

## The subscription lane (owner decision, 2026-08-17 — QI Brain #530)
Three consequences that are **not** bugs and must not be "fixed":

1. **No token counts, no cost.** `claude -p` reports neither, so the router omits `usage`
objection was never the service; it was that an NSSM service runs under a service account
and the QI Connector's executor runs as **NT AUTHORITY\SYSTEM**, so installing it would
put *one person's consumer Claude Max subscription* behind a machine-wide always-on
endpoint. A provider-agnostic Router dissolves that: the service is *the inference
gateway*, and the Claude subscription is one backend that can be switched off.
**Order, and do not skip a step:**

1. A non-Claude model must be genuinely selectable. **Done** — `granite3.1-dense:8b` is
   registered, the Ollama lane is enabled, and `openai/granite3.1-dense:8b` is offered for
   the persona role. A connection's model list is editable from Settings via
2. Model-name truth must be enforced so the indirection can never lie. **Done** — see the
   naming rule in "Rules for changes" below.
3. Generalise the Router. **Done 2026-08-21 (Session 8).** The Router is now an
   *inference gateway*, v0.2.0. `synvox\ai\targets.py` turns the config into a registry
   Budgets and queues are **per connection** — a spent Claude quota must not close the
   offline lane that exists precisely as the fallback. Proven end to end: a 3-persona
   study ran the whole SynVox pipeline on `granite3.1-dense:8b`, graded, 3/3, 0 errored,
   the Router stays a per-user foreground process (`python tools\run_router.py`); do not
   install `QI_SynVoxRouter` and do not add a `dispatch\scripts` entry for it.

The Router omits `usage` only when the provider genuinely reports none. `claude -p`
unchanged and must stay. Ollama *does* report tokens, and those are passed through
unaltered: dropping a number a provider actually measured would make a metered lane
look free, which is the same class of lie in the other direction.
## Rules for changes
   Never launch a persona run without an explicit budget statement first. On the
   subscription lane that statement is **calls × latency × concurrency**, not dollars
   (`2 personas = 2 calls ≈ 45s each = under 2 min`); the dollar figure is genuinely $0
   old rule stands verbatim: personas × turns × model, priced, before you start. Debug on
   **Sonnet** with 3–5 personas, then scale on Sonnet — this used to say "debug on Haiku"
   and that was wrong on this lane: **haiku fails the Router's JSON contract 10 times in
   The rule stands, and the reason it was given is **wrong** — corrected
   2026-08-21 (Session 8). It was not that "the verifier is not concurrency-safe
   and silently writes nothing, with no timeout and no error message". There
   never started, so nothing was executed and retrying is safe), decodes the
   UTF-16 message, and raises `VerifierExecutionError` instead of letting a
   failed exec vanish. Measured on a real 8-persona job at concurrency 3:
   the bug, so **rule 1b still binds on a stock checkout.**

   **D2b decided (2026-08-22): SynVox carries the branch locally, and the state
   "carried locally" created its own hazard: whether rule 1b binds is a property
   of *the checkout in front of you*, and somebody who measures 8/8 at
   concurrency 3 on this machine could reasonably conclude the rule is obsolete
   and write that down, while the next person on a stock clone loses half their
   scores with a zero exit code. So:
   as a gate. It reads the **source**, never the branch name — a branch is a
   label somebody chose, and a working tree can be edited without changing it.
   All three markers are required: half of 0005 measured 7/8, which is still a
   checkout has never been observed giving the other answer. Answer payloads were
   11.8 KB on both passing and failing trials throughout, so the personas were
   always fine; only the scoring was lost, and the run still exits 0 — which is
   what makes it dangerous. Canonical samples:
   `tasks\synvox-serial-sonnet-n8.yaml` and `tasks\synvox-c3-granite-n8.yaml`.
1c. **Never cut a candidate set with `sorted(ids)[:n]`.** Row id is a *data
   source* key in Persona 1M — the release is packed in contiguous blocks:

   comes from the seed, never from sorting — compiled scenarios hash their
   cohort. `tests\test_cohort_provenance.py` guards both call sites and fails
   the build if the sorted-slice pattern comes back.
   never market estimates. Every output says so. Never present a simulation result
   without its confidence grade and the reality-check beside it.

   it has never heard of. Both produced `status: agrees`, and `agrees` is what unlocks the
   grade-A path — so an artefact was reaching a confidence grade.

   Every rule now declares the `evidence_kind` it can read (`change` · `band` · `level`),
   and a level is **never** compared by sign; it needs a band or a baseline, and until one
   is supplied the honest answer is that it is not checkable. Claims that named a
   construct but could not be compared are reported in `reality_check.not_comparable`
   Two related refusals, both for the same reason — a rule that always has an answer is
   not a rule: a claim naming **two** constructs is evidence for neither (one sentence
   must not become an agreement and a disagreement at once), and churn and retention no
   longer share a comparator (rising churn supports a switch intent, rising retention
   contradicts it; they used to agree with each other).
   | hackernews | `level` | yes, `trend_days`, opt-in — ⚠️ but it could not fire at all until D4b fixed the cap test; see rule 2f |
   | wikipedia | `text` (summary) · `level` (Wikidata quantities) | no |
   | rag | `text` | no |
   | opencollective | `level` | yes, two adjacent windows, automatic — see rule 2h |
   | custom | whatever the instance config declares | operator's call |

   raised needed asking: which rules have a source that could ever satisfy them?
   Every source now carries `emits` and `emits_conditionally` as data, and every
   adapter carries `CLAIM_TEMPLATES`. Read the table for the story; run
   `tools\reality_coverage.py` for the answer, and see rule 2g.

   **github's "no" was closed in Session 10 (D1c), and the answer was a
   construct in `reality_check_rules.json` is about them. Issue volume was
   refused twice: `/issues` returns pull requests in the same array, and even
   filtered, rising issues means rising usage *or* rising breakage. A **star**
   checkable once somebody fetches a baseline, and a Wikipedia paragraph never does.
   Telling a reader to go and find the direction in a paragraph wastes their
   afternoon. A **rule** may never ask for `text`: no comparator reads prose, so
   such a rule could only ever produce `not_comparable`, and a rule that cannot
   fire looks like coverage.

   `synvox\grade\reality.py` — those two packages have never imported each other and
   the module docstrings say so on purpose. `tests\test_evidence_measure_declarations
   .py` fails the build on drift. Same arrangement for `RELIABILITIES`, three copies.
...(truncated — cap 150 lines)