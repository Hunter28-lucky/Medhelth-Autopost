import re
import datetime
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import init_db, get_db, AsyncSessionLocal
from backend.models import Topic, ContentRule, GeneratedPost, RunLog
from backend.schemas import (
    TopicCreate, TopicUpdate, TopicResponse, TopicBulkImport,
    ContentRuleResponse, ContentRuleUpdate,
    GeneratedPostResponse, DraftReviewAction,
    RunTriggerRequest, RunLogResponse,
    SettingsResponse, SettingsUpdate,
    AuthLoginRequest, AuthLoginResponse
)
from backend.services.auth_service import (
    create_developer_token, verify_developer_token, require_developer
)
from backend.services.research_engine import ResearchEngine
from backend.services.generator_engine import ContentGenerator
from backend.services.dedup_engine import DeduplicationEngine
from backend.services.pipeline import PublishingPipeline
from backend.services.scheduler import scheduler_service
from backend.services.wp_client import WordPressClient
from backend.services.yoast_optimizer import yoast_optimizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("publisher.api")

pipeline = PublishingPipeline()

async def seed_initial_data():
    """Seed initial topics and content rules if database is fresh."""
    async with AsyncSessionLocal() as session:
        # Check topics
        topic_count_res = await session.execute(select(Topic))
        if not topic_count_res.scalars().first():
            default_topics = [
                Topic(
                    name="AI in Diagnostics",
                    keywords=["medical imaging AI", "CT scan deep learning", "radiomics biomarker", "computational pathology"],
                    weight=9,
                    is_active=True,
                    domain_whitelist=["nature.com", "nejm.org", "thelancet.com", "jamanetwork.com"],
                    lookback_days=7
                ),
                Topic(
                    name="Cardiology Breakthroughs",
                    keywords=["mRNA heart repair", "transcatheter valves", "cardiac myocyte regeneration", "heart failure clinical trial"],
                    weight=8,
                    is_active=True,
                    domain_whitelist=["nejm.org", "ahajournals.org", "acc.org", "thelancet.com"],
                    lookback_days=7
                ),
                Topic(
                    name="FDA Drug Approvals",
                    keywords=["FDA oncology approval", "novel therapeutics", "accelerated approval", "bispecific antibody"],
                    weight=8,
                    is_active=True,
                    domain_whitelist=["fda.gov", "biopharmadive.com", "fiercebiotech.com", "reuters.com"],
                    lookback_days=14
                ),
                Topic(
                    name="Mental Health Tech",
                    keywords=["digital phenotyping biomarkers", "psychiatric actigraphy", "depression digital therapeutics", "wearable EEG"],
                    weight=7,
                    is_active=True,
                    domain_whitelist=["jamanetwork.com", "psychiatryonline.org", "nature.com"],
                    lookback_days=14
                ),
                Topic(
                    name="Genomic & Base Editing",
                    keywords=["in vivo base editing", "CRISPR therapeutic trial", "gene therapy rare disease", "targeted LNP"],
                    weight=6,
                    is_active=True,
                    domain_whitelist=["cell.com", "nature.com", "science.org"],
                    lookback_days=14
                )
            ]
            session.add_all(default_topics)
            logger.info("Seeded 5 default medical & AI topics.")

        # Check content rules
        rule_res = await session.execute(select(ContentRule))
        if not rule_res.scalars().first():
            default_rule = ContentRule(
                name="Default Clinical SEO Guidelines",
                is_active=True,
                tone="Professional & Journalistic",
                reading_level="General Public with High School Education",
                word_count_min=800,
                word_count_max=1200,
                heading_structure="H1 Title, 3-4 H2 Sections, H3 Subsections",
                include_takeaways=True,
                include_faq=True,
                include_disclaimer=True,
                include_quotes=True,
                include_sources=True,
                disclaimer_text="Disclaimer: This article is for informational purposes only and does not constitute medical advice or formal clinical diagnosis. Consult a qualified healthcare professional before making health-related decisions.",
                style_guide_text="Maintain scientific accuracy. Avoid sensational headlines like 'miracle cure' or 'breakthrough.' Clearly specify clinical trial phases and distinguish preclinical animal data from human clinical trials.",
                auto_push_to_wp=settings.AUTO_PUSH_TO_WP
            )
            session.add(default_rule)
            logger.info("Seeded default Content Rules.")

        await session.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database schema...")
    await init_db()
    await seed_initial_data()
    if settings.SCHEDULER_ENABLED:
        scheduler_service.start()
    yield
    # Shutdown
    scheduler_service.stop()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Enable CORS for local dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# DEVELOPER AUTHENTICATION (KRISH GOSWAMI)
# ==============================================================================

@app.post("/api/auth/login", response_model=AuthLoginResponse)
async def developer_login(payload: AuthLoginRequest):
    """
    Developer-only authentication for Krish Goswami.
    Validates developer password and returns a cryptographic HMAC session token.
    """
    if payload.password != settings.DEVELOPER_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid developer password. Access is strictly restricted to Krish Goswami."
        )
    token = create_developer_token(settings.DEVELOPER_NAME)
    return AuthLoginResponse(
        success=True,
        token=token,
        developer_name=settings.DEVELOPER_NAME,
        message="Developer session initialized. Welcome, Krish Goswami."
    )

@app.get("/api/auth/verify")
async def verify_developer_session(developer: str = Depends(require_developer)):
    """Verifies that the caller has a valid, unexpired developer session token."""
    return {
        "authenticated": True,
        "developer_name": developer,
        "role": "Lead Developer & System Architect"
    }

# ==============================================================================
# TOPICS ENDPOINTS
# ==============================================================================

@app.get("/api/topics", response_model=List[TopicResponse])
async def list_topics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Topic).order_by(desc(Topic.weight), Topic.name))
    return result.scalars().all()

@app.post("/api/topics", response_model=TopicResponse, status_code=201, dependencies=[Depends(require_developer)])
async def create_topic(topic_in: TopicCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate name
    existing = await db.execute(select(Topic).where(Topic.name == topic_in.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="A topic category with this name already exists.")

    topic = Topic(**topic_in.model_dump())
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic

@app.get("/api/topics/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic

@app.put("/api/topics/{topic_id}", response_model=TopicResponse, dependencies=[Depends(require_developer)])
async def update_topic(topic_id: int, topic_in: TopicUpdate, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    update_data = topic_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(topic, key, value)

    await db.commit()
    await db.refresh(topic)
    return topic

@app.delete("/api/topics/{topic_id}", status_code=204, dependencies=[Depends(require_developer)])
async def delete_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    await db.delete(topic)
    await db.commit()
    return None

@app.post("/api/topics/bulk-import", response_model=List[TopicResponse], dependencies=[Depends(require_developer)])
async def bulk_import_topics(payload: TopicBulkImport, db: AsyncSession = Depends(get_db)):
    """
    Parses bulk text formatted as:
    Topic Name: keyword1, keyword2, keyword3
    or individual lines of topics/keywords.
    """
    created_topics = []
    lines = [line.strip() for line in payload.raw_text.splitlines() if line.strip()]

    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            name = parts[0].strip()
            kw_raw = parts[1].strip()
            keywords = [k.strip() for k in re.split(r'[,;]', kw_raw) if k.strip()]
        else:
            name = line
            keywords = [line]

        if not name:
            continue

        existing = await db.execute(select(Topic).where(Topic.name == name))
        topic = existing.scalars().first()
        if topic:
            # Merge keywords
            current_kws = set(topic.keywords or [])
            current_kws.update(keywords)
            topic.keywords = list(current_kws)
            created_topics.append(topic)
        else:
            topic = Topic(
                name=name,
                keywords=keywords,
                weight=5,
                is_active=True,
                lookback_days=7
            )
            db.add(topic)
            created_topics.append(topic)

    await db.commit()
    for t in created_topics:
        await db.refresh(t)

    return created_topics

# ==============================================================================
# CONTENT RULES & SEO ENDPOINTS
# ==============================================================================

@app.get("/api/content-rules", response_model=ContentRuleResponse)
async def get_content_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContentRule).where(ContentRule.is_active == True))
    rule = result.scalars().first()
    if not rule:
        rule = ContentRule()
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return rule

@app.put("/api/content-rules", response_model=ContentRuleResponse, dependencies=[Depends(require_developer)])
async def update_content_rules(rules_in: ContentRuleUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContentRule).where(ContentRule.is_active == True))
    rule = result.scalars().first()
    if not rule:
        rule = ContentRule()
        db.add(rule)

    update_data = rules_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule

# ==============================================================================
# RUNS & PIPELINE EXECUTION
# ==============================================================================

async def run_pipeline_task(topic_id: int, force_fresh: bool):
    async with AsyncSessionLocal() as session:
        await pipeline.execute_run_for_topic(
            session=session,
            topic_id=topic_id,
            trigger_type="MANUAL",
            force_fresh_search=force_fresh
        )

@app.post("/api/runs/trigger", dependencies=[Depends(require_developer)])
async def trigger_run(
    payload: RunTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a run immediately for a specific topic, or all active topics.
    """
    if payload.topic_id:
        topic = await db.get(Topic, payload.topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        background_tasks.add_task(run_pipeline_task, payload.topic_id, payload.force_fresh_search)
        return {"status": "queued", "message": f"Run queued for topic: {topic.name}"}
    else:
        # Trigger for all active topics
        result = await db.execute(select(Topic).where(Topic.is_active == True))
        active_topics = result.scalars().all()
        if not active_topics:
            raise HTTPException(status_code=400, detail="No active topics found.")

        for t in active_topics:
            background_tasks.add_task(run_pipeline_task, t.id, payload.force_fresh_search)

        return {"status": "queued", "message": f"Runs queued for {len(active_topics)} active topics."}

@app.get("/api/runs/history", response_model=List[RunLogResponse])
async def get_run_history(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunLog).order_by(desc(RunLog.started_at)).limit(limit))
    return result.scalars().all()

@app.get("/api/runs/{run_id}", response_model=RunLogResponse)
async def get_run_detail(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunLog).where(RunLog.run_id == run_id))
    log_entry = result.scalars().first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Run log not found")
    return log_entry

# ==============================================================================
# DRAFTS & EDITORIAL QUEUE
# ==============================================================================

@app.get("/api/drafts", response_model=List[GeneratedPostResponse])
async def list_drafts(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = select(GeneratedPost).order_by(desc(GeneratedPost.created_at)).limit(limit)
    if status:
        query = query.where(GeneratedPost.status == status)
    result = await db.execute(query)
    return result.scalars().all()

@app.get("/api/drafts/{post_id}", response_model=GeneratedPostResponse)
async def get_draft(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(GeneratedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Draft not found")
    return post

@app.post("/api/drafts/{post_id}/action", dependencies=[Depends(require_developer)])
async def review_draft_action(
    post_id: int,
    action_in: DraftReviewAction,
    db: AsyncSession = Depends(get_db)
):
    """
    Editorial actions:
    - 'approve': Approves the draft
    - 'reject': Marks the draft as rejected
    - 'push_to_wp': Pushes the draft directly to WordPress
    - 'regenerate': Re-generates using a different angle/feedback
    """
    post = await db.get(GeneratedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Draft post not found")

    act = action_in.action.lower().strip()

    if act == "approve":
        post.status = "APPROVED"
        await db.commit()
        return {"success": True, "status": post.status, "message": "Draft marked as approved."}

    elif act == "reject":
        post.status = "REJECTED"
        await db.commit()
        return {"success": True, "status": post.status, "message": "Draft rejected."}

    elif act == "push_to_wp":
        res = await pipeline.push_draft_to_wordpress(db, post_id)
        if not res.get("success"):
            raise HTTPException(status_code=500, detail=res.get("error", "WordPress push failed"))
        return res

    elif act == "regenerate":
        # Load topic and rules
        topic = await db.get(Topic, post.topic_id) if post.topic_id else None
        rule_res = await db.execute(select(ContentRule).where(ContentRule.is_active == True))
        rules = rule_res.scalars().first() or ContentRule()

        # Gather sources
        fake_research = [
            {"title": s.get("title", post.title), "url": s.get("url", "https://example.com"), "source": s.get("domain", "Journal"), "key_claims": post.key_takeaways or []}
            for s in (post.sources_used or [])
        ]
        if not fake_research:
            fake_research = [{"title": post.title, "url": "https://example.com", "source": "Clinical Journal", "key_claims": post.key_takeaways or []}]

        pivot_directive = action_in.feedback or "Pivot to a distinctly different subtopic: emphasize cellular mechanisms, diagnostic sensitivity, and patient-centric healthcare access."

        new_data = await pipeline.generator.generate_draft(
            topic_name=topic.name if topic else "Medical Innovation",
            research_articles=fake_research,
            rules=rules,
            deviation_angle_instruction=pivot_directive
        )

        # Update post
        post.title = new_data.get("title", post.title)
        post.slug = new_data.get("slug", post.slug)
        post.excerpt = new_data.get("excerpt", post.excerpt)
        post.body_html = new_data.get("body_html", post.body_html)
        post.meta_title = new_data.get("meta_title", post.meta_title)
        post.meta_description = new_data.get("meta_description", post.meta_description)
        post.key_takeaways = new_data.get("key_takeaways", post.key_takeaways)
        post.status = "PENDING_REVIEW"
        post.similarity_status = "RE_ANGLED"

        await db.commit()
        await db.refresh(post)
        return {"success": True, "status": post.status, "message": "Draft successfully regenerated with new angle."}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action '{action_in.action}'.")

@app.get("/api/drafts/{post_id}/yoast-audit")
async def get_draft_yoast_audit(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(GeneratedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Draft not found")

    post_dict = {
        "title": post.title,
        "slug": post.slug,
        "body_html": post.body_html,
        "meta_title": post.meta_title or post.title,
        "meta_description": post.meta_description or post.excerpt,
        "focus_keyphrase": post.focus_keyphrase,
        "tags": post.tags or [],
        "sources_used": post.sources_used or []
    }
    audit = yoast_optimizer.analyze_full_post(post_dict)
    return audit

@app.post("/api/drafts/{post_id}/yoast-autofix", dependencies=[Depends(require_developer)])
async def autofix_draft_yoast(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(GeneratedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Draft not found")

    post_dict = {
        "title": post.title,
        "slug": post.slug,
        "body_html": post.body_html,
        "meta_title": post.meta_title or post.title,
        "meta_description": post.meta_description or post.excerpt,
        "focus_keyphrase": post.focus_keyphrase,
        "tags": post.tags or [],
        "sources_used": post.sources_used or []
    }
    repaired = yoast_optimizer.auto_fix_post(post_dict)

    # Apply updates to database
    post.title = repaired["title"]
    post.slug = repaired["slug"]
    post.meta_title = repaired["meta_title"]
    post.meta_description = repaired["meta_description"]
    post.body_html = repaired["body_html"]
    post.focus_keyphrase = repaired["focus_keyphrase"]
    post.yoast_seo_score = repaired["yoast_seo_score"]
    post.yoast_readability_score = repaired["yoast_readability_score"]
    post.yoast_checklist = repaired["yoast_checklist"]

    await db.commit()
    await db.refresh(post)

    return {
        "success": True,
        "post_id": post.id,
        "focus_keyphrase": post.focus_keyphrase,
        "yoast_seo_score": post.yoast_seo_score,
        "yoast_readability_score": post.yoast_readability_score,
        "yoast_all_green": repaired.get("yoast_all_green", True),
        "yoast_checklist": post.yoast_checklist,
        "message": "Post successfully auto-fixed to 100% Yoast SEO green compliance!"
    }

# ==============================================================================
# SETTINGS & INTEGRATIONS
# ==============================================================================

@app.get("/api/settings", response_model=SettingsResponse)
async def get_settings():
    return SettingsResponse(
        ai_provider=settings.AI_PROVIDER,
        openrouter_api_key_configured=bool(settings.OPENROUTER_API_KEY),
        openrouter_model=settings.OPENROUTER_MODEL,
        anthropic_api_key_configured=bool(settings.ANTHROPIC_API_KEY),
        anthropic_model=settings.ANTHROPIC_MODEL,
        search_provider=settings.SEARCH_PROVIDER,
        serpapi_key_configured=bool(settings.SERPAPI_API_KEY),
        newsapi_key_configured=bool(settings.NEWSAPI_API_KEY),
        bing_key_configured=bool(settings.BING_API_KEY),
        wordpress_url=settings.WORDPRESS_URL,
        wordpress_api_key_configured=bool(settings.WORDPRESS_API_KEY),
        dedup_threshold=settings.DEDUP_SIMILARITY_THRESHOLD,
        auto_push_to_wp=settings.AUTO_PUSH_TO_WP,
        scheduler_enabled=settings.SCHEDULER_ENABLED,
        scheduler_interval_hours=settings.SCHEDULER_INTERVAL_HOURS
    )

@app.put("/api/settings", response_model=SettingsResponse, dependencies=[Depends(require_developer)])
async def update_settings(payload: SettingsUpdate):
    if payload.ai_provider is not None:
        settings.AI_PROVIDER = payload.ai_provider
        pipeline.generator = ContentGenerator()
    if payload.openrouter_api_key is not None:
        settings.OPENROUTER_API_KEY = payload.openrouter_api_key
        pipeline.generator = ContentGenerator()
    if payload.openrouter_model is not None:
        settings.OPENROUTER_MODEL = payload.openrouter_model
        pipeline.generator = ContentGenerator()
    if payload.anthropic_api_key is not None:
        settings.ANTHROPIC_API_KEY = payload.anthropic_api_key
        pipeline.generator = ContentGenerator()
    if payload.anthropic_model is not None:
        settings.ANTHROPIC_MODEL = payload.anthropic_model
        pipeline.generator = ContentGenerator()
    if payload.search_provider is not None:
        settings.SEARCH_PROVIDER = payload.search_provider
        pipeline.research_engine = ResearchEngine()
    if payload.serpapi_api_key is not None:
        settings.SERPAPI_API_KEY = payload.serpapi_api_key
    if payload.newsapi_api_key is not None:
        settings.NEWSAPI_API_KEY = payload.newsapi_api_key
    if payload.bing_api_key is not None:
        settings.BING_API_KEY = payload.bing_api_key
    if payload.wordpress_url is not None:
        settings.WORDPRESS_URL = payload.wordpress_url.rstrip("/")
        pipeline.wp_client = WordPressClient()
    if payload.wordpress_api_key is not None:
        settings.WORDPRESS_API_KEY = payload.wordpress_api_key
        pipeline.wp_client = WordPressClient()
    if payload.dedup_threshold is not None:
        settings.DEDUP_SIMILARITY_THRESHOLD = payload.dedup_threshold
        pipeline.dedup_engine = DeduplicationEngine(payload.dedup_threshold)
    if payload.auto_push_to_wp is not None:
        settings.AUTO_PUSH_TO_WP = payload.auto_push_to_wp
    if payload.scheduler_interval_hours is not None:
        settings.SCHEDULER_INTERVAL_HOURS = payload.scheduler_interval_hours
        scheduler_service.update_interval(payload.scheduler_interval_hours)
    if payload.scheduler_enabled is not None:
        settings.SCHEDULER_ENABLED = payload.scheduler_enabled
        if payload.scheduler_enabled:
            scheduler_service.start()
        else:
            scheduler_service.stop()
    if payload.developer_password is not None and payload.developer_password.strip():
        settings.DEVELOPER_PASSWORD = payload.developer_password.strip()

    return await get_settings()

@app.post("/api/settings/test-openrouter", dependencies=[Depends(require_developer)])
async def test_openrouter_connection():
    from backend.services.openrouter_client import OpenRouterClient
    client = OpenRouterClient()
    return client.check_connection()

@app.post("/api/settings/test-wordpress", dependencies=[Depends(require_developer)])
async def test_wordpress_connection():
    client = WordPressClient()
    res = client.check_connection()
    return res

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    return scheduler_service.get_status()

@app.post("/api/scheduler/toggle", dependencies=[Depends(require_developer)])
async def toggle_scheduler(enable: bool = Query(...)):
    if enable:
        scheduler_service.start()
        settings.SCHEDULER_ENABLED = True
    else:
        scheduler_service.stop()
        settings.SCHEDULER_ENABLED = False
    return scheduler_service.get_status()

@app.get("/api/download-plugin")
async def download_wordpress_plugin():
    from fastapi.responses import FileResponse
    from backend.config import BASE_DIR
    plugin_zip_path = BASE_DIR.parent / "wp-plugin" / "ai-news-publisher.zip"
    if not plugin_zip_path.exists():
        raise HTTPException(status_code=404, detail="Plugin zip archive not found")
    return FileResponse(
        path=str(plugin_zip_path),
        filename="pulse-content-sync.zip",
        media_type="application/zip"
    )

# ==============================================================================
# STATIC FRONTEND SERVING (SINGLE-PORT HOSTING & CLOUD DEPLOYMENT)
# ==============================================================================
from fastapi.staticfiles import StaticFiles
from backend.config import BASE_DIR

frontend_dist = BASE_DIR.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static_frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8081"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)



