# Video 1 Storyboard — "Your Bot Never Misses a Message"
### Kroger-style animated explainer · Gate 1 (after M1) · drafted 2026-07-30

**Source of truth:** AWS_Free_Tier_Setup_Guide.md Parts 0–3 (all steps proven live 2026-07-30).
**Pipeline:** extended `C:\APPS\CLAUDE\Tools\build_bu_videos.py` — edge-tts narration (Andrew/Ava) + Pillow flat-2D character frames + FFmpeg. ~4–5 min.
**Characters:** "Renne" (builder, at a desk with a PC tower) · "Maia" (friendly bot avatar) · "Postie" (LINE mail-carrier character) · a cloud with a door (Lambda) and a mailbox (SQS).

| # | Scene | Visual | Narration beat |
|---|---|---|---|
| 1 | The problem | Postie knocks at the PC's door; PC is rebooting (zzz); letter falls in a puddle | When your bot lives on one machine, every reboot loses messages |
| 2 | The idea | A little cloud house appears above; door + mailbox | Give the bot a front door in the cloud — one that never sleeps |
| 3 | Free, really | Price tags flip to $0; calendar shows "forever" on Lambda/SQS | The always-free tier: not a trial — sized for personal bots forever |
| 4 | Locking the doors first | Root key goes into a safe (MFA); a smaller "work badge" (IAM user) is printed | Never work as root; least privilege from day one |
| 5 | The doorman | Cloud door checks Postie's ID stamp (signature HMAC); fake postman bounced (403) | A public URL is safe when every knock is cryptographically checked |
| 6 | The mailbox | Letters stack in order per sender; duplicate letter merges | FIFO queue: ordered, deduplicated, holds 4 days |
| 7 | Gotcha interlude ⚠ | Door shows TWO locks; old tutorial shows one | Since Oct 2025 a public Lambda URL needs two permission grants — most guides miss it |
| 8 | Home pickup | PC wakes, walks to mailbox, collects letters, hands to Maia | The drainer: your machine collects mail whenever it's ready |
| 9 | Reply economics | Fresh letter → free "reply" stamp; old letter → limited "push" stamp | Fresh events use free reply tokens; pushes only for backlog — quota math matters |
| 10 | The switch | Signpost rotates from "tunnel" to "cloud door"; instant rotate-back shown | Cutover in one line, rollback in one line |
| 11 | Proof | Phone buzzes: Maia's real reply bubble appears | Verified live: LINE's own test + a real message through the cloud |
| 12 | Outro | Zoom out: cloud door + mailbox + happy PC; "$0/month" badge; series teaser | Next: putting the collector in a container |

**Production notes:** reuse guide's gotchas as the ⚠ interludes (that's the differentiating content); keep AWS console shots OUT (characters + diagrams only — timeless); captions burned in; QI branding end-card with link to the universal kit (after M8).
