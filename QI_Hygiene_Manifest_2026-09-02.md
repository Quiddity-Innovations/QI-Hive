# QI Hygiene Manifest — enumerated approval list

**Generated:** 2026-09-02 15:28 · **Status:** awaiting owner approval
**Nothing in this file has been deleted or moved.** This is the D4 approval list.

Proposed action for every item below is **MOVE to `C:\QIH\_archive\hygiene_2026-09-02\`**, preserving relative paths — not delete. Fully reversible.

## Totals

| Category | Count | Size |
|---|---|---|
| Stray Claude worktrees | 37 | 1GB |
| `.bak-*` / `.backup-*` files | 1792 | 520MB |
| &nbsp;&nbsp;of which **orphaned** (no live original) | 59 | — |
| **TOTAL** | **1829** | **2GB** |

## Section 1 — Stray Claude Code worktrees

Abandoned agent worktrees under `<project>/.claude/worktrees/`. These inflate the
tree, pollute greps with phantom matches, and are not referenced by any service.

⚠️ **MailBrain's are the exception** — see §5.5 of the architecture plan. MailBrain
has no repository of its own, so verify nothing unique lives in these before moving.

| # | Project | Worktree | Files | Size | Newest | Action |
|---|---|---|---|---|---|---|
| 1 | QI | `reverent-lichterman` | 336 | 120MB | 2026-04-15 | MOVE |
| 2 | QI | `clever-merkle` | 336 | 120MB | 2026-04-13 | MOVE |
| 3 | QI | `funny-grothendieck` | 330 | 119MB | 2026-04-09 | MOVE |
| 4 | QI | `beautiful-dewdney` | 330 | 119MB | 2026-04-09 | MOVE |
| 5 | AutoPDF | `affectionate-greider-c42a91` | 281 | 61MB | 2026-08-07 | MOVE |
| 6 | MailBrain ⚠️ | `gifted-visvesvaraya-d6aa5b` | 304 | 33MB | 2026-04-20 | MOVE |
| 7 | MailBrain ⚠️ | `beautiful-shtern-c08de1` | 303 | 33MB | 2026-05-03 | MOVE |
| 8 | MailBrain ⚠️ | `thirsty-booth-d52f75` | 303 | 33MB | 2026-05-09 | MOVE |
| 9 | MailBrain ⚠️ | `nice-clarke-f9ba44` | 303 | 33MB | 2026-04-22 | MOVE |
| 10 | MailBrain ⚠️ | `youthful-shaw-e677fd` | 297 | 32MB | 2026-04-20 | MOVE |
| 11 | EasyFlow | `crazy-mclaren` | 219 | 30MB | 2026-04-15 | MOVE |
| 12 | MailBrain ⚠️ | `crazy-mclaren` | 219 | 30MB | 2026-04-15 | MOVE |
| 13 | MailBrain ⚠️ | `jolly-jennings-61015c` | 218 | 30MB | 2026-04-16 | MOVE |
| 14 | MailBrain ⚠️ | `vibrant-volhard` | 218 | 30MB | 2026-04-14 | MOVE |
| 15 | MailBrain ⚠️ | `peaceful-germain` | 218 | 30MB | 2026-04-14 | MOVE |
| 16 | MailBrain ⚠️ | `gallant-kare` | 198 | 29MB | 2026-04-14 | MOVE |
| 17 | MailBrain ⚠️ | `condescending-greider` | 198 | 29MB | 2026-04-14 | MOVE |
| 18 | MailBrain ⚠️ | `exciting-kapitsa` | 198 | 29MB | 2026-04-14 | MOVE |
| 19 | EasyFlow | `nice-ellis` | 194 | 29MB | 2026-04-13 | MOVE |
| 20 | MailBrain ⚠️ | `nice-ellis` | 194 | 29MB | 2026-04-13 | MOVE |
| 21 | CogniBase | `clever-poincare-c95cf2` | 274 | 13MB | 2026-05-13 | MOVE |
| 22 | CogniBase | `great-babbage-72abfc` | 241 | 6MB | 2026-05-12 | MOVE |
| 23 | OC | `stoic-tharp-1781fa` | 134 | 3MB | 2026-04-24 | MOVE |
| 24 | OC | `gallant-davinci-4b3d88` | 134 | 3MB | 2026-05-13 | MOVE |
| 25 | OC | `eager-spence-2ebfb3` | 134 | 3MB | 2026-04-25 | MOVE |
| 26 | CogniBase | `nice-chatelet-5f1c92` | 168 | 2MB | 2026-05-12 | MOVE |
| 27 | MapSnap | `brave-hawking-6bc3b3` | 56 | 1MB | 2026-05-14 | MOVE |
| 28 | CogniBase | `great-bohr-1e3dab` | 131 | 1MB | 2026-05-11 | MOVE |
| 29 | MapSnap | `awesome-moser-b60408` | 39 | 845KB | 2026-05-12 | MOVE |
| 30 | MapSnap | `eager-hypatia-d0157a` | 38 | 833KB | 2026-05-13 | MOVE |
| 31 | MapSnap | `affectionate-rhodes-80034a` | 33 | 832KB | 2026-05-11 | MOVE |
| 32 | MapSnap | `hopeful-euclid-94b5ae` | 32 | 771KB | 2026-05-11 | MOVE |
| 33 | MapSnap | `vigilant-satoshi-33c5e9` | 31 | 770KB | 2026-05-08 | MOVE |
| 34 | MapSnap | `stoic-knuth-d13296` | 31 | 770KB | 2026-05-08 | MOVE |
| 35 | Retirement Analyzer | `quizzical-zhukovsky-cb1be1` | 2 | 788B | 2026-07-02 | MOVE |
| 36 | QI | `frosty-almeida` | 0 | 0B | - | MOVE |
| 37 | QI | `jolly-torvalds` | 0 | 0B | - | MOVE |

**Full paths:** all under `C:\APPS\<project>\.claude\worktrees\`

## Section 2 — `.bak-*` and `.backup-*` files

Sibling backup copies written next to the original during past migrations.
**Orphaned** = the file it backed up no longer exists, so the backup is the only
copy of that content — review those before moving.

| Project | Count | Size | Orphaned | Action |
|---|---|---|---|---|
| QIH | 512 | 330MB | **29** ⚠️ | MOVE |
| QI | 310 | 8MB | **2** ⚠️ | MOVE |
| CLAUDE | 154 | 6MB | 0 | MOVE |
| OC | 111 | 320KB | 0 | MOVE |
| NAYA | 96 | 1MB | **1** ⚠️ | MOVE |
| AutoPDF | 93 | 703KB | **1** ⚠️ | MOVE |
| PersonalSong | 77 | 204KB | 0 | MOVE |
| MailBrain | 64 | 371KB | 0 | MOVE |
| EasyFlow | 63 | 375KB | 0 | MOVE |
| NEXUS | 49 | 1MB | **1** ⚠️ | MOVE |
| CogniBase | 47 | 14MB | **1** ⚠️ | MOVE |
| SynVox | 30 | 961KB | **1** ⚠️ | MOVE |
| QIP | 25 | 80KB | **3** ⚠️ | MOVE |
| TUBESCOUT | 25 | 158KB | 0 | MOVE |
| MapSnap | 24 | 155MB | **20** ⚠️ | MOVE |
| Gamez | 22 | 474KB | 0 | MOVE |
| CypherMiner | 15 | 80KB | 0 | MOVE |
| Lottery Wiz | 15 | 191KB | 0 | MOVE |
| MQ | 14 | 69KB | 0 | MOVE |
| AkiyaScout | 10 | 80KB | 0 | MOVE |
| M2V | 10 | 61KB | 0 | MOVE |
| Retirement Analyzer | 10 | 812KB | 0 | MOVE |
| AutoPDF_Portable_Dupe | 7 | 28KB | 0 | MOVE |
| MediaStudio | 4 | 68KB | 0 | MOVE |
| PlayDeck | 2 | 4KB | 0 | MOVE |
| AvatarStudio | 1 | 105KB | 0 | MOVE |
| VLCDaemon | 1 | 6KB | 0 | MOVE |
| VoiceStudio | 1 | 3KB | 0 | MOVE |

### Orphaned backups — review individually before moving

| Path | Size | Date |
|---|---|---|
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260512_135625.bak` | 22MB | 2026-05-08 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260512_135625.bak` | 22MB | 2026-05-08 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260515_192117.bak` | 12MB | 2026-05-14 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260515_192117.bak` | 12MB | 2026-05-14 |
| `C:\APPS\CogniBase\Product\ONBASE\schema.20260509_pre_obdb24.1.bak` | 12MB | 2026-05-09 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260502_003028.bak` | 11MB | 2026-05-02 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260502_003028.bak` | 11MB | 2026-05-02 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260512_135626.bak` | 10MB | 2026-05-12 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260514_121457.bak` | 10MB | 2026-05-14 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260515_192118.bak` | 10MB | 2026-05-15 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260512_135626.bak` | 10MB | 2026-05-12 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260514_121457.bak` | 10MB | 2026-05-14 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260515_192118.bak` | 10MB | 2026-05-15 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260502_005513.bak` | 10MB | 2026-05-02 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260502_005554.bak` | 10MB | 2026-05-02 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260502_005513.bak` | 10MB | 2026-05-02 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260502_005554.bak` | 10MB | 2026-05-02 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260502_004430.bak` | 10MB | 2026-05-02 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260502_004454.bak` | 10MB | 2026-05-02 |
| `C:\APPS\MapSnap\Product\ONBASE\schema.20260502_004501.bak` | 10MB | 2026-05-02 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260502_004430.bak` | 10MB | 2026-05-02 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260502_004454.bak` | 10MB | 2026-05-02 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE\schema.20260502_004501.bak` | 10MB | 2026-05-02 |
| `C:\APPS\MapSnap\Product\JENZABAR\schema.20260501_122659.bak` | 8MB | 2026-05-01 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\JENZABAR\schema.20260501_122659.bak` | 8MB | 2026-05-01 |
| `C:\APPS\MapSnap\Product\JENZABAR\schema.20260501_083108.bak` | 8MB | 2026-05-01 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\JENZABAR\schema.20260501_083108.bak` | 8MB | 2026-05-01 |
| `C:\APPS\MapSnap\Product\ONBASE_GOV25\schema.20260814_100724.bak` | 6MB | 2026-08-14 |
| `C:\APPS\MapSnap\Product\ONBASE13_POC\schema.20260623_225332.bak` | 2MB | 2026-06-23 |
| `C:\APPS\MapSnap\Product\ONBASE13_POC\schema.20260623_225333.bak` | 2MB | 2026-06-23 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE13_POC\schema.20260623_225332.bak` | 2MB | 2026-06-23 |
| `C:\QIH\BU Administrative Backups\MapSnap BU institutional data\ONBASE13_POC\schema.20260623_225333.bak` | 2MB | 2026-06-23 |
| `C:\APPS\QI\secrets\maia_server_bak_round2.py.bak` | 380KB | 2026-06-12 |
| `C:\APPS\SynVox\var\backups\synvox.db.20260818_181322.bak` | 380KB | 2026-08-18 |
| `C:\APPS\NEXUS\ui\app.py.pre-restructure.bak` | 236KB | 2026-05-20 |
| `C:\APPS\MapSnap\_backup\phase0_20260624\server.py.bak` | 232KB | 2026-06-24 |
| `C:\APPS\NAYA\secrets\naya_server_bak_round2.py.bak` | 73KB | 2026-05-15 |
| `C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\configs\qi_registry.json.bak` | 69KB | 2026-08-07 |
| `C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\configs\.claude.json.bak` | 59KB | 2026-08-08 |
| `C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\claude.json.bak-phase3f` | 57KB | 2026-08-09 |
| `C:\QIH\ecosystem\qi_registry.backup-20260615-000000.json` | 44KB | 2026-08-09 |
| `C:\QIH\ecosystem\qi_registry.backup-20260615-000000.json.bak-move` | 44KB | 2026-08-09 |
| `C:\QIH\ecosystem\qi_registry.backup-20260615-000000.json.bak-phase3h` | 44KB | 2026-06-15 |
| `C:\QIH\ecosystem\qi_registry.backup-20260509-003616.json` | 31KB | 2026-08-09 |
| `C:\QIH\ecosystem\qi_registry.backup-20260509-003616.json.bak-move` | 31KB | 2026-08-09 |
| `C:\QIH\ecosystem\qi_registry.backup-20260509-003616.json.bak-phase3h` | 31KB | 2026-05-09 |
| `C:\QIH\_archive\audit_2026-08-17\ecosystem_audit_20260515.md.bak-move` | 12KB | 2026-05-15 |
| `C:\QIH\data\tasks.bak-20260514-082221.json` | 9KB | 2026-08-09 |
| `C:\QIH\data\tasks.bak-20260514-082221.json.bak-move` | 9KB | 2026-04-19 |
| `C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\configs\whitelist.json.bak` | 7KB | 2026-08-08 |
| `C:\APPS\QI\secrets\webhook_updater_bak_round2.py.bak` | 7KB | 2026-04-13 |
| `C:\APPS\AutoPDF\Application\regex_library.corrupt-2026-08-07.json.bak` | 6KB | 2026-04-30 |
| `C:\APPS\QIP\Bakeoff\logs\openclaw.json.bak-20260706_092126` | 4KB | 2026-07-06 |
| `C:\APPS\QIP\Bakeoff\logs\openclaw.json.bak-20260706_090827` | 3KB | 2026-06-15 |
| `C:\APPS\QIP\Bakeoff\logs\openclaw.json.bak-20260706_091108` | 3KB | 2026-06-15 |
| `C:\APPS\MapSnap\_backup\phase0_20260624\connection.json.bak` | 643B | 2026-08-10 |
| `C:\APPS\MapSnap\_backup\key_redaction_20260810\_backup__phase0_20260624__connection.json.bak` | 621B | 2026-08-17 |
| `C:\APPS\MapSnap\_backup\phase0_20260624\ONBASE13_POC_mapsnap_meta.json.bak` | 535B | 2026-06-24 |
| `C:\QIH\shared\documentation\migration_2026-08\phase2\rollback\configs\pyvenv.cfg.bak` | 198B | 2026-05-08 |

## Section 3 — `qi_registry.json` backups

In `C:\QIH\ecosystem\`. These are registry **history** — archive, never delete.

| # | File | Size | Date |
|---|---|---|---|
| 1 | `qi_registry.backup-20260509-003616.json` | 31KB | 2026-08-09 |
| 2 | `qi_registry.backup-20260509-003616.json.bak-move` | 31KB | 2026-08-09 |
| 3 | `qi_registry.backup-20260509-003616.json.bak-phase3h` | 31KB | 2026-05-09 |
| 4 | `qi_registry.backup-20260615-000000.json` | 44KB | 2026-08-09 |
| 5 | `qi_registry.backup-20260615-000000.json.bak-move` | 44KB | 2026-08-09 |
| 6 | `qi_registry.backup-20260615-000000.json.bak-phase3h` | 44KB | 2026-06-15 |
| 7 | `qi_registry.json.bak` | 97KB | 2026-08-23 |
| 8 | `qi_registry.json.bak-20260813_170600` | 84KB | 2026-08-11 |
| 9 | `qi_registry.json.bak-20260814-brainfix` | 84KB | 2026-08-14 |
| 10 | `qi_registry.json.bak-bom-20260827` | 99KB | 2026-08-27 |
| 11 | `qi_registry.json.bak-comfyui-2026-08-10` | 72KB | 2026-08-10 |
| 12 | `qi_registry.json.bak-filmforge-2026-08-10` | 81KB | 2026-08-10 |
| 13 | `qi_registry.json.bak-mediastudio-2026-08-10` | 78KB | 2026-08-10 |
| 14 | `qi_registry.json.bak-move` | 69KB | 2026-08-09 |
| 15 | `qi_registry.json.bak-mythologies` | 97KB | 2026-08-21 |
| 16 | `qi_registry.json.bak-noosorbis` | 96KB | 2026-08-21 |
| 17 | `qi_registry.json.bak-phase3` | 69KB | 2026-08-09 |
| 18 | `qi_registry.json.bak-phase3h` | 69KB | 2026-08-09 |
| 19 | `qi_registry.json.bak-port8740` | 85KB | 2026-08-10 |
| 20 | `qi_registry.json.bak-promoted` | 97KB | 2026-08-21 |
| 21 | `qi_registry.json.bak-rename-20260827` | 99KB | 2026-08-23 |
| 22 | `qi_registry.json.bak-synvox-20260816` | 87KB | 2026-08-14 |
| 23 | `qi_registry.json.bak-synvox-ports-20260817` | 84KB | 2026-08-16 |
| 24 | `qi_registry.json.bak-voicestudio-2026-08-10` | 69KB | 2026-08-09 |
| 25 | `qi_registry.json.bak_20260506_182000` | 28KB | 2026-05-01 |
| 26 | `qi_registry.json.bak_20260506_212901` | 29KB | 2026-05-06 |
| 27 | `qi_registry.json.bak_20260506_223156` | 31KB | 2026-05-06 |
| 28 | `qi_registry.json.bak_20260507_081854` | 31KB | 2026-05-06 |
| 29 | `qi_registry.json.bak_20260507_082033` | 31KB | 2026-05-07 |
| 30 | `qi_registry.json.bak_20260806_voiceapi` | 67KB | 2026-08-06 |
| 31 | `qi_registry.json.bak_20260807` | 67KB | 2026-08-06 |
| 32 | `qi_registry.json.bak_gamez_2026-06-19` | 47KB | 2026-06-19 |

**Action:** MOVE all to `C:\QIH\_archive\registry_history\`. Keep `qi_registry.json` in place.

## Approval

- [ ] Section 1 — worktrees (strike any line to keep it)
- [ ] Section 2 — `.bak-*` files
- [ ] Section 3 — registry backups

On approval: everything MOVES to the dated archive. Nothing is deleted. Restore is a single `robocopy` back.