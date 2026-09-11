# Retirement Analyzer (retirementanalyzer) — L2 brief

_Generated 2026-09-10 02:35:09_

## Registry facts
- Path: `C:\APPS\Retirement Analyzer`
- Status: paused
- Ports: api:8504, ui:7844
- Notes: Personal-finance utility. Automates the manual Fidelity portfolio review/rebalancing previously done by hand (see Downloads analysis docs), extended with a 5-year retirement-readiness planning layer.

## Brain
- Current state: status=paused, phase=v0.14 â€” Task 1 cleared; end-to-end walkthrough in progress
  712 tests pass, everything pushed, tree clean. Tier conservative, figures signed 2026-08-27, one detector firing (property exemptions). A blank disposable clone runs at C:\APPS\RetirementAnalyzer-TEST on 17844/18504 for the walkthrough; two of its steps have been walked and produced four defects. Resuming Sunday 2026-08-30.
- No project-scoped decisions recorded.

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
