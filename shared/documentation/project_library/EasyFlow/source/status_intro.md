# EasyFlow — Your Inbox, Sorted Into Tiers

## What is EasyFlow?

EasyFlow is an **email-organization tool** by **Quiddity Innovations** that turns a chaotic Gmail
inbox into a calm, tiered filing system. It sorts every email into a six-tier hierarchy — from
**1 - ME** (health, security, the things that matter most) all the way down to **6 - Low Priority**
(promotions, social, receipts) — so the important mail rises to the top and the noise quietly
files itself away.

EasyFlow ships in two complementary forms, both driven by the **same tier configuration**:

- A **Chrome / Edge browser extension** (Manifest V3, v1.2.1) that lives in a Gmail side panel —
  one-click classification, AI triage, label management, and subscription cleanup, all in the browser.
- A set of **Google-API automations** — a local **Flask dashboard** (port 8550) that designs the
  tier tree and *generates* a **Google Apps Script** classifier and **Gmail server-side filters**,
  so mail keeps sorting itself even when the browser is closed.

It was built first as a free gift for family and friends, and is on the path to the Chrome Web Store
and Microsoft Edge Add-ons.

## The Problem We Solve

- Gmail's labels are powerful but tedious: building a hierarchy, writing filters, and cleaning up
  old labels means clicking through many settings screens by hand.
- A flat inbox treats a security alert and a 40%-off coupon the same — there is no built-in notion
  of *priority tiers*.
- Rule-based filters miss the grey-area emails. Modern AI can read sender, subject, and snippet and
  classify confidently — but Gmail has no native place to plug an AI classifier in.
- Unsubscribing from junk and retiring stale labels is manual, repetitive, and easy to put off.

## Our Approach

EasyFlow is **config-first**. One JSON tier configuration (`Tools/config.json`) is the single source
of truth: it defines the tiers, their colors, the sub-labels, and the sender/subject rules. From that
one file EasyFlow can:

1. **Create** the matching colored Gmail label tree (Gmail API).
2. **Generate** server-side Gmail filters that auto-label and skip the inbox.
3. **Generate and deploy** a Google Apps Script that classifies new mail every 15 minutes and triages
   stale mail nightly — running entirely on Google's servers, no PC required.
4. **Drive** the browser extension's side panel, where a rules engine plus an optional AI classifier
   (Gemini / OpenAI / Anthropic / local Ollama, bring-your-own-key) sort mail on demand.

Everything is local and private — keys live in the browser's storage or local token files; email
bodies are never shipped to a server EasyFlow controls.

## Who Uses EasyFlow?

| Role | How they interact |
|---|---|
| **Owner / end user** | Gmail side panel in Chrome / Edge — classify, triage, manage labels, clean subscriptions |
| **Power user** | Local Flask dashboard (`http://localhost:8550`) to design tiers, generate filters + Apps Script |
| **Gmail (server-side)** | Generated Apps Script + filters keep sorting mail 24/7 with no app open |
| **AI providers (BYOK)** | Gemini, OpenAI, Anthropic, or local Ollama classify grey-area emails on request |
| **Family & friends** | The original audience — a free, no-cost tool to tame their inboxes |

## Current Build Status (June 2026)

EasyFlow is in **active development**. The browser extension is at **v1.2.1**; the Apps-Script and
filter automations are live; the tier engine is shipped. Outlook support is the next major arc.

| Area | Status |
|---|---|
| Six-tier classification model (1-ME … 6-Low Priority) | ✅ Live |
| Config-driven tier engine (`Tools/config.json`) | ✅ Live |
| Browser extension — Chrome (Manifest V3, v1.2.1) | ✅ Live |
| Browser extension — Microsoft Edge (web-flow OAuth) | ✅ Live |
| Gmail side panel (classify / triage / manage labels) | ✅ Live |
| Google Apps Script classifier (15-min + nightly triage) | ✅ Live |
| Gmail server-side filter generation | ✅ Live |
| Colored Gmail label-tree creation | ✅ Live |
| Local Flask dashboard (designer + deploy, port 8550) | ✅ Live |
| Cross-browser OAuth (getAuthToken + launchWebAuthFlow) | ✅ Live |
| AI triage (Gemini / OpenAI / Anthropic / Ollama, BYOK) | ✅ Live |
| Label migration & cleanup (retire / delete / re-home) | ✅ Live |
| Subscription / unsubscribe manager | ✅ Live |
| 10-language UI (EN · ZH · FR · DE · JA · KO · PT-BR · ES · HI · RU) | ✅ Live |
| Diagnostic logger (service worker + dashboard export) | ✅ Live |
| Apps Script auto-deploy via Apps Script API | ⚠️ Built — needs script ID + token |
| Chrome Web Store / Edge Add-ons listing | ⚠️ In review — CASA verification pending |
| Outlook / Microsoft Graph adaptation | 🗓️ Planned — v1.x dual-provider |
| Paid tiers (Free / Pro / Premium) + licensing backend | 🗓️ Planned — v1.3+ (scope LOCKED) |
| QI Brain integration | 🗓️ Planned |

## The Tier Model

EasyFlow's heart is a small, opinionated taxonomy. Every email lands in exactly one of six tiers,
each with its own color so the inbox reads at a glance:

| Tier | Color | What lives here |
|---|---|---|
| **1 - ME** | Red | Health & medical, security alerts, wellbeing, vision |
| **2 - Inner Circle** | Orange | Family, close friends |
| **3 - Life Admin** | Yellow | Bills, finance, taxes, appointments, insurance |
| **4 - Active Projects** | Blue | QI, education, career, AI tools |
| **5 - Interests** | Purple | Newsletters, travel, tech & AI news, hobbies |
| **6 - Low Priority** | Gray | Shopping & receipts, Amazon, promotions, social |

Anything the rules can't place gets a **Triage** label and is surfaced for the AI classifier or a
quick manual decision — nothing is silently lost.

## The Vision

One tier configuration, sorted everywhere. Today EasyFlow perfects Gmail across Chrome and Edge;
next it adapts the same provider-abstracted engine to **Outlook via Microsoft Graph**, then graduates
from a free family gift into a polished, store-listed product with optional paid tiers — while the
free core stays free.

---
*This page is editable at `C:\EasyFlow\INTRO\status_intro.md` — save and click Refresh to update.*
