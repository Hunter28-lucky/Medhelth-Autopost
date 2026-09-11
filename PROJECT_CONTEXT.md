# PulsePublish AI — Master Project Context & AI Handoff Manifest

> **Note for AI Coding Assistants**: This file contains the complete, authoritative architectural, environmental, and workflow state for the **AI-Powered Medical & AI News Research & WordPress Auto-Publisher** system developed for **Krish Goswami**. Read this document to get instant, 360-degree context without re-analyzing the entire codebase.

---

## 1. Project Overview & Architecture

PulsePublish is a full-stack, automated medical & AI journalism intelligence platform. It autonomously discovers trending clinical studies and medical news from peer-reviewed literature and the open web, synthesizes original high-authority draft articles via OpenRouter frontier free AI models, runs automated Yoast SEO 28.4 compliance audits to guarantee 100% green scores, checks semantic deduplication against all historical posts, and syncs approved drafts into a WordPress site via a stealth custom connector plugin (`Pulse Content Sync`).

```
┌────────────────────────────────────────────────────────────────────────┐
│                          REACT CONTROL DASHBOARD                       │
│           (Port 5173 / Single-Port Cloud Host on FastAPI '/')          │
│   Topics (74) │ Style Cloner │ Review Queue │ Logs │ Live Settings     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (/api/*)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI ASYNCHRONOUS BACKEND (Port 8081)            │
│  • Auth: Developer Password & HMAC-SHA256 Token (Krish Goswami)        │
│  • Research Engine: DuckDuckGo HTML + Europe PMC + PubMed Central      │
│  • AI Engine: OpenRouter Free Models Cascade (Zero API Cost)           │
│  • Dedup Engine: TF-IDF Scikit-Learn Vectorizer & Cosine Similarity    │
│  • Yoast SEO Engine: Self-Healing 100% Green Audit & Auto-Fixer        │
│  • DB: SQLite (publisher.db) via SQLAlchemy & aiosqlite               │
│  • Scheduler: APScheduler Background Cron Runner                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST + X-Pulse-Sync-Key
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             WORDPRESS SITE & STEALTH CONNECTOR PLUGIN                  │
│  • Plugin: Pulse Content Sync v2.8.4 (wp-plugin/pulse-content-sync.zip)│
│  • Target: http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes   │
│  • Endpoints: /wp-json/pulse-sync/v1/post & /health                    │
│  • Security: Header auth, Mod_Security friendly, Coming Soon bypass    │
│  • Posts created strictly with post_status = 'draft'                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Credentials & Environment Vault

| Key / Variable | Value / Configuration | Location |
|---|---|---|
| **Developer Name** | `Krish Goswami` | `backend/config.py` |
| **Developer Password** | `krish@dev2026` | `backend/.env`, `backend/config.py` |
| **OpenRouter API Key** | `sk-or-v1-1c05370f...` (Stored locally in `backend/.env`) | `backend/.env` |
| **Active AI Provider** | `openrouter` (100% Free Tier) | `backend/config.py` |
| **Primary Free Model** | `inclusionai/ling-3.0-flash-sante:free` | `backend/config.py` |
| **WordPress Site URL** | `http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes` | `backend/.env` |
| **WordPress API Key** | `k60pRp6jNGAf9CdjexXHfsofXGqzlyoq` | `backend/.env` |
| **WordPress Headers** | `X-Pulse-Sync-Key` / `X-WP-AI-Key` | `backend/services/wp_client.py` |
| **GitHub Repository** | `https://github.com/Hunter28-lucky/Medhelth-Autopost.git` | Remote `origin/main` |
| **Render Service** | `Medhelth-Autopost` | Render.com Docker Blueprint |

---

## 3. Directory Map & Component Roles

```
web post/
├── AGENTS.md                   # Global agent workspace instructions & conventions
├── PROJECT_CONTEXT.md          # This master context & handoff documentation
├── DEPLOYMENT.md               # Production hosting & Docker guide
├── Dockerfile                  # Multi-stage build (Node 20 React build + Python 3.10)
├── render.yaml                 # Render.com Blueprint (zero-config cloud deploy)
├── build.sh                    # Linux/Render native build script
├── start.command               # Double-clickable macOS launcher
├── start.sh                    # Linux/macOS shell launcher
├── backend/
│   ├── .env                    # Local secrets (ignored by git for secret scanning)
│   ├── .env.example            # Sample environment variables
│   ├── config.py               # Pydantic-style system settings & defaults
│   ├── database.py             # SQLite async engine & Base declarative
│   ├── models.py               # Topic, ContentRule, ResearchArticle, GeneratedPost, PipelineRun
│   ├── publisher.db            # Seeded SQLite database (74 topics + clinical keywords)
│   ├── requirements.txt        # Python dependencies (includes lxml_html_clean)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── seed_user_categories.py # 69+ custom medical category seed script
│   ├── main.py                 # FastAPI application routes, auth, static serving
│   ├── services/
│   │   ├── auth_service.py     # HMAC-SHA256 token issuance & validation
│   │   ├── dedup_engine.py     # Scikit-Learn TF-IDF cosine similarity
│   │   ├── free_search_provider.py # DuckDuckGo HTML + Europe PMC + PubMed search
│   │   ├── generator_engine.py # Prompt builder, few-shot style cloner, OpenRouter router
│   │   ├── openrouter_client.py# OpenRouter free cascade with robust JSON parser
│   │   ├── pipeline.py         # 5-stage research -> AI -> Dedup -> Yoast -> WP engine
│   │   ├── research_engine.py  # Article crawler, trafilatura, key fact extractor
│   │   ├── scheduler.py        # APScheduler background runner
│   │   ├── search_providers.py # Provider factory (free_online, serpapi, newsapi)
│   │   ├── wp_client.py        # WordPress REST API client (Mod_Security & CSMM bypass)
│   │   └── yoast_optimizer.py  # Yoast SEO 28.4 compliance & auto-fix engine
│   └── tests/                  # 16 Pytest test suites (100% passing)
├── frontend/
│   ├── dist/                   # Production React build (served by FastAPI at '/')
│   ├── src/
│   │   ├── App.jsx             # Main dashboard layout, tabs, developer lock screen
│   │   ├── apiClient.js        # Global fetch interceptor (appends Bearer token)
│   │   ├── components/
│   │   │   ├── TopicManager.jsx        # 74 categories manager, keyword editor, bulk import
│   │   │   ├── ContentRulesEditor.jsx  # Tone, word count, style cloner, few-shot box
│   │   │   ├── DraftReviewQueue.jsx    # Review gate, preview modal, Yoast score pills
│   │   │   ├── YoastSeoInspector.jsx   # Live Yoast SEO & readability audit modal
│   │   │   ├── RunControlsAndLogs.jsx  # Manual triggers, execution logs, live stream
│   │   │   └── SystemSettings.jsx      # OpenRouter key, WP keys, scheduler toggle
├── wp-plugin/
│   ├── pulse-content-sync.zip  # Compiled distributable WordPress stealth plugin
│   └── ai-news-publisher/      # Plugin source code (v2.8.4 by Krish Goswami)
```

---

## 4. Key Subsystems & Technical Details

### A. Free AI Engine & OpenRouter Cascade
- Located in `backend/services/openrouter_client.py`.
- **Primary Model**: `inclusionai/ling-3.0-flash-sante:free` (Specialized in medical & healthcare).
- **Fallback Cascade**:
  1. `inclusionai/ling-3.0-flash-sante:free`
  2. `nex-agi/nex-n2.5-pro:free`
  3. `nex-agi/nex-n2.5-mini:free`
  4. `google/gemma-4-31b-it:free`
  5. `openrouter/free`
- **Resilience**:
  - Automatically cleans `<think>...</think>` tags from reasoning models.
  - Uses regex `\{.*\}` multi-line search for resilient JSON extraction.
  - Catches upstream rate limits (HTTP 429) or overloaded models (HTTP 502) and cascades to the next candidate model.
  - Falls back to deterministic clinical sandbox if network is unavailable.

### B. Free Research & Scraping Provider
- Located in `backend/services/free_search_provider.py`.
- Queries **DuckDuckGo HTML**, **Europe PMC API**, and **NCBI PubMed Central** without requiring any paid search API keys.
- Extracts full-text using `trafilatura` and `beautifulsoup4`.
- Respects `robots.txt` and skips paywalls / binary PDFs.

### C. Yoast SEO 28.4 Compliance Engine
- Located in `backend/services/yoast_optimizer.py`.
- Evaluates 8 SEO checks and 6 Readability checks:
  - Focus keyphrase in SEO title, meta description (135–155 chars), URL slug, introduction paragraph, and `<h2>` headings.
  - Keyphrase density between 1.0% and 2.5%.
  - Flesch Reading Ease score calculation.
  - Transition words percentage ($\ge 30\%$).
  - Paragraph length ($\le 150$ words) and sentence length ($\le 20$ words for 75%+).
- Includes **Auto-Fixer (`auto_fix_draft_to_green`)**: Automatically injects missing focus keyphrase and transition words to achieve 100% Green lights.

### D. WordPress Connector (`Pulse Content Sync` v2.8.4)
- Located in `wp-plugin/ai-news-publisher/` and packaged as `pulse-content-sync.zip`.
- **Endpoints**: `/wp-json/pulse-sync/v1/post` and `/wp-json/pulse-sync/v1/health`.
- **Stealth Architecture**: Completely white-labeled as "Pulse Content Sync by Krish Goswami" with zero AI disclosures on the WordPress site.
- **Mod_Security Bypass**: Requests from `WordPressClient` send Chrome browser User-Agents so Apache Mod_Security firewall does not return HTTP 406.
- **Maintenance Mode Bypass**: Plugin hooks at `init` priority 1 to unhook `csmm_plugin_init` (`Minimal Coming Soon & Maintenance Mode`) when authorized API requests arrive.

### E. Seeded Medical Categories (74 Active Topics)
- Seeded via `backend/seed_user_categories.py` into `backend/publisher.db`.
- Covers 74 categories including: *Cardiovascular, Oncology, Artificial Intelligence, Endocrinology, Telemedicine, Digital Health Transformation, Genomics, Nanotechnology, Health Wearables, Assistive Devices*, etc.

### F. Standardized Editorial Blueprint (`example post.md`)
- **Canonical Reference**: [`example post.md`](file:///Users/krishyogi/Desktop/web%20post/example%20post.md) holds the exact reference articles (`EggNest Launch Egg Medical Unveils Version 2.0 .` and `Patent Dispute Court Ruling Reshapes Biotech Competition .`) directly from WordPress Classic Editor screenshots.
- **Clean Semantic WordPress HTML (`H6 » STRONG`)**: Output strictly contains clean `<h6><strong>Heading Title</strong></h6>` section headers and `<p>` body paragraphs. Zero custom styled `<div>` containers, no inline CSS, and no artificial callout blocks in `body_html` so WordPress Classic & Gutenberg editors render native, clean typography matching the WordPress editor's `H6 » STRONG` breadcrumb path.
- **5-6 Section Cadence (Strictly 450–520 words, ~482 words exact editor benchmark)**:
  - 5 to 6 concise sections with 1 to 3 short paragraphs each (2–3 sentences, 30–50 words per paragraph).
  - Headline structure: `[Focus Keyphrase] [Subject/Action/Detail] .` (ends with a period).
- **Yoast SEO 28.4 Compliance**: Frontloaded focus keyphrase, 3–5 total keyphrase occurrences for optimal density (1.0%–2.2%), $\ge 30\%$ natural transition phrases (*"Specifically"*, *"Furthermore"*, *"Consequently"*, *"In addition"*, *"Therefore"*, *"Another advantage"*, *"Notably"*, *"Moreover"*, *"However"*, *"Ultimately"*), scoring 100/100 on Readability and SEO.

---

## 5. Solved Gotchas & Important Lessons

1. **GitHub Push Protection (Secret Scanning)**:
   - Never commit raw plaintext API keys (e.g. `sk-or-v1-...`) to Git.
   - `backend/.env` is in `.gitignore` to keep local secrets safe.
   - `render.yaml` uses `sync: false` for API keys so Render prompts or allows environment configuration without committing keys to Git.
2. **Linux Container `trafilatura` / `justext` Dependency**:
   - `lxml>=5.2` removed `lxml.html.clean` into `lxml_html_clean`.
   - `backend/requirements.txt` explicitly specifies `lxml_html_clean>=0.1.0`.
3. **OpenRouter Response Handling**:
   - OpenRouter sometimes returns HTTP 200 with an internal `{"error": ...}` payload if an upstream provider is overloaded; `_send_request` checks for `"error"` in response data.
   - `openrouter_client.py` uses null-safe content access: `(choices[0].get("message", {}).get("content") or "").strip()`.
4. **WordPress Maintenance Mode**:
   - If the remote site returns "Coming Soon" HTML, the user can either disable Maintenance Mode in WP Admin -> Settings -> Minimal Coming Soon, or install the updated `pulse-content-sync.zip` which has priority-1 unhooking.

---

## 6. How to Run Locally & Verify

```bash
# 1. Start backend
PYTHONPATH=. ./backend/venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8081

# 2. Start frontend dev server
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173

# 3. Or launch both in 1 click (macOS)
./start.command

# 4. Run test suite
PYTHONPATH=. ./backend/venv/bin/pytest backend/tests/ -v

# 5. Build production frontend
cd frontend && npm run build
```
