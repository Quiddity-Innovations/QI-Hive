# QI Ecosystem — Component & Technology Inventory

**Generated:** 2026-08-02 · **Owner:** Renne Santiago / Quiddity Innovations · **Maintainer:** Claude Manager

This is the master inventory of every technology used across all QI projects, apps and products — what we **created** (proprietary QI code), what we **borrowed** (open-source components, with author, license, version in use, latest available version and repository link), what is **vendored** (copied in), and what was **discussed but not adopted**.

Data sources: per-app `status_techstack.json` files in the project library (built 2026-06-24), a fresh scan of projects added since then (PlayDeck, Bakeoff, QI Connector, Headroom, video pipeline, MCP Gateway), and live PyPI / npm / GitHub version checks performed 2026-08-02.

---

## 1. Project index

| Project / App | Where | Stack summary (top components) |
|---|---|---|
| AkiyaScout | C:\APPS\AkiyaScout | Python, FastAPI, Uvicorn, Pydantic, Gradio, selectolax |
| AutoPDF | C:\APPS\AutoPDF | Windows PowerShell, AutoPDF-Server.ps1, Vanilla JavaScript, HTML5 + CSS3, C#, Ghostscript |
| AvatarStudio | C:\AvatarStudio | Python, Gradio, Kokoro, edge-tts, soundfile + NumPy + SciPy, LivePortrait |
| Claude Manager | C:\APPS\CLAUDE | Claude Code, Opus / Sonnet / Haiku, Python, PowerShell, Windows Batch, Markdown front-matter agents |
| Claude Voice | C:\APPS\CLAUDE\Claude Voice | Python, FastAPI, Uvicorn, Pydantic, faster-whisper, edge-tts |
| CogniBase | C:\APPS\CogniBase | Python, FastAPI, Uvicorn, Pydantic, python-multipart, ChromaDB |
| CypherMiner | C:\APPS\CypherMiner | TypeScript, Vite, vite-plugin-pwa, Vanilla DOM, CSS variables, Web Crypto API |
| Digitization Cost Tool | (BU consulting tool) | Single-file HTML5, Vanilla JavaScript, Hand-written CSS, Web Storage, Browser print-to-PDF, Python 3 + python-docx |
| EasyFlow | C:\APPS\EasyFlow | Chrome / Edge Extension, JavaScript, Chrome Extension APIs, Google Apps Script, Python + Flask, Jinja2 + HTML/CSS/JS |
| FileHQ | C:\FileHQ | Python, FastAPI, Uvicorn, Jinja2 + StaticFiles, python-multipart, SQLite |
| Gamez | C:\APPS\Gamez | Single-file HTML/CSS/JS, Python, FastAPI, Uvicorn, httpx, APScheduler |
| LotteryWiz | C:\LotteryWiz | Python, FastAPI, Uvicorn, Python stdlib, NumPy, httpx |
| M2V | C:\APPS\M2V | Python, FastAPI, Uvicorn, python-multipart, Pydantic, Gradio |
| MQ | C:\APPS\MQ | Python, FastAPI, Uvicorn, Pydantic, Gradio, feedparser |
| MapSnap | C:\APPS\MapSnap | Python, Python stdlib http.server, Single-page HTML / CSS / vanilla JS, SQLite, JSON sidecar files, pyodbc |
| NEXUS | C:\APPS\NEXUS | Python, FastAPI, Uvicorn, Pydantic, Gradio, asyncio |
| Naya | C:\APPS\NAYA | Python, Flask, Anthropic SDK, requests, FastAPI + Uvicorn, Gradio |
| OpenClaw | C:\APPS\OC (WSL) | OpenClaw, WSL — Ubuntu, systemd, Python 3.11 / 3.12, Bash, Node.js |
| PersonalSong Studio | C:\APPS\PersonalSong | Python, FastAPI, Uvicorn, Pydantic, python-multipart + aiofiles, ACE-Step |
| QI Brain | C:\QIH\engine\brain | Python, FastAPI, Uvicorn, Pydantic, JSON-RPC 2.0 over stdio, SQLite |
| QI Hive | C:\QIH | Python, FastAPI, Uvicorn, Pydantic, AdminLTE, Bootstrap |
| TubeScout | C:\APPS\TUBESCOUT | Python, FastAPI, Uvicorn, Pydantic, Gradio, Server-rendered HTML + CSS + vanilla JS |
| PlayDeck *(new since 6/24)* | C:\PlayDeck, :8506 | FastAPI, Uvicorn[standard], httpx, yt-dlp, curl_cffi, python-dotenv |
| Bakeoff *(new since 6/24)* | C:\APPS\QIP\Bakeoff | Hermes Agent, OpenClaw, Ollama, PyYAML, RDAP via stdlib urllib, WSL2 |
| QI Connector *(new since 6/24)* | C:\APPS\QIP\Connector, :9030 | MCP SDK / FastMCP, FastAPI, Uvicorn[standard], httpx, Pydantic, python-docx |
| Claude Manager Tools — video pipeline *(new since 6/24)* | C:\APPS\CLAUDE\Tools | edge-tts, Pillow, FFmpeg, python-docx, AWS CLI, winget + Task Scheduler |
| Headroom *(new since 6/24)* | C:\APPS\CLAUDE\Tools, :9020 | headroom-ai[all], litellm, anthropic SDK, torch/transformers/huggingface-hub/datasets, opentelemetry api/sdk/otlp, NSSM |
| QI MCP Gateway *(new since 6/24)* | C:\QIH\engine\common\qi_mcp_gateway.py | MCP SDK / FastMCP + transport_security, httpx |

---

## 2. Borrowed components — open-source registry

Everything below is third-party. **In use** = version pinned/observed in our projects; **Latest** = current upstream release as of the generation date. ⬆️ = a newer upstream version exists · ✅ = we are current · blank = not comparable (unpinned/stdlib/service).

### Languages & Runtimes

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Python (CPython)** | — | Apache 2.0; Apache 2.0 / Apache 2.0; BSD | 0.0.20; 3.10+; 3.11 | — | | — | 21 apps: AkiyaScout, AvatarStudio, Claude Manager, Claude Voice, CogniBase… |
| **JavaScript (ES Modules / vanilla)** | — | Built-in (ES2020); N/A (project source); Open standard | ES2022+; asset token v=20260624a; generated | — | | — | 7 apps: AutoPDF, CypherMiner, Digitization Cost Tool, EasyFlow, LotteryWiz… |
| **Windows Batch (.bat)** | — | Microsoft (OS); N/A; Windows | Windows 11; cmd.exe; n/a | — | | — | AkiyaScout, Claude Manager, Digitization Cost Tool, QI Hive |
| **PowerShell** | — | BSD; MIT (PowerShell Core) / Windows; MIT (PowerShell) / proprietary (Windows PowerShell 5.1) | 5.1 target, 7+ compatible; Windows PowerShell 5.1+; see r… | — | | — | AutoPDF, Claude Manager, Claude Voice |
| **Bash / Shell** | — | GPL | 5.x | — | | — | OpenClaw |
| **Google Apps Script (V8)** | — | Free (Google quotas apply) | V8 runtime | — | | — | EasyFlow |
| **Node.js** | — | MIT-style | system node | — | | — | OpenClaw |
| **OpenJDK / Java JRE** | — | GPL-2.0-with-classpath-exception | bundled | — | | — | AutoPDF |
| **TypeScript** | Microsoft | Apache-2.0 | ^5.6.3 | 7.0.2 | ⬆️ newer available | [repo](https://github.com/microsoft/TypeScript) | CypherMiner |
| ↳ *note* | *major jump from pinned ^5.6.3 — TS7 native compiler; check migration notes* | | | | | | |

### Web & API Frameworks / Servers

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **FastAPI** | Sebastián Ramírez (tiangolo) | MIT | 0.115+; 0.115.6; >=0.104 | 0.141.1 | ⬆️ newer available | [repo](https://github.com/fastapi/fastapi) | 15 apps: AkiyaScout, Claude Voice, CogniBase, CypherMiner, FileHQ… |
| ↳ *note* | *repo moved from tiangolo/fastapi to fastapi/fastapi org* | | | | | | |
| **Uvicorn** | Encode (Tom Christie et al.) | BSD-3-Clause | 0.30+; 0.34.0 [standard]; >=0.24 [standard] | 0.52.1 | ⬆️ newer available | [repo](https://github.com/encode/uvicorn) | 14 apps: AkiyaScout, Claude Voice, CogniBase, CypherMiner, FileHQ… |
| **Gradio** | Gradio / Hugging Face | Apache-2.0 | 6.14.0; >=5.0 | 6.22.0 | ⬆️ newer available | [repo](https://github.com/gradio-app/gradio) | 7 apps: AkiyaScout, AvatarStudio, M2V, MQ, NEXUS… |
| ↳ *note* | *ahead of pinned 6.14.0* | | | | | | |
| **Jinja2 templating** | Pallets Projects | BSD-3-Clause | 3.1.5; Flask templating | 3.1.6 | ⬆️ newer available | [repo](https://github.com/pallets/jinja) | EasyFlow, FileHQ |
| **Caddy** | Matt Holt / Caddy team | Apache-2.0 | engine/bin/caddy.exe | v2.11.4 |  | [repo](https://github.com/caddyserver/caddy) | QI Hive |
| **Flask** | Pallets Projects | BSD-3-Clause | 3.x | 3.1.3 |  | [repo](https://github.com/pallets/flask) | Naya |

### Frontend, UI & Styling

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Single-file / single-page HTML-CSS-JS** | — | N/A (project source); Proprietary (QI); Proprietary (Quiddity Innovations) | 1 file; embedded <style>; n/a | — | | — | AutoPDF, CypherMiner, Digitization Cost Tool, Gamez |
| **Browser storage (localStorage / Web Storage)** | — | Browser built-in; Web standard | with in-memory fallback; — | — | | — | CypherMiner, Digitization Cost Tool |
| **AdminLTE** | ColorlibHQ (Colorlib) | MIT | 4.x | v4.1.0 |  | [repo](https://github.com/ColorlibHQ/AdminLTE) | QI Hive |
| **Bootstrap** | Bootstrap core team (Mark Otto, Jacob Thornton et al.) | MIT | 1.13.1; 5.x | v5.3.8 | ⬆️ newer available | [repo](https://github.com/twbs/bootstrap) | QI Hive |
| **folium / Leaflet** | python-visualization team | MIT | >=0.20 | 0.20.0 | ✅ current | [repo](https://github.com/python-visualization/folium) | AkiyaScout |
| ↳ *note* | *matches pinned floor* | | | | | | |
| **pywebview** | Roman Sirokov (r0x0r) | BSD-3-Clause | launcher_gui.py | 6.2.1 |  | [repo](https://github.com/r0x0r/pywebview) | Gamez |
| **SortableJS** | SortableJS org (RubaXa / community maintainers) | MIT | 1.15.0 | 1.15.7 | ⬆️ newer available | [repo](https://github.com/SortableJS/Sortable) | QI Hive |
| ↳ *note* | *ahead of pinned 1.15.0* | | | | | | |
| **Vite** | Evan You / VoidZero, Vite team | MIT | ^0.21.1; ^6.0.7 | 8.2.0 | ⬆️ newer available | [repo](https://github.com/vitejs/vite) | CypherMiner |
| ↳ *note* | *major jump from pinned ^6.0.7 — breaking changes likely* | | | | | | |

### Data Validation, HTTP Clients & Concurrency

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Pydantic** | Samuel Colvin / Pydantic Services team | MIT | (FastAPI dep); 2.x; >=2.6 | 2.13.4 | ⬆️ newer available | [repo](https://github.com/pydantic/pydantic) | 11 apps: AkiyaScout, Claude Voice, CogniBase, CypherMiner, M2V… |
| **httpx** | Encode | BSD-3-Clause | >=0.25; >=0.27; current | 0.28.1 | ⬆️ newer available | [repo](https://github.com/encode/httpx) | 10 apps: AkiyaScout, CogniBase, CypherMiner, Gamez, LotteryWiz… |
| **requests** | Python Software Foundation (originally Kenneth Reitz) | Apache-2.0 | 2.34.2; >=2.31; >=2.32 | 2.34.2 | ✅ current | [repo](https://github.com/psf/requests) | 7 apps: AvatarStudio, Claude Voice, FileHQ, M2V, MQ… |
| **asyncio** | — | MIT; PSF (stdlib) | >=8; stdlib | — | | — | CogniBase, NEXUS, QI Brain |
| **aiofiles** | Tin Tvrtković | Apache-2.0 | 24.1.0; >=23.2 | 25.1.0 | ⬆️ newer available | [repo](https://github.com/Tinche/aiofiles) | FileHQ, NEXUS |
| **urllib (stdlib)** | — | PSF (stdlib) | stdlib | — | | — | LotteryWiz, MQ |
| **humanize / rich** | Will McGugan / Textualize | MIT | 4.11.0 / 13.9.4 | 15.0.0 | ⬆️ newer available | [repo](https://github.com/Textualize/rich) | FileHQ |
| ↳ *note* | *major bump from pinned 13.9.4* | | | | | | |
| **threading** | — | PSF (stdlib) | stdlib | — | | — | QI Brain |

### Databases, Vector Stores & On-Disk State

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **JSON files as state store** | — | Internal (QI); MIT; MIT (spec) | -; 6.0.2; C:\QIH\ecosystem\ | — | | — | 12 apps: AutoPDF, Claude Manager, Claude Voice, CogniBase, FileHQ… |
| **SQLite** | — | Public domain; Public domain / Apache 2.0 | 3.x; 3.x (WAL mode); 3.x (WAL mode, FK on) | — | | — | 12 apps: AkiyaScout, Claude Manager, CogniBase, FileHQ, LotteryWiz… |
| **ChromaDB** | Chroma (Jeff Huber, Anton Troynikov) | Apache-2.0 | 0.5.x (PersistentClient); >=0.5; local | 1.5.9 | ⬆️ newer available | [repo](https://github.com/chroma-core/chroma) | CogniBase, MapSnap, NEXUS, QI Brain, QI Hive |
| ↳ *note* | *major jump from pinned 0.5.x — breaking changes likely* | | | | | | |
| **Excel COM as data mirror** | — | Commercial (Microsoft) | Office 2013+ | — | | — | AutoPDF |
| **oracledb (Oracle driver)** | Oracle Corporation | Apache-2.0 / UPL (dual) | via /api/install-driver | 4.0.2 |  | [repo](https://github.com/oracle/python-oracledb) | MapSnap |
| ↳ *note* | *PyPI name 'oracledb'* | | | | | | |
| **psycopg2 (PostgreSQL driver)** | Federico Di Gregorio / psycopg team | LGPL-3.0 (linking exception) | via /api/install-driver | 2.9.12 |  | [repo](https://github.com/psycopg/psycopg2) | MapSnap |
| **PyMySQL (MySQL driver)** | PyMySQL team | MIT | via /api/install-driver | 1.2.0 |  | [repo](https://github.com/PyMySQL/PyMySQL) | MapSnap |
| **pyodbc (SQL Server driver)** | Michael Kleehammer | MIT | via /api/install-driver | 5.3.0 |  | [repo](https://github.com/mkleehammer/pyodbc) | MapSnap |
| **Qdrant** | Qdrant team | Apache-2.0 | optional | v1.18.3 |  | [repo](https://github.com/qdrant/qdrant) | MapSnap |

### AI — Local Inference (LLMs, Embeddings, Speech, Vision, Media)

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Ollama** | Ollama (org) | MIT | /api/tags, /api/chat; API :11434; HTTP (no SDK) | v0.32.5 | ✅ current | [repo](https://github.com/ollama/ollama) | 15 apps: AkiyaScout, AutoPDF, Claude Voice, CogniBase, EasyFlow… |
| ↳ *note* | *released 2026-07-27; local server, not a pip package* | | | | | | |
| **faster-whisper / Whisper (STT)** | SYSTRAN (Guillaume Klein) | MIT | >=20231117; base model; model base.en (PC) / base (multil… | 1.2.1 |  | [repo](https://github.com/SYSTRAN/faster-whisper) | Claude Voice, M2V, OpenClaw, PersonalSong Studio, TubeScout |
| **edge-tts (Microsoft neural voices)** | rany2 | LGPL-3.0 (srt_composer.py MIT) | 7.2.8; Communicate API; dots.tts 2B | 7.2.8 | ✅ current | [repo](https://github.com/rany2/edge-tts) | AvatarStudio, Claude Voice, OpenClaw, PersonalSong Studio |
| ↳ *note* | *matches version we run* | | | | | | |
| **Local open-weight LLMs (Qwen/Gemma/DeepSeek/etc.)** | — | Derived from base model (e.g. Qwen2.5); Free tier / local; Mixed open weights / MIT runtime | autopdf-mapper:latest; see NEXUS providers.json; via Ollama | — | | — | AutoPDF, Naya, TubeScout |
| **PyTorch (CUDA)** | PyTorch Foundation / Meta | BSD-3-Clause | 2.11.0+cu128; >=2.0 (torch 2.11 / cu128 build); torch 2.1… | 2.13.0 | ⬆️ newer available | [repo](https://github.com/pytorch/pytorch) | AvatarStudio, M2V, PersonalSong Studio |
| ↳ *note* | *we run 2.11.0+cu128* | | | | | | |
| **Kokoro-82M (offline TTS)** | hexgrad | Apache-2.0 | 0.9.4; planned | unverified |  | [repo](https://huggingface.co/hexgrad/Kokoro-82M) | AvatarStudio, Claude Voice |
| ↳ *note* | *HF model repo, no release tags; last modified 2025-04-10* | | | | | | |
| **librosa / audio analysis** | librosa development team (Brian McFee et al.) | ISC | >=0.10; soundfile (libsndfile) · pydub · scipy>=1.11 · nu… | 0.11.0 | ✅ current | [repo](https://github.com/librosa/librosa) | M2V, PersonalSong Studio |
| **Stable Diffusion XL / SVD (diffusers)** | Hugging Face | Apache-2.0 | diffusers>=0.32 / transformers>=4.44 / accelerate>=0.33; … | 0.39.0 | ✅ current | [repo](https://github.com/huggingface/diffusers) | M2V, PersonalSong Studio |
| **ACE-Step (singing model)** | ACE Studio / StepFun | Apache-2.0 | 0.2.0 (per song metadata) | unverified |  | [repo](https://github.com/ace-step/ACE-Step) | PersonalSong Studio |
| ↳ *note* | *no GitHub releases; we run 0.2.0 locally* | | | | | | |
| **ComfyUI** | Comfy-Org (formerly comfyanonymous) | GPL-3.0 | core nodes | v0.29.2 |  | [repo](https://github.com/Comfy-Org/ComfyUI) | M2V |
| ↳ *note* | *old comfyanonymous URL redirects here* | | | | | | |
| **Demucs (stem separation)** | Alexandre Défossez (orig. Meta/FAIR, facebookresearch repo archived) | MIT | htdemucs, two-stems mode | 4.1.0 |  | [repo](https://github.com/adefossez/demucs) | PersonalSong Studio |
| ↳ *note* | *adefossez fork is the maintained one; PyPI points to it* | | | | | | |
| **IP-Adapter (character consistency)** | Tencent AI Lab | Apache-2.0 | ip-adapter_sdxl | unverified |  | [repo](https://github.com/tencent-ailab/IP-Adapter) | M2V |
| ↳ *note* | *weights at huggingface.co/h94/IP-Adapter; no releases* | | | | | | |
| **NotebookLM (vision-driven)** | — | Commercial (free) | — | — | | — | OpenClaw |
| **OpenCV (computer vision)** | OpenCV.org / opencv-python maintainers | Apache-2.0 | opencv-python (cv2) | 5.0.0.93 |  | [repo](https://github.com/opencv/opencv-python) | AvatarStudio |
| **rembg (background removal)** | Daniel Gatis | MIT | rembg 2.0.75 / pillow 12.2.0 | 2.0.77 | ⬆️ newer available | [repo](https://github.com/danielgatis/rembg) | AvatarStudio |
| ↳ *note* | *we run 2.0.75* | | | | | | |
| **Seed-VC (voice conversion)** | Plachtaa | GPL-3.0 | f0-conditioned (sing) / non-f0 (speech) | unverified |  | [repo](https://github.com/Plachtaa/seed-vc) | PersonalSong Studio |
| ↳ *note* | *no releases; latest commit 2025-04-20* | | | | | | |
| **Talking-head render engines (Hallo2/LivePortrait/SadTalker/etc.)** | — | Apache 2.0 (research); MIT (research); Mixed (research) | WSL2 conda env 'hallo'; WSL2 conda env 'liveportrait'; WS… | — | | — | AvatarStudio |
| **VAD & wake-word (silero/webrtc/openWakeWord)** | Silero Team | MIT | see requirements.txt | 6.2.1 |  | [repo](https://github.com/snakers4/silero-vad) | Claude Voice |

### AI — Cloud & Hosted Models

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Anthropic Claude (API / SDK)** | Anthropic | MIT | OpenAI-compatible / vendor APIs; Opus 4.x / Sonnet 4.x / … | 0.120.2 | ⬆️ newer available | [repo](https://github.com/anthropics/anthropic-sdk-python) | 9 apps: Claude Manager, Claude Voice, CogniBase, EasyFlow, Gamez… |
| **OpenAI / ChatGPT (API)** | OpenAI | Apache-2.0 | gpt-4o-mini; gpt-5.4; openai>=1.50 / google-generativeai>… | 2.52.0 | ✅ current | [repo](https://github.com/openai/openai-python) | CogniBase, EasyFlow, NEXUS, OpenClaw |
| **Cloudflare Workers AI** | — | Commercial (free tier); Free tier | llama-3.3-70b-fp8; qwen2.5-7b-instruct-fast; — | — | | — | MQ, NEXUS, OpenClaw |
| **OpenRouter (model gateway)** | — | Commercial API; Free tier; Mixed (mostly paid) | /api/v1; see llm_chain; see providers.json | — | | — | MapSnap, NEXUS, Naya |
| **D-ID / HeyGen (avatar SaaS)** | — | Commercial SaaS | D-ID v1, HeyGen v2 | — | | — | AvatarStudio |
| **DeepEval (LLM evaluation)** | Confident AI (Jeffrey Ip) | Apache-2.0 | optional dep | 4.1.5 |  | [repo](https://github.com/confident-ai/deepeval) | NEXUS |
| **DeepL (translation)** | — | Paid / free-tier API | v2 | — | | — | AkiyaScout |
| **Google Gemini** | — | Free tier / Paid | gemini-2.0-flash | — | | — | EasyFlow |
| **Groq** | — | Free tier | llama-3.3-70b | — | | — | NEXUS |
| **Mistral** | — | Free tier | mistral-small-latest | — | | — | NEXUS |
| **tiktoken** | OpenAI (Shantanu Jain) | MIT | >=0.7 | 0.13.0 | ⬆️ newer available | [repo](https://github.com/openai/tiktoken) | CogniBase |

### Document, PDF, Office & Media Processing

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **FFmpeg** | FFmpeg community project | LGPL-2.1+/GPL-2.0+ (dual, build-dependent) | Pillow>=10 / imageio>=2.34; WSL2 system ffmpeg + imageio-… | 8.1.2 ('Hoare') | ⬆️ newer available | [repo](https://github.com/FFmpeg/FFmpeg) | AvatarStudio, Claude Voice, M2V, PersonalSong Studio |
| ↳ *note* | *canonical repo git.ffmpeg.org; GitHub is a mirror* | | | | | | |
| **lxml / selectolax / BeautifulSoup (HTML/XML parsing)** | lxml dev team (Stefan Behnel et al.) | BSD-3-Clause | >=0.3.21; >=5.1; current | 6.1.1 | ⬆️ newer available | [repo](https://github.com/lxml/lxml) | AkiyaScout, CogniBase, LotteryWiz |
| **openpyxl** | openpyxl team (Charlie Clark, maintainer) | MIT | >=3.1; current; installed | 3.1.5 | ⬆️ newer available | [repo](https://foss.heptapod.net/openpyxl/openpyxl) | CogniBase, LotteryWiz, MapSnap |
| ↳ *note* | *canonical repo is Heptapod (Mercurial), not GitHub* | | | | | | |
| **PDF text extraction (PyMuPDF/Poppler/PyPDF2/pdfminer)** | Artifex Software Inc. | AGPL-3.0 OR Artifex commercial (dual) | >=1.24; bundled; optional | 1.28.0 | ⬆️ newer available | [repo](https://github.com/pymupdf/PyMuPDF) | AutoPDF, CogniBase, MapSnap |
| **Microsoft Office COM / pywin32** | Mark Hammond et al. | PSF-2.0 | Office 2013+; optional | 312 |  | [repo](https://github.com/mhammond/pywin32) | AutoPDF, Naya |
| ↳ *note* | *build-number versioning* | | | | | | |
| **mutagen (audio tags)** | Quod Libet project (Christoph Reiter et al.) | GPL-2.0+ | >=1.47; soundfile>=0.12 / mutagen>=1.47 | 1.48.1 | ⬆️ newer available | [repo](https://github.com/quodlibet/mutagen) | M2V, PersonalSong Studio |
| **soundfile / pydub / scipy / numpy (audio I/O)** | Bastian Bechtold | BSD-3-Clause | see requirements.txt; soundfile 0.13.1 / numpy 2.4.5 / sc… | 0.14.0 | ⬆️ newer available | [repo](https://github.com/bastibe/python-soundfile) | AvatarStudio, Claude Voice |
| ↳ *note* | *newer than our 0.13.1* | | | | | | |
| **Ghostscript** | Artifex Software Inc. | AGPL-3.0 OR Artifex commercial (dual) | 10.07.0 | 10.07.1 | ⬆️ newer available | [repo](https://github.com/ArtifexSoftware/ghostpdl) | AutoPDF |
| ↳ *note* | *we run 10.07.0 — one patch behind* | | | | | | |
| **matplotlib + pandas** | John D. Hunter / matplotlib dev team | Matplotlib License (PSF/BSD-style) | >=3.8 / >=2.2 | 3.11.1 | ⬆️ newer available | [repo](https://github.com/matplotlib/matplotlib) | CogniBase |
| **MoviePy** | Zulko et al. | MIT | v2 API (with_duration/with_effects) | 2.2.1 |  | [repo](https://github.com/Zulko/moviepy) | M2V |
| **NAPS2 (scanner bridge)** | Ben Olden-Cooligan (cyanfish) | GPL-2.0 | 8.2.1 | 8.3.2 | ⬆️ newer available | [repo](https://github.com/cyanfish/naps2) | AutoPDF |
| ↳ *note* | *one minor ahead of our 8.2.1* | | | | | | |
| **NumPy / SciPy** | NumPy Developers / NumFOCUS | BSD-3-Clause | optional | 2.5.1 |  | [repo](https://github.com/numpy/numpy) | LotteryWiz |
| **PDFtk (pdftk-java)** | Angad Singh (maintainer); originally Sid Steward's pdftk | GPL-2.0+ | bundled | 3.3.3 |  | [repo](https://gitlab.com/pdftk-java/pdftk) | AutoPDF |
| ↳ *note* | *canonical is GitLab* | | | | | | |
| **Pillow (PIL)** | Jeffrey A. Clark and contributors | HPND ('Pillow License') | bundled | 12.3.0 |  | [repo](https://github.com/python-pillow/Pillow) | PersonalSong Studio |
| ↳ *note* | *newer than our 12.2.0* | | | | | | |
| **qrcode** | Lincoln Loop | BSD-3-Clause | bundled | 8.2 |  | [repo](https://github.com/lincolnloop/python-qrcode) | PersonalSong Studio |
| **RapidOCR (ONNX)** | SWHL / RapidAI team | Apache-2.0 | not started (plan 2026-06-22) | 1.4.4 |  | [repo](https://github.com/RapidAI/RapidOCR) | AutoPDF |
| ↳ *note* | *unified 'rapidocr' package now also exists* | | | | | | |
| **Tabula (tabula-java)** | Manuel Aristarán / Tabula project | MIT | bundled (optional) | 1.0.5 |  | [repo](https://github.com/tabulapdf/tabula-java) | AutoPDF |
| ↳ *note* | *last release 2021 — dormant* | | | | | | |
| **Tesseract OCR** | HP-originated; Google + community (lead Zdenko Podobny) | Apache-2.0 | bundled | 5.5.3 |  | [repo](https://github.com/tesseract-ocr/tesseract) | AutoPDF |
| **ytmusicapi** | sigma67 | MIT | >=1.10 | 1.12.1 | ⬆️ newer available | [repo](https://github.com/sigma67/ytmusicapi) | PersonalSong Studio |
| **zipfile + xml (stdlib)** | — | PSF | stdlib | — | | — | MapSnap |

### Service Management, Tunnels & Scheduling

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **NSSM (Windows service manager)** | Iain Patterson | Public Domain | 2.24 (engine/bin/nssm.exe); C:\QIH\engine\bin\nssm.exe; n… | 2.24 | ✅ current | [repo](https://nssm.cc) | 18 apps: AutoPDF, AvatarStudio, Claude Manager, Claude Voice, CogniBase… |
| ↳ *note* | *canonical source is SVN at nssm.cc, not GitHub; 2.24 (2014) still latest — project dormant* | | | | | | |
| **APScheduler** | Alex Grönholm | MIT | 3.10.4; >=3.10 | 3.11.3 | ⬆️ newer available | [repo](https://github.com/agronholm/apscheduler) | AkiyaScout, FileHQ, Gamez, NEXUS, Naya |
| **Cloudflare Tunnel (cloudflared)** | Cloudflare, Inc. | Apache-2.0 | named tunnel qi-kaze; named tunnels (migrated 2026-06-20)… | 2026.7.3 |  | [repo](https://github.com/cloudflare/cloudflared) | MapSnap, OpenClaw, QI Hive |
| **Windows Task Scheduler** | — | OS; OS built-in; OS component | Windows 11; — | — | | — | MQ, Naya, TubeScout |
| **WSL / WSL2 (Ubuntu)** | — | Open source; Ubuntu (Canonical) / WSL (MS) | Ubuntu-24.04 | — | | — | AvatarStudio, OpenClaw |
| **PyInstaller** | PyInstaller Development Team | GPL-2.0 w/ bundling exception | WC2026.spec | 6.21.0 |  | [repo](https://github.com/pyinstaller/pyinstaller) | Gamez |
| **setuptools + Docker** | — | MIT / Apache 2.0 | pyproject 0.4.0.dev0 | — | | — | CogniBase |
| **Win32 process control (CIM/Stop-Process)** | — | Windows | CIM | — | | — | Claude Manager |

### External Integrations & Data Sources

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **feedparser (RSS/Atom)** | Kurt McKee | BSD-2-Clause | >=6.0.11; — | 6.0.14 | ⬆️ newer available | [repo](https://github.com/kurtmckee/feedparser) | MQ, NEXUS, OpenClaw |
| **LINE Messaging API** | LINE Corporation | Apache-2.0 | messaging v3; v2 broadcast; — | 3.25.0 |  | [repo](https://github.com/line/line-bot-sdk-python) | Claude Manager, Claude Voice, OpenClaw |
| ↳ *note* | *messaging v3 SDK* | | | | | | |
| **Gmail API / IMAP-SMTP** | — | Commercial (free); Free (Google quotas apply) | v1; — | — | | — | EasyFlow, OpenClaw |
| **Google Workspace APIs (Apps Script / People / Drive)** | Google LLC | Apache-2.0 | >=1.2 / >=0.2; v1 | 2.198.0 | ⬆️ newer available | [repo](https://github.com/googleapis/google-api-python-client) | EasyFlow, TubeScout |
| **Chrome / Edge Extension platform (Manifest V3)** | — | Chrome extension APIs; Open standard; Open standard (Google) | 10 locales; MV3; manifest v1.2.1 | — | | — | EasyFlow |
| **Facebook / Instagram / WhatsApp (Meta APIs)** | — | Meta Platform Terms | planned; v19.0 | — | | — | MQ |
| **Lottery open-data feeds** | — | Open data / official | live | — | | — | LotteryWiz |
| **Map tiles & geocoding (OSM/Esri/GSI)** | — | ODbL (free, usage policy); Tile-provider terms (attribution required) | live tiles; public API | — | | — | AkiyaScout |
| **Plex (media server)** | — | in-repo module | local Plex Media Server :32400 | — | | — | PersonalSong Studio |
| **praw (Reddit)** | Bryce Boe / PRAW dev team | BSD-2-Clause | >=7.8 | 8.0.2 | ⬆️ newer available | [repo](https://github.com/praw-dev/praw) | NEXUS |
| **Sports & odds data APIs (ESPN/API-Football/Kalshi/EA FC)** | — | Community dataset; Free tier (paid plans); Public API (no key) | GitHub EAFC26-DataHub; site.api.espn.com v2/v3; trade-api/v2 | — | | — | Gamez |
| **Telegram Bot API** | — | Free API | Bot API | — | | — | Naya |
| **YouTube Data API & transcripts** | Jonas Depoix | MIT | >=0.6.2 | 1.2.4 | ⬆️ newer available | [repo](https://github.com/jdepoix/youtube-transcript-api) | TubeScout |
| **yt-dlp** | yt-dlp maintainers collective (fork of youtube-dl) | Unlicense (public domain) | module -m yt_dlp | 2026.7.4 |  | [repo](https://github.com/yt-dlp/yt-dlp) | PersonalSong Studio |

### Security, Auth & Cryptography

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **stdlib crypto (hmac / hashlib / secrets)** | — | PSF; PSF (stdlib) | stdlib | — | | — | MapSnap, Naya |
| **Authlib** | Hsiaoming Yang (lepture) | BSD-3-Clause | >=1.3 | 1.7.2 | ⬆️ newer available | [repo](https://github.com/authlib/authlib) | CogniBase |
| **Google OAuth2 (+ PKCE)** | — | Open standard | OAuth 2.0 | — | | — | EasyFlow |
| **Hashing for dedup (xxhash / hashlib)** | Yue Du | BSD-2-Clause | 3.5.0 | 3.8.1 | ⬆️ newer available | [repo](https://github.com/ifduyue/python-xxhash) | FileHQ |
| ↳ *note* | *newer than our 3.5.0* | | | | | | |
| **sqlglot (SQL safety)** | Toby Mao | MIT | >=25.0 | 30.14.0 | ⬆️ newer available | [repo](https://github.com/tobymao/sqlglot) | CogniBase |
| **Web Crypto API** | — | Browser built-in | — | — | | — | CypherMiner |

### Developer Tooling, Agents & Protocols

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Git / GitHub** | — | GPL; GPL / proprietary; GPLv2 | C:\Program Files\Git\cmd\git.exe; git; system git | — | | — | Claude Manager, OpenClaw, QI Brain, QI Hive |
| **Claude Code (Anthropic CLI / Agent SDK)** | — | Commercial (Anthropic); Internal (QI); Subscription (Anthropic) | Claude Code / Desktop (MSIX); engine/common/usage_stats.p… | — | | — | Claude Manager, Claude Voice, QI Hive |
| **Model Context Protocol (MCP / FastMCP)** | Jeremiah Lowin | Apache-2.0 | API on port 9011; JSON-RPC 2.0; mcp.server.fastmcp | 3.4.5 | ⬆️ newer available | [repo](https://github.com/jlowin/fastmcp) | Claude Manager, LotteryWiz, QI Hive |
| ↳ *note* | *homepage gofastmcp.com* | | | | | | |
| **rapidfuzz / difflib (fuzzy matching)** | Max Bachmann | MIT | >=3.9; stdlib | 3.14.5 | ⬆️ newer available | [repo](https://github.com/rapidfuzz/RapidFuzz) | NEXUS, Naya |
| **filesystem stdlib (os/shutil/pathlib)** | — | PSF (stdlib) | stdlib | — | | — | FileHQ |
| **langdetect** | Michal 'Mimino' Danilák | Apache-2.0 | optional | 1.0.9 |  | [repo](https://github.com/Mimino666/langdetect) | Claude Voice |
| ↳ *note* | *Python port of Google's language-detection* | | | | | | |
| **Markdown front-matter agents** | — | n/a (project files) | 8 agents | — | | — | Claude Manager |
| **Playwright / Pester (UI & API tests)** | Microsoft Corporation | Apache-2.0 | Tests/ tree | 1.62.0 |  | [repo](https://github.com/microsoft/playwright-python) | AutoPDF |
| **send2trash** | Andrew Senetar (arsenetar) | BSD-3-Clause | >=1.8 | 2.1.0 | ⬆️ newer available | [repo](https://github.com/arsenetar/send2trash) | Naya |

### QI Internal Platform Services

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **NEXUS (multi-AI synthesis)** | — | QI internal; Quiddity Innovations (internal) | 0.1.0; registry; — | — | | — | FileHQ, Naya, TubeScout |
| **Maia / Naya shared modules** | — | QI internal; Quiddity Innovations (internal) | merged 2026; shared with Maia | — | | — | FileHQ, Naya |
| **OpenClaw (agent gateway)** | — | Open source (npm package) | 2026.4.26 (be8c246) | — | | — | OpenClaw |

### Other / Project-Specific Components

| Component | Author / Maintainer | License | In use | Latest | Status | Repository | Used in |
|---|---|---|---|---|---|---|---|
| **Browser print-to-PDF** | — | Browser-native | @media print | — | | — | Digitization Cost Tool |
| **Built-in glossary stub** | — | In-house | n/a | — | | — | AkiyaScout |
| **file:// · web server · SharePoint embed** | — | N/A | no install | — | | — | Digitization Cost Tool |
| **OnBase XML Index DIP** | — | n/a (output format) | Foundation 24.1 | — | | — | AutoPDF |
| **smtplib (stdlib)** | — | PSF (stdlib) | stdlib | — | | — | AkiyaScout |

### Additional components from the post-6/24 projects

| Component | Author / Maintainer | License | Latest | Repository | Used in |
|---|---|---|---|---|---|
| **curl_cffi** | lexiforest (Yifei Kong) | MIT | 0.16.0 | [repo](https://github.com/lexiforest/curl_cffi) | PlayDeck |
| **python-dotenv** | Saurabh Kumar (theskumar) | BSD-3-Clause | 1.2.2 | [repo](https://github.com/theskumar/python-dotenv) | PlayDeck |
| **PyYAML** | YAML community (orig. Kirill Simonov) | MIT | 6.0.3 | [repo](https://github.com/yaml/pyyaml) | Bakeoff |
| **litellm** | BerriAI (Ishaan Jaffer, Krrish Dholakia) | MIT | 1.95.0 | [repo](https://github.com/BerriAI/litellm) | Headroom |
| **headroom-ai** | Headroom project | Apache-2.0 | 0.33.0 | [repo](https://headroom-docs.vercel.app) | Headroom (QI_Headroom :9020) |
| **hls.js** | video-dev community | Apache-2.0 | 1.6.16 | [repo](https://github.com/video-dev/hls.js) | PlayDeck (vendored) |

---

## 3. QI-created components (proprietary)

Original Quiddity Innovations code — no upstream, no external author.

| Component | What it is | Lives in |
|---|---|---|
| **Single-file HTML/CSS/JS front-ends** | Hand-written no-framework UIs (MapSnap schema browser, dashboards, launchers) | MapSnap, AutoPDF, Naya, many |
| **QI Hive dashboard + War Room + Library** | FastAPI ops center: mission control, dispatch, compliance, doc Library (:8600) | C:\QIH\engine\hive\dashboard |
| **QI Brain (API + ChromaDB memory)** | Ecosystem memory: decisions, sessions, features, doc index (:9011) | C:\QIH\engine\brain |
| **qi_mcp_gateway.py** | Reusable config-driven MCP front door for any QI app (ADAPTERS registry); MapSnap first adopter | C:\QIH\engine\common |
| **QI Connector** | Remote MCP server for claude.ai / Claude Code (:9030, connector.quiddityinnovations.com) | C:\APPS\QIP\Connector |
| **QI_Elevate broker** | Elevation broker for headless admin ops (replaces gsudo) | C:\QIH\engine\common |
| **qi_registry.py / qi_validator.py / qi_new_project.py** | Ecosystem registry, compliance checker, project scaffolder | C:\QIH\ecosystem |
| **Maia / Naya / NEXUS bot engines** | Multi-channel AI assistant platform, multi-LLM chains, template engine vision | C:\APPS\QI, C:\APPS\NAYA, C:\APPS\NEXUS |
| **MapSnap engine + extractors** | DB schema browser/extractor suite (SQL Server/Postgres/MySQL/Oracle/Qdrant), Data Chat, BU Edition kit | C:\APPS\MapSnap |
| **AutoPDF engine** | PowerShell HttpListener PDF/OCR pipeline | C:\APPS\AutoPDF |
| **EasyFlow extension** | Chrome/Edge MV3 extension (10 locales) | C:\APPS\EasyFlow |
| **qi_toon_video.py + BU video pipeline** | Flat-2D character animation / explainer-video generator (edge-tts + Pillow + FFmpeg) | C:\APPS\CLAUDE\Tools |
| **doc_harvester.py + hive-librarian** | Documentation Brain: doc index + knowledge graph (937+ docs) | C:\QIH\engine\brain |
| **Bakeoff eval rig** | Hermes vs OpenClaw agent-harness evaluation (same gpt-oss-20b brain) | C:\APPS\QIP\Bakeoff |
| **PlayDeck** | Own video player UI: 3-tier browse (yt-dlp/scrape/headless), offline library (:8506) | C:\PlayDeck |
| **PersonalSong Studio** | Local AI song generator orchestration (ACE-Step + Demucs + Seed-VC) | C:\APPS\PersonalSong |
| **TubeScout** | YouTube-subscription news tool (:8503) | C:\APPS\TUBESCOUT |
| **Claude Voice** | LINE/Telegram voice bridge + meeting room (:8722) | C:\APPS\CLAUDE\Claude Voice |
| **Hive agent suite** | 8 specialized sub-agents (architect/builder/inspector/ops/scout/scribe/tester/librarian) + dispatch protocol | C:\APPS\CLAUDE\.claude\agents |

---

## 4. Vendored third-party code (copied in, not package-managed)

- C:\PlayDeck\web\vendor\hls.min.js — vendored minified hls.js build (no version string)
- C:\PlayDeck\engine\bin\nssm.exe — per-project NSSM copy (QI convention)
- C:\APPS\QIP\Connector — NSSM per-project service convention (shared C:\QIH\engine\bin\nssm.exe)
- C:\APPS\CLAUDE\Tools\headroom_env\ — entire isolated Python venv vendored (torch, transformers, datasets, cv2, aiohttp, cryptography...), no manifest
- No verbatim code copying between QI sibling projects found — cross-project reuse is the shared nssm.exe binary and the intentionally shared qi_mcp_gateway.py module
- `C:\QIH\engine\hive\dashboard\static\vendor\vis-network.min.js` — vis-network graph library (Apache-2.0/MIT dual), used by the Library knowledge graph
- Per-project `engine\bin\nssm.exe` copies across QI projects (standing convention: each project ships its own NSSM 2.24)
- Bundled Java runtimes + tabula-java / pdftk-java jars inside AutoPDF (no system Java install required)

---

## 5. Components discussed but NOT adopted (or only partially adopted)

- **Buzz** (Block / Jack Dorsey's open-source AI-agent workspace) — evaluated as successor to the hand-built QI Hive War Room/dispatch UI; not migrated (too new; replatforming mid-cycle would burn August). Sandbox trial + 3–6 month re-check instead. (2026-07-27, C:\APPS\CLAUDE\Tech_Evaluation_2026-07.md)
- **Colibri** (MoE model streaming engine, 744B GLM-5.2 on consumer hardware) — evaluated for "Ronald" local Ollama fallback; watch-list only — ~9 tok/s too slow for voice latency. (2026-07-27, Tech_Evaluation_2026-07.md)
- **Nostr** (decentralized signed-message protocol) — evaluated as notification/identity layer; skipped — LINE/Telegram already cover it. (2026-07-27, Tech_Evaluation_2026-07.md)
- **OpenClaw as the Claude Voice harness** — rejected for the real-time voice/video rebuild (gateway 404/version mismatch, fragile extra hop); **LiveKit** chosen instead. (2026-06-21, ClaudeVoice summaries)
- **MiniMax 230B local** — rejected as MapSnap local LLM: 108 GB at 4-bit, needs 128 GB RAM — not viable on RTX 5080/64 GB. Cloud A/B variant also deferred. (2026-06-16/17, MapSnap summaries)
- **Tailscale / Cloudflare Tunnel / raw port exposure** for MapSnap BU Edition — rejected; IIS + VPN chosen for the ~100-user BU server (authorization stays in MapSnap's own login; no per-seat cost). (Brain decision_502, 2026-07)
- **Headless Claude Code as Hive Auto-Apply executor** — deferred then replaced by a deterministic Python worker (Dependabot/Renovate pattern) for reliability/auditability. (2026-05-13/14, Auto_Apply_Pipeline_Design)
- **gsudo** for headless elevation — superseded by the QI_Elevate broker; Access Denied from non-interactive subprocesses. Still fine interactively. (2026-05-14)
- **RapidOCR / RapidOcrNet** (PP-OCRv5/v6 ONNX+.NET) — approved 2026-06-22 as AutoPDF's second OCR engine, NOT started; Tesseract remains sole live engine. (AutoPDF status files)
- **PaddlePaddle Python OCR prototype** (autopdf_ocr.py) — rejected for footprint/AVX risk; never wired in; superseded by the planned RapidOcrNet route. (2026-06-22)
- **Qdrant** — QdrantExtractor built into MapSnap's extraction layer but shipped optional, never enabled by default. (MapSnap status files)
- **ScanSnap scanners** — rejected for Digitization-Costs tool (no TWAIN/ISIS); Ricoh fi-8170 chosen. (2026-06-12/15)
- **pythonw.exe** for scheduled tasks — rejected (nulls sys.stdout, breaks logging; venvs lack it); conhost --headless + python.exe instead. (2026-06-18)
- **Cloudflare Workers AI via OpenClaw plugin** — plugin found hardcoded to Anthropic API; patch deferred. (2026-05-16)
- **dots.tts** (local GPU voice cloning for OpenClaw Koe) — built but parked/disabled (EN/ZH only); edge-tts + Piper used instead. (OpenClaw status intro)
- **D-ID / HeyGen** (cloud avatar SaaS) — wired into AvatarStudio as swappable engines but disabled by default (API keys, cost); local LivePortrait/Hallo2 + Kokoro/edge-tts is the default path.
- **MuseTalk / SadTalker / Wav2Lip** — pre-wired AvatarStudio lip-sync alternates, disabled pending WSL2 installs (install-blocked more than rejected).
- **XTTS-v2 / F5-TTS voice cloning** — reserved as Stage 2.5 polish for War Room avatars; edge-tts is the live baseline, Kokoro the local middle ground. (2026-06-18, Phase N spec)
- **WebSocket push for Naya** — polling refresh used instead. (2026-04-13)
- **Microsoft Graph API** (Outlook) — deferred; Outlook→Gmail forwarding as interim. (2026-04-14)
- **Playwright sync_testers.py for EasyFlow** — deferred by Renne in favor of Claude-driven manual syncing. (2026-04-15)
- **Cloudflare named tunnels for the 4-bot rollout** — stayed on quick tunnels until the domain was owned (later adopted ecosystem-wide — partial/timing deferral). (2026-05-15)
- **Telethon janitor** (Telegram cleanup) — deferred; wire filter judged sufficient. (2026-05-15)
- **webcall_server.py** (WebRTC-style call server, Claude Voice) — superseded by meeting_server (both :8722); not run.

False lead checked: **NotebookLM** IS adopted (Kaze news-digest archive + knowledge-base client) — not a rejected item.

---

## Appendix — how to regenerate this inventory

1. Rebuild per-app stacks: re-run the project-library build (`C:\QIH\shared\documentation\project_library\_build_project_docs.py`) so each app's `source/status_techstack.json` is fresh.
2. Re-aggregate: `python C:\APPS\CLAUDE\Tools\techstack_aggregate.py`
3. Refresh latest-version research (PyPI/npm/GitHub) and update the research JSONs.
4. `python C:\APPS\CLAUDE\Tools\gen_component_inventory.py` → writes this file into the project library.
5. `python C:\APPS\CLAUDE\Tools\gen_inventory_pdf.py` → refreshes the .docx/.pdf twins.
6. Re-index the Library: `python C:\QIH\engine\brain\doc_harvester.py --no-embed` (or full run to embed).
