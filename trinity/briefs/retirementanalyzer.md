# Retirement Analyzer (retirementanalyzer) — L2 brief

_Generated 2026-09-12 02:35:04_

## Registry facts
- Path: `C:\APPS\Retirement Analyzer`
- Status: paused
- Ports: api:8504, ui:7844
- Notes: Personal-finance utility. Automates the manual Fidelity portfolio review/rebalancing previously done by hand (see Downloads analysis docs), extended with a 5-year retirement-readiness planning layer.

## Brain
- Current state: status=active, phase=analysis
  Deterministic scenario analysis is now complete and internally consistent. The two inputs previously carried as admitted placeholders - the US downsize rent and the contradictory life-expectancy pair - are both resolved: the rent by the owner's figure plus a swept band, the life expectancy by running all nine combinations instead of choosing one. Correcting the rent moved a real headline three years later; the longevity sweep showed longevity is close to irrelevant against the destination decision, which is reported plainly rather than dressed up.

A defect in the withdrawal-rate test was found and fixed during that sweep: it discarded the entire survivor phase. A year-by-year walk now runs alongside it.

Reporting is de-duplicated at the source: all narrative numbers are computed once in a shared figures module, which removed about twenty hand-typed literals from prose. The plain report exists in English, Portuguese and Japanese from one generator. Two automated gates now run before anything is sent.

Two gaps remain open by deliberate choice, each with its own named section rather than a footnote: foreign tax (both jurisdictions tax him; no US-Brazil treaty at all; Japan taxes US social security under its own treaty's Article 17(1) rather than the US Model rule) and long-term care (wholly unmodelled; the owner's view that it matters less abroad is recorded as his judgement, not as a result).

Everything remains private and outside the git repository. Nothing committed, published or uploaded.
- Last decisions:
  - A single steady-state ratio cannot test a plan that has phases; add a year-by-year walk alongside it (2026-09-11)

## CLAUDE.md rules
# RetirementAnalyzer — Claude Project Instructions
# Quiddity Innovations
## READ BEFORE ACTING
project, but under **rule R9 it is operationally independent**: it must run correctly
with every other QI service stopped and `C:\APPS\QI` and `C:\QIH` absent from disk.

structural change (ports, folders, configs, new files); never read them at runtime:
- `C:\QIH\ecosystem\QI_Standards.md` — all naming/folder/code conventions
- `C:\QIH\ecosystem\qi_registry.json` — all ports and project relationships
decisions, or headlines to the Hive, but never reads from it, never blocks on it, and
never fails because of it. Every outbound call is wrapped in `try/except` with a short
timeout, logs failure to the local master log, and continues.

Self-test: `python -c "import shared.montecarlo, shared.plans"` must succeed with QI
services stopped. Enforced by `tests\test_independence.py`.

## What RetirementAnalyzer Is
## Paths
> That path no longer exists (defect D1). Never write it.

## Ports (DO NOT CHANGE without updating qi_registry.json first)
## Parallel Projects — Do Not Break
## Standing authority (granted by the owner, 2026-09-04)
> "Can you set the rules to allow you to simply do it? I do not need to be
> approving it every single time."

**Do it, then report. Do not ask first** for any of the following:

- Writing a **verified external fact** into the profile — an SSA statement, a
allocation, a housing allowance, a risk appetite — do not stall. **Apply the
documented conservative default, state plainly that it was a default and what
the alternatives cost, and move on.** He can overrule any single number in one
line; he should not have to unblock the work to do it.

**Always still report** what was changed, what it moved, and what remains open.
Authority to act is not permission to be silent — and never to be silent about a
result that got *better* because of a change I made.

## Entry points
`Start_RetirementAnalyzer.bat`, `install_service.bat`, `main.py`, `mcp_server.py`
