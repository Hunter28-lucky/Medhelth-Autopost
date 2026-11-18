# PulsePublish AI — Master Project Context & AI Handoff Manifest

> **Note for AI Coding Assistants**: This file contains the complete, authoritative architectural, environmental, and workflow state for the **Multi-Site AI-Powered Journalism Research & WordPress Auto-Publisher** system developed for **Krish Goswami**. Read this document to get instant, 360-degree context without re-analyzing the entire codebase.

---

## 1. Project Overview & Architecture

PulsePublish is a full-stack, multi-site automated publishing and intelligence platform. It autonomously discovers trending domain-specific news (clinical studies & healthcare for medical sites, human capital & enterprise leadership for workplace sites), synthesizes original high-authority draft articles via OpenRouter frontier free AI models, runs automated Yoast SEO 28.4 compliance audits to guarantee 100% green scores, checks semantic deduplication against all historical posts within the target site, and syncs approved drafts into WordPress sites via a stealth connector plugin (`Pulse Content Sync`).

```
┌────────────────────────────────────────────────────────────────────────┐
│                    REACT MULTI-SITE CONTROL DASHBOARD                  │
│           (Port 5173 / Single-Port Cloud Host on FastAPI '/')          │
│   Site Switcher │ Topics (129) │ Content Rules │ Review Queue │ Logs   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (/api/*) [SafeFetch Resilient]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI ASYNCHRONOUS BACKEND (Port 8081)            │
│  • Auth: Developer Password & HMAC-SHA256 Token (Krish Goswami)        │
│  • Multi-Site Core: Isolated Site ID routing (MedHealth Times & HR Rev)│
│  • Research Engine: PubMed/Europe PMC (Medical) & DDG HR News (Work)   │
│  • AI Engine: OpenRouter Free Models Cascade (Zero API Cost)           │
│  • Dedup Engine: Site-Scoped TF-IDF Scikit-Learn Cosine Similarity     │
│  • Yoast SEO Engine: Self-Healing 100% Green Audit & Auto-Fixer        │
│  • DB: SQLite (publisher.db) with site-isolated unique indexes         │
│  • Scheduler: APScheduler Background Cron Runner per Website           │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ HTTP REST + X-Pulse-Sync-Key   │ HTTP REST + Key
                    ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│  SITE 1: MedHealth Times             │  │  SITE 2: The HR Review       │
│  • URL: ~ttprdsmy/medhealthtimes     │  │  • URL: https://thehrreview  │
│  • Topics: 69 Medical Categories     │  │  • Topics: 60 HR Categories  │
│  • Connector: Pulse Content Sync     │  │  • Connector: Pulse Content  │
│  • Status: post_status = 'draft'     │  │  • Status: 'draft'           │
└──────────────────────────────────────┘  └──────────────────────────────┘
```

---

## 2. Credentials & Environment Vault

| Key / Variable | Value / Configuration | Location |
|---|---|---|
| **Developer Name** | `Krish Goswami` | `backend/config.py` |
| **Developer Password** | `krish@dev2026` | `backend/.env`, `backend/config.py` |
| **OpenRouter API Key** | `sk-or-v1-1c05370f...` (Stored locally in `backend/.env`) | `backend/.env` |
| **Active AI Provider** | `openrouter` (100% Free Tier Cascade) | `backend/config.py` |
| **Primary Free Model** | `inclusionai/ling-3.0-flash-sante:free` | `backend/config.py` |
| **Site 1 (MedHealth Times)** | `http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes` | ID 1, `managed_sites` |
| **Site 2 (The HR Review)** | `https://thehrreview.com` | ID 2, `managed_sites` |
| **WordPress API Sync Key** | `k60pRp6jNGAf9CdjexXHfsofXGqzlyoq` (Shared by both sites) | `backend/.env` / DB |
| **WordPress Headers** | `X-Pulse-Sync-Key` / `X-WP-AI-Key` | `backend/services/wp_client.py` |
| **GitHub Repository** | `https://github.com/Hunter28-lucky/Medhelth-Autopost.git` | Remote `origin/main` |
| **Render Cloud URL** | `https://anaya-web-post-ting-agent.onrender.com` | Render.com Docker Deploy |

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
│   ├── database.py             # SQLite async engine, WAL mode, composite unique indexes
│   ├── models.py               # ManagedSite, Topic, ContentRule, ResearchArticle, GeneratedPost, PipelineRun
│   ├── publisher.db            # Seeded SQLite database (2 sites, 129 topics, isolated rules)
│   ├── requirements.txt        # Python dependencies (includes lxml_html_clean)
│   ├── schemas.py              # Defensively nullable Pydantic request/response schemas
│   ├── seed_user_categories.py # Category seed scripts for MedHealth Times and The HR Review
│   ├── main.py                 # FastAPI application routes, auth, static serving
│   ├── services/
│   │   ├── auth_service.py     # HMAC-SHA256 token issuance & validation
│   │   ├── dedup_engine.py     # Scikit-Learn TF-IDF cosine similarity scoped strictly by site_id
│   │   ├── free_search_provider.py # Smart domain-aware search routing (Medical vs HR/Workforce)
│   │   ├── generator_engine.py # HR & Medical prompt builders, few-shot style cloner, OpenRouter router
│   │   ├── openrouter_client.py# OpenRouter free cascade with robust JSON parser & token economics
│   │   ├── pipeline.py         # 5-stage research -> AI -> Dedup -> Yoast -> WP engine with site isolation
│   │   ├── research_engine.py  # Article crawler, trafilatura, key fact extractor
│   │   ├── scheduler.py        # APScheduler background runner per site
│   │   ├── search_providers.py # Provider factory (free_online, serpapi, newsapi)
│   │   ├── wp_client.py        # WordPress REST API client with taxonomy lookup for all 60 HR categories
│   │   └── yoast_optimizer.py  # Yoast SEO 28.4 compliance & auto-fix engine
│   └── tests/                  # 14 Pytest test suites including multisite isolation (100% passing)
├── frontend/
│   ├── dist/                   # Production React build (served by FastAPI at '/')
│   ├── src/
│   │   ├── App.jsx             # Main dashboard layout, site switcher, safeFetchJson resilience
│   │   ├── apiClient.js        # Global fetch interceptor (appends Bearer token)
│   │   ├── components/
│   │   │   ├── TopicManager.jsx        # 129 categories manager, keyword editor, bulk import
│   │   │   ├── ContentRulesEditor.jsx  # Tone, word count, style cloner, site-specific rules
│   │   │   ├── DraftReviewQueue.jsx    # Review gate, preview modal, Yoast score pills
│   │   │   ├── YoastSeoInspector.jsx   # Live Yoast SEO & readability audit modal
│   │   │   ├── RunControlsAndLogs.jsx  # Manual triggers, execution logs, live stream
│   │   │   ├── SiteManager.jsx         # Multi-site configuration, health check & test connection
│   │   │   └── SystemSettings.jsx      # OpenRouter key, WP keys, scheduler toggle
├── wp-plugin/
│   ├── pulse-content-sync.zip  # Compiled distributable WordPress stealth plugin (v2.8.4)
│   └── ai-news-publisher/      # Plugin source code (v2.8.4 by Krish Goswami)
```

---

## 4. Multi-Site Architecture & Zero-Collision Isolation

The system hosts multiple independent publications within a single unified backend and dashboard while maintaining 100% data and editorial isolation:

### A. Managed Sites Taxonomy
1. **MedHealth Times (`site_id = 1`)**:
   - Target URL: `http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes`
   - Niche: Clinical research, medical breakthroughs, biotechnology, pharmaceutical news.
   - Topics: 69 active medical categories.
2. **The HR Review (`site_id = 2`)**:
   - Target URL: `https://thehrreview.com`
   - Niche: Strategic Human Resources, workplace leadership, talent management, employee experience, and HR technology.
   - Topics: 60 active HR categories (*Administration Management, AI in HR, Applicant Tracking Systems, Blogs, Change Management, Compensation Management, Corporate Advisory, Diversity and Inclusion Management, editors pick, Employee Benefits, Employee Communication, Employee Engagement, Employee Expense Management, Employee Experience Management, Employee Health Management, Employee Learning Management, Employee Monitoring, Employee Onboarding, Employee Performance Management, Employee Satisfaction Management, Employee Training, Employee Wellbeing, Employment Law, Employment Verification, Featured, Financial Wellness, Headline News, Hiring, Hiring and Onboarding, Hot this week, HR Reporting, Human Capital Management, Human Resource Management System, Human Resources Compliance, Insights, Labor Allocation, Labour Management, Must Read, News, Payroll Management, Payroll Tax, Performance Management, popular, Position Management, Pre Employment Screening, Press Release, Professional Employer Organization, Profile, Recruitment, Recruitment Process Outsourcing, Remote Work, Retirement, Talent Management, Time and Attendance Management, Top Stories, Trending, Uncategorized, Woman Leaders, Workforce Management, Xclusive Articles*).

### B. Database Schema & Composite Unique Indexes
- SQLite index `uq_topics_site_id_name ON topics (site_id, name)`:
  Categories with shared generic names across websites (e.g. *Featured, Blogs, Headline News, Insights, Must Read, News, popular, Press Release, Profile, Top Stories, Trending, Uncategorized, Xclusive Articles*) coexist cleanly without collisions or database integrity crashes.
- All database queries for topics, content rules, drafts, and pipeline logs filter strictly by `site_id`.

### C. Zero-Collision Search & Generation Routing
- **Search Engine Routing (`backend/services/free_search_provider.py`)**:
  - `_is_hr_workforce_query()` detects HR/workplace topics and routes them exclusively to DuckDuckGo workplace/HR news, completely bypassing medical feeds (NCBI PubMed, Europe PMC, clinical RSS).
  - Medical indicator negative checks prevent false positives (e.g., "Cancer Screening" is never mistakenly routed as an HR "Screening" query).
- **Deduplication Engine Isolation (`backend/services/dedup_engine.py`)**:
  - Both pre-generation URL/headline checks and post-generation Scikit-Learn TF-IDF cosine similarity checks are scoped strictly to `post.site_id == site_id`.
  - Articles from The HR Review are never compared against MedHealth Times articles, preventing false duplicate flags.
- **Dedicated HR Procedural Generator (`backend/services/generator_engine.py`)**:
  - Contains specialized HR prompts and a fallback procedural sandbox generator producing authoritative 460–510 word executive workplace journalism with zero medical terminology.
- **WordPress Publishing Routing (`backend/services/pipeline.py` & `wp_client.py`)**:
  - Pushes route dynamically to the target site's `wp_url`.
  - `HR_KNOWN_CATEGORIES` and `HR_LOOKUP` ensure every HR post is tagged with its correct WordPress category on `thehrreview.com`.

---

## 5. Key Subsystems & Technical Details

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
  - Automatically strips reasoning tags (`<think>...</think>`).
  - Regex `\{.*\}` multi-line extraction for robust JSON parsing.
  - Automatically cascades on HTTP 429 rate limits or HTTP 502 model overloads.
  - Fallback deterministic sandboxes (separate medical and HR sandboxes).

### B. Yoast SEO 28.4 Compliance Engine
- Located in `backend/services/yoast_optimizer.py`.
- Evaluates 8 SEO criteria and 6 Readability criteria:
  - Focus keyphrase in SEO title, meta description (135–155 chars), URL slug, introduction paragraph, and subheadings.
  - Keyphrase density between 1.0% and 2.5%.
  - Flesch Reading Ease score calculation.
  - Transition words percentage ($\ge 30\%$).
  - Paragraph length ($\le 150$ words) and sentence length ($\le 20$ words for 75%+).
- Includes **Auto-Fixer (`auto_fix_draft_to_green`)**: Automatically injects missing focus keyphrase and transition words to guarantee 100% Green lights.

### C. WordPress Stealth Connector (`Pulse Content Sync` v2.8.4)
- Located in `wp-plugin/ai-news-publisher/` and packaged as `pulse-content-sync.zip`.
- **Endpoints**: `/wp-json/pulse-sync/v1/posts` and `/wp-json/pulse-sync/v1/health`.
- **Stealth Architecture**: Completely white-labeled as "Pulse Content Sync by Krish Goswami" with zero AI disclosures on the WordPress site.
- **Direct Download**: Served directly at `https://anaya-web-post-ting-agent.onrender.com/pulse-content-sync.zip` for 1-click installation.
- **Draft Guarantee**: Posts are strictly inserted with `post_status => 'draft'`.

---

## 6. Solved Gotchas & Important Lessons

1. **Pydantic v2 Nullable DB Fields**:
   - Pydantic v2 raises `ValidationError` when an existing DB column is `NULL` unless the field is explicitly `Optional[T] = None` or has a default factory.
   - All response schemas in `backend/schemas.py` (`SiteResponse`, `TopicResponse`, `ContentRuleResponse`, `GeneratedPostResponse`, `RunLogResponse`) use defensive `Optional` typing and default factories to prevent 500 crashes.
2. **Frontend Multi-Request Resilience (`safeFetchJson`)**:
   - In `frontend/src/App.jsx`, avoid raw `Promise.all([fetch().then(r => r.json())])` because a single non-200 response will cause the entire promise chain to reject and blank out the UI.
   - `safeFetchJson` catches individual network errors and returns `null`, allowing sites, topics, and drafts to load reliably even if one ancillary endpoint fails.
3. **Database Unique Constraints in Multi-Site**:
   - When multiple sites share category names (e.g. "Featured", "Trending"), global unique indexes on `topics(name)` cause SQLite `IntegrityError`. Always use composite unique index `(site_id, name)`.
4. **GitHub Push Protection (Secret Scanning)**:
   - Never commit raw plaintext API keys (e.g. `sk-or-v1-...`) to Git. Keep secrets in `backend/.env` (which is git-ignored) and use `sync: false` in `render.yaml`.

---

## 7. How to Run Locally & Verify

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
npm --prefix frontend run build
```
