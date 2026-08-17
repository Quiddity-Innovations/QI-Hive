# Phase 5 — Installer Packaging Plan (PLAN ONLY, nothing built)

**Author:** Claude Opus 5 session, 2026-08-09
**Status:** Design document. No build tooling has been installed or run.
**Depends on:** Phase 4 (code/data separation) being complete. Packaging a QI app
before its data paths move out of the code directory is not possible — see §2.

---

## 1. What we are actually packaging

Not "the QI ecosystem". The ecosystem is 27 registered projects plus 52 Windows
services, most of which are internal plumbing (tunnels, drains, brokers) that will
never ship to a third party. Packaging effort should target the small set of apps
that a non-Renne user could plausibly install:

| Tier | Apps | Ship as |
|---|---|---|
| **A — product candidates** | MapSnap, AutoPDF, TubeScout, Retirement Analyzer, Lottery Wiz | Signed installer, standalone |
| **B — internal, but installable** | CogniBase, PlayDeck, EasyFlow | Installer, no signing initially |
| **C — never ships** | QIH engine, tunnels, drains, brokers, Gate, Elevate | Stays a git checkout + NSSM |

Do Tier A only. Tier B follows the same recipe once Tier A is proven. Tier C is
explicitly out of scope — trying to package the Hive engine is what would turn this
into a year-long project.

---

## 2. Hard prerequisite: Phase 4 must land first

Today every app writes beside its own code:

```
C:\QI\LOGS\maia_service_log.txt
C:\QI\maia.db
C:\NEXUS\LOGS\nexus_service.log
C:\PlayDeck\data\logs\service_out.log
```

`C:\Program Files\<app>` is read-only for non-elevated processes. An app that
writes next to its `.exe` either fails at first run or silently triggers UAC
virtualisation. So the Phase 4 resolver is not a nice-to-have — it is the gate.

Required end state before any packaging work starts:

| Kind | Location | Env var |
|---|---|---|
| Code / binaries | `C:\Program Files\Quiddity Innovations\<App>` | — |
| Machine data (DBs, shared state) | `C:\ProgramData\Quiddity Innovations\<App>` | `QI_DATA_DIR` |
| Per-user config | `%APPDATA%\Quiddity Innovations\<App>` | `QI_CONFIG_DIR` |
| Cache + logs | `%LOCALAPPDATA%\Quiddity Innovations\<App>\Logs` | `QI_LOG_DIR` |

**Acceptance test for Phase 4 readiness:** copy the app directory to a path the
user cannot write to, run it as a standard user, and confirm it starts, logs, and
persists. Until that passes, packaging is blocked.

---

## 3. Freezer: PyInstaller vs Nuitka

| | **PyInstaller** | **Nuitka** |
|---|---|---|
| Mechanism | Bundles CPython + bytecode into an archive | Compiles Python to C, then to a real binary |
| Build time | Fast (1-3 min typical) | Slow (10-40 min, C compiler required) |
| Output size | Large but predictable | Comparable; sometimes smaller |
| Startup | Slower (unpacks to temp on onefile) | Faster |
| Source protection | Weak — bytecode trivially recoverable | Strong — genuinely compiled |
| Hidden-import pain | Common; needs `--hidden-import` / hooks | Also present, different failure modes |
| Ecosystem support | Excellent; hooks exist for most packages | Good and improving, thinner for exotic packages |
| Licence | GPL w/ commercial exception for output | Apache 2.0 (Nuitka commercial for some features) |
| Torch / transformers | Known-workable with effort | Known-painful |

**Recommendation: PyInstaller, `--onedir` (not `--onefile`).**

Reasons:
- Build-iterate loop matters more than binary purity at this stage. A 40-minute
  Nuitka cycle will kill momentum.
- `--onedir` avoids the temp-extraction startup cost and — more importantly —
  makes installer-level differential updates possible later. `--onefile` is a
  single opaque blob that must be replaced wholesale every release.
- Source protection is not a real requirement yet. None of Tier A is being sold to
  an adversarial customer today. Revisit Nuitka if that changes.
- Several Tier A apps pull in `numpy`/`pandas`; PyInstaller's hook coverage there is
  mature.

**Revisit trigger:** if an app ships to a paying external customer *and* the source
is genuinely commercially sensitive, re-evaluate Nuitka for that one app only.

### Known freezer traps for this codebase
- **FastAPI/uvicorn** — `uvicorn` loads its loop/protocol implementations by string
  name. Requires `--hidden-import uvicorn.logging`, `uvicorn.loops.auto`,
  `uvicorn.protocols.*`, `uvicorn.lifespan.on`. Every Tier A app uses this.
- **Gradio** (Maia/Naya, Tier C but worth noting) — ships a large JS/template tree
  that must be added via `--add-data`. Gradio is a well-known PyInstaller problem
  child; another reason those stay Tier C.
- **ChromaDB / sqlite** — native extensions; verify the `.pyd` is collected.
- **certifi** — must be bundled or HTTPS fails only on the target machine.
- `sys._MEIPASS` must be handled in the path resolver so bundled read-only assets
  resolve correctly while writable data still goes to ProgramData.

---

## 4. Installer: Inno Setup vs WiX

| | **Inno Setup** | **WiX Toolset** |
|---|---|---|
| Authoring | Pascal-ish `.iss` script, very readable | XML, verbose, steep curve |
| Output | `setup.exe` | `.msi` (+ optional bootstrapper) |
| Learning cost | Low — productive in an afternoon | High — days |
| Per-machine + service install | Supported via `[Run]` / Pascal code | First-class (ServiceInstall/ServiceControl) |
| Group Policy / SCCM deployment | Not really | Yes — MSI is the enterprise format |
| Upgrade/patch semantics | Manual but simple | Formal, powerful, unforgiving |
| Signing | Straightforward | Straightforward |

**Recommendation: Inno Setup for Tier A now.**

Reasons:
- Tier A apps are consumer-ish desktop/web-local tools, not enterprise fleet
  deployments. Nobody is pushing MapSnap via SCCM.
- The NSSM service registration these apps need is a shell-out, which Inno's
  `[Run]` section handles trivially. Expressing the same in WiX's ServiceInstall is
  more correct but far more work — and we would be fighting WiX to install a
  *third-party* service wrapper anyway.
- One `.iss` per app can be generated from a shared template, keeping 5 installers
  maintainable by one person.

**Switch to WiX if and when** an enterprise customer requires `.msi`, Group Policy
deployment, or formal patch (MSP) semantics. Design the `.iss` so that switch is
possible: keep the file layout and registry keys declarative, not scattered through
Pascal code.

### Installer responsibilities per app
1. Install code to `C:\Program Files\Quiddity Innovations\<App>`.
2. Create `C:\ProgramData\Quiddity Innovations\<App>` with an ACL granting Users
   write access (or Modify for the service account only, if stricter).
3. Register the NSSM service as `QI_<App>` — prefix, Description, and AppDirectory
   set per the QI service naming rule.
4. Write the port allocation from the project's registered block; fail loudly on
   conflict rather than silently picking a neighbouring port.
5. Start menu shortcut to the local UI URL.
6. Uninstall: stop + remove the service, delete code. **Leave ProgramData in place**
   unless the user ticks "also remove my data" — deleting a user's database on
   uninstall is the classic unforgivable installer bug.

---

## 5. Code signing

Unsigned installers get SmartScreen-blocked, which for a small publisher reads as
"this is malware". Options:

| Option | Cost/yr | SmartScreen | Notes |
|---|---|---|---|
| **OV code-signing cert** | ~$200-400 | Reputation must be *earned* over weeks/downloads | Since Jun 2023 must live on FIPS-140-2 hardware or a cloud HSM |
| **EV code-signing cert** | ~$400-700 | **Immediate** SmartScreen trust | Hardware token or cloud HSM mandatory; identity vetting is heavier |
| Self-signed | £0 | None — worse than unsigned | Only useful for internal machines with the root pre-trusted |
| Unsigned | £0 | Blocked | Acceptable only while Renne is the sole user |

**Recommendation:** stay unsigned while the audience is Renne and trusted testers.
The moment an app goes to a real external user, buy **EV** rather than OV. The
immediate-reputation property is the entire point; an OV cert that spends six weeks
accruing reputation while early users hit scary warnings is a false economy.

Practical notes:
- The 2023 hardware-storage requirement means no more "cert file on the build
  machine". Use a cloud signing service (Azure Trusted Signing, DigiCert KeyLocker,
  SSL.com eSigner) so CI can sign without a physical token in a USB port.
- **Azure Trusted Signing is the cheapest credible route** (~$10/month) if the
  identity requirements are met — worth checking eligibility first, as it has a
  business-age requirement that a young entity may fail.
- Sign **both** the frozen `.exe` files and the final `setup.exe`. Signing only the
  installer leaves the inner binaries untrusted.
- Timestamp every signature (`/tr`), or everything breaks when the cert expires.

---

## 6. Recommended stack (summary)

```
source  ->  PyInstaller --onedir   ->  Inno Setup .iss  ->  signtool (EV, later)
                                          |
                                          +-- NSSM service registration
                                          +-- ProgramData provisioning + ACL
```

- **Freezer:** PyInstaller, `--onedir`
- **Installer:** Inno Setup 6
- **Signing:** none now; EV via cloud HSM at first external release
- **Scope:** Tier A only (5 apps)

---

## 7. Suggested sequencing (when this gets built)

1. Finish Phase 4 for **one** app end-to-end. Recommend **AutoPDF** as the pilot: it
   already has a `data/` convention and a relatively contained dependency set.
2. Prove the read-only-directory acceptance test from §2 for that app.
3. PyInstaller spec for it; get a working `--onedir` build.
4. Write `installer/common.iss` (shared macros) + `installer/autopdf.iss`.
5. Install on a **clean VM** as a standard user. This is non-negotiable — building
   and testing on the dev machine hides every missing-dependency bug, because the
   dev machine already has them.
6. Only then template out to the remaining four Tier A apps.
7. Revisit signing at first external release.

**Estimated effort:** 2-3 focused sessions for the pilot, then roughly half a
session per additional app.

---

## 8. Open questions for Renne

1. Is any Tier A app actually going to an external user in the next 6 months? The
   answer decides whether signing is urgent or theoretical.
2. Is source protection a real requirement for any of them? Only that would justify
   Nuitka's build-time cost.
3. Should Tier A installers bundle their own Python, or assume the machine has one?
   (Recommendation: bundle — freezing exists precisely so the user never installs
   Python. This is also the argument for keeping the Phase 2 per-machine Python as a
   *development* dependency only, not a shipping one.)
