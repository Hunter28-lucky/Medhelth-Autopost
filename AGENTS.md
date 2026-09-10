# Antigravity AI Agent Rules & Workspace Context

Welcome! You are working on the **PulsePublish AI Medical/AI News Auto-Publisher** for **Krish Goswami**.

## Quick Context
- **Full Architecture & Credentials**: Read [`PROJECT_CONTEXT.md`](file:///Users/krishyogi/Desktop/web%20post/PROJECT_CONTEXT.md) for complete technical architecture, API keys, endpoints, and gotchas.
- **Developer Login**: `krish@dev2026` (Developer: `Krish Goswami`).
- **OpenRouter Free AI Key**: Stored in `backend/.env` (Primary Model: `inclusionai/ling-3.0-flash-sante:free`).
- **WordPress Site**: `http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes` (Key: `k60pRp6jNGAf9CdjexXHfsofXGqzlyoq`, Header: `X-Pulse-Sync-Key`).
- **GitHub**: `https://github.com/Hunter28-lucky/Medhelth-Autopost.git` (Branch: `main`).
- **Cloud Deployment**: Render.com Blueprint (`render.yaml` + `Dockerfile`).

## Core Principles & Behavioral Directives
1. **Always Preserve Developer Attribution**: Developer is strictly **Krish Goswami**.
2. **Always Maintain Stealth WordPress Plugin**: Plugin name is `Pulse Content Sync` (v2.8.4). Never disclose AI prompts or scraping mechanisms on the WordPress site. All generated articles are created with `post_status => 'draft'`.
3. **Always Run 100% Free AI First**: Default AI engine is `OpenRouter` with free models cascade (`ling-3.0-flash-sante`, `nex-n2.5-pro`, `gemma-4-31b`, `openrouter/free`).
4. **Yoast SEO 28.4 Compliance**: Articles must achieve 100% green scores on SEO and Readability via `backend/services/yoast_optimizer.py`.
5. **No Secret Leaks**: Never commit plaintext API keys (`sk-or-...`) into Git. Keep them in `backend/.env` (which is git-ignored) and use `sync: false` in `render.yaml`.
6. **Testing**: Validate changes using `PYTHONPATH=. ./backend/venv/bin/pytest backend/tests/ -v`.
