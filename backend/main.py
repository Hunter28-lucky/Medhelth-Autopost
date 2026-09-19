import os
import re
import datetime
import logging
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import init_db, get_db, AsyncSessionLocal
from backend.models import Topic, ContentRule, GeneratedPost, RunLog, ManagedSite, ResearchArticle
from backend.schemas import (
    SiteCreate, SiteUpdate, SiteResponse, SiteTestResponse,
    TopicCreate, TopicUpdate, TopicResponse, TopicBulkImport,
    ContentRuleResponse, ContentRuleUpdate,
    GeneratedPostResponse, DraftReviewAction,
    DraftBulkDeleteRequest, DraftBulkDeleteResponse, DraftBulkPushRequest,
    RunTriggerRequest, RunLogResponse,
    SettingsResponse, SettingsUpdate,
    AuthLoginRequest, AuthLoginResponse,
    CostBreakdownResponse, CostAnalyticsSummaryResponse
)
from backend.services.auth_service import (
    create_developer_token, verify_developer_token, require_developer
)
from backend.services.research_engine import ResearchEngine
from backend.services.generator_engine import ContentGenerator, clean_semantic_post_html
from backend.services.dedup_engine import DeduplicationEngine
from backend.services.pipeline import PublishingPipeline
from backend.services.batch_runner import BatchExecutionManager
from backend.services.scheduler import scheduler_service
from backend.services.wp_client import WordPressClient
from backend.services.yoast_optimizer import yoast_optimizer
from backend.services.cost_engine import (
    estimate_tokens_from_text, compute_post_cost, calculate_catalog_summary
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("publisher.api")

pipeline = PublishingPipeline()
batch_runner = BatchExecutionManager.get_instance(pipeline=pipeline)

async def seed_initial_data():
    """Seed initial managed sites, topics, and content rules if database is fresh."""
    async with AsyncSessionLocal() as session:
        # 1. Ensure Primary Site #1 (MedHealth Times) exists
        site_res = await session.execute(select(ManagedSite).where(ManagedSite.id == 1))
        primary_site = site_res.scalars().first()
        if not primary_site:
            primary_site = ManagedSite(
                id=1,
                name="MedHealth Times",
                slug="medhealthtimes",
                wp_url=settings.WORDPRESS_URL,
                wp_api_key=settings.WORDPRESS_API_KEY,
                description="Primary Medical & Clinical AI Journalism Publication",
                is_active=True,
                auto_push_to_wp=settings.AUTO_PUSH_TO_WP,
                is_scheduler_enabled=settings.SCHEDULER_ENABLED,
                schedule_interval_hours=settings.SCHEDULER_INTERVAL_HOURS
            )
            session.add(primary_site)
            await session.commit()
            logger.info("Seeded Primary Managed Site #1: MedHealth Times.")

        # 2. Backfill existing records missing site_id
        await session.execute(update(Topic).where(Topic.site_id == None).values(site_id=1))
        await session.execute(update(ContentRule).where(ContentRule.site_id == None).values(site_id=1))
        await session.execute(update(ResearchArticle).where(ResearchArticle.site_id == None).values(site_id=1))
        await session.execute(update(GeneratedPost).where(GeneratedPost.site_id == None).values(site_id=1))
        await session.execute(update(RunLog).where(RunLog.site_id == None).values(site_id=1, site_name="MedHealth Times"))
        await session.commit()

        # 3. Check topics
        topic_count_res = await session.execute(select(Topic))
        if not topic_count_res.scalars().first():
            default_topics = [
                Topic(
                    site_id=1,
                    name="AI in Diagnostics",
                    keywords=["medical imaging AI", "CT scan deep learning", "radiomics biomarker", "computational pathology"],
                    weight=9,
                    is_active=True,
                    domain_whitelist=["nature.com", "nejm.org", "thelancet.com", "jamanetwork.com"],
                    lookback_days=7
                ),
                Topic(
                    site_id=1,
                    name="Cardiology Breakthroughs",
                    keywords=["mRNA heart repair", "transcatheter valves", "cardiac myocyte regeneration", "heart failure clinical trial"],
                    weight=8,
                    is_active=True,
                    domain_whitelist=["nejm.org", "ahajournals.org", "acc.org", "thelancet.com"],
                    lookback_days=7
                ),
                Topic(
                    site_id=1,
                    name="FDA Drug Approvals",
                    keywords=["FDA oncology approval", "novel therapeutics", "accelerated approval", "bispecific antibody"],
                    weight=8,
                    is_active=True,
                    domain_whitelist=["fda.gov", "biopharmadive.com", "fiercebiotech.com", "reuters.com"],
                    lookback_days=14
                ),
                Topic(
                    site_id=1,
                    name="Mental Health Tech",
                    keywords=["digital phenotyping biomarkers", "psychiatric actigraphy", "depression digital therapeutics", "wearable EEG"],
                    weight=7,
                    is_active=True,
                    domain_whitelist=["jamanetwork.com", "psychiatryonline.org", "nature.com"],
                    lookback_days=14
                ),
                Topic(
                    site_id=1,
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

        # 4. Check content rules
        rule_res = await session.execute(select(ContentRule).where(ContentRule.site_id == 1))
        if not rule_res.scalars().first():
            default_rule = ContentRule(
                site_id=1,
                name="Default Clinical SEO Guidelines",
                is_active=True,
                tone="Professional & Journalistic",
                reading_level="General Public with High School Education",
                word_count_min=450,
                word_count_max=520,
                heading_structure="<h6><strong>Heading Title</strong></h6>",
                include_takeaways=False,
                include_faq=False,
                include_disclaimer=False,
                include_quotes=False,
                include_sources=True,
                disclaimer_text="Disclaimer: This article is for informational purposes only and does not constitute medical advice or formal clinical diagnosis. Consult a qualified healthcare professional before making health-related decisions.",
                style_guide_text="Maintain scientific accuracy. Avoid sensational headlines like 'miracle cure' or 'breakthrough.' Clearly specify clinical trial phases and distinguish preclinical animal data from human clinical trials.",
                auto_push_to_wp=settings.AUTO_PUSH_TO_WP
            )
            session.add(default_rule)
            logger.info("Seeded default Content Rules for Site #1.")

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
    scheduler_service.shutdown()

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
# SYSTEM HEALTH & UPTIME MONITORING
# ==============================================================================

@app.get("/api/health")
async def system_health_check():
    """Lightweight health check endpoint for Render.com and monitoring services."""
    return {
        "status": "ok",
        "service": "PulsePublish AI Multi-Site Auto-Publisher",
        "developer": settings.DEVELOPER_NAME,
        "version": settings.VERSION
    }

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
# MANAGED SITES ENDPOINTS (MULTI-SITE PUBLISHING HUB)
# ==============================================================================

@app.get("/api/sites", response_model=List[SiteResponse])
async def list_managed_sites(db: AsyncSession = Depends(get_db)):
    """List all managed websites with live topics, drafts, and published counts."""
    sites_res = await db.execute(select(ManagedSite).order_by(ManagedSite.id))
    sites = sites_res.scalars().all()
    
    response = []
    for s in sites:
        t_count = (await db.execute(select(func.count(Topic.id)).where(Topic.site_id == s.id))).scalar() or 0
        d_count = (await db.execute(select(func.count(GeneratedPost.id)).where(GeneratedPost.site_id == s.id, GeneratedPost.status == "PENDING_REVIEW"))).scalar() or 0
        p_count = (await db.execute(select(func.count(GeneratedPost.id)).where(GeneratedPost.site_id == s.id, GeneratedPost.status == "SENT_TO_WP"))).scalar() or 0
        masked_key = (s.wp_api_key[:3] + "..." + s.wp_api_key[-4:]) if len(s.wp_api_key) > 7 else "••••••••"
        
        response.append(SiteResponse(
            id=s.id,
            name=s.name,
            slug=s.slug,
            wp_url=s.wp_url,
            wp_api_key_masked=masked_key,
            description=s.description,
            is_active=s.is_active,
            auto_push_to_wp=s.auto_push_to_wp,
            is_scheduler_enabled=s.is_scheduler_enabled,
            schedule_interval_hours=s.schedule_interval_hours,
            topics_count=t_count,
            drafts_count=d_count,
            published_count=p_count,
            created_at=s.created_at,
            updated_at=s.updated_at
        ))
    return response

@app.post("/api/sites", response_model=SiteResponse, status_code=201, dependencies=[Depends(require_developer)])
async def create_managed_site(site_in: SiteCreate, db: AsyncSession = Depends(get_db)):
    """Create a new managed website for auto-publishing."""
    slug = site_in.slug or re.sub(r'[^a-z0-9]+', '-', site_in.name.lower()).strip('-')
    
    existing = await db.execute(select(ManagedSite).where(ManagedSite.slug == slug))
    if existing.scalars().first():
        slug = f"{slug}-{int(datetime.datetime.utcnow().timestamp())}"

    new_site = ManagedSite(
        name=site_in.name.strip(),
        slug=slug,
        wp_url=site_in.wp_url.strip().rstrip('/'),
        wp_api_key=site_in.wp_api_key.strip(),
        description=site_in.description,
        is_active=site_in.is_active,
        auto_push_to_wp=site_in.auto_push_to_wp,
        is_scheduler_enabled=site_in.is_scheduler_enabled,
        schedule_interval_hours=site_in.schedule_interval_hours
    )
    db.add(new_site)
    await db.commit()
    await db.refresh(new_site)
    
    # Create isolated default content rule for this site
    site_rule = ContentRule(
        site_id=new_site.id,
        name=f"Publishing Rules for {new_site.name}",
        tone="Professional & Informative",
        reading_level="General Public (Clear, Accessible)",
        word_count_min=450,
        word_count_max=520,
        heading_structure="<h6><strong>Heading Title</strong></h6>",
        disclaimer_text=f"Disclaimer: This article on {new_site.name} is for informational purposes only.",
        style_guide_text="Maintain editorial accuracy and authoritative analysis.",
        auto_push_to_wp=new_site.auto_push_to_wp,
        enforce_yoast_green=True
    )
    db.add(site_rule)
    await db.commit()

    masked_key = (new_site.wp_api_key[:3] + "..." + new_site.wp_api_key[-4:]) if len(new_site.wp_api_key) > 7 else "••••••••"
    return SiteResponse(
        id=new_site.id,
        name=new_site.name,
        slug=new_site.slug,
        wp_url=new_site.wp_url,
        wp_api_key_masked=masked_key,
        description=new_site.description,
        is_active=new_site.is_active,
        auto_push_to_wp=new_site.auto_push_to_wp,
        is_scheduler_enabled=new_site.is_scheduler_enabled,
        schedule_interval_hours=new_site.schedule_interval_hours,
        topics_count=0,
        drafts_count=0,
        published_count=0,
        created_at=new_site.created_at,
        updated_at=new_site.updated_at
    )

@app.get("/api/sites/{site_id}", response_model=SiteResponse)
async def get_managed_site(site_id: int, db: AsyncSession = Depends(get_db)):
    site = await db.get(ManagedSite, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    
    t_count = (await db.execute(select(func.count(Topic.id)).where(Topic.site_id == site.id))).scalar() or 0
    d_count = (await db.execute(select(func.count(GeneratedPost.id)).where(GeneratedPost.site_id == site.id, GeneratedPost.status == "PENDING_REVIEW"))).scalar() or 0
    p_count = (await db.execute(select(func.count(GeneratedPost.id)).where(GeneratedPost.site_id == site.id, GeneratedPost.status == "SENT_TO_WP"))).scalar() or 0
    masked_key = (site.wp_api_key[:3] + "..." + site.wp_api_key[-4:]) if len(site.wp_api_key) > 7 else "••••••••"
    
    return SiteResponse(
        id=site.id,
        name=site.name,
        slug=site.slug,
        wp_url=site.wp_url,
        wp_api_key_masked=masked_key,
        description=site.description,
        is_active=site.is_active,
        auto_push_to_wp=site.auto_push_to_wp,
        is_scheduler_enabled=site.is_scheduler_enabled,
        schedule_interval_hours=site.schedule_interval_hours,
        topics_count=t_count,
        drafts_count=d_count,
        published_count=p_count,
        created_at=site.created_at,
        updated_at=site.updated_at
    )

@app.put("/api/sites/{site_id}", response_model=SiteResponse, dependencies=[Depends(require_developer)])
async def update_managed_site(site_id: int, site_in: SiteUpdate, db: AsyncSession = Depends(get_db)):
    site = await db.get(ManagedSite, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    update_data = site_in.model_dump(exclude_unset=True)
    if "wp_url" in update_data and update_data["wp_url"]:
        update_data["wp_url"] = update_data["wp_url"].strip().rstrip('/')
    if "wp_api_key" in update_data and update_data["wp_api_key"]:
        update_data["wp_api_key"] = update_data["wp_api_key"].strip()

    for key, val in update_data.items():
        setattr(site, key, val)

    await db.commit()
    await db.refresh(site)

    t_count = (await db.execute(select(func.count(Topic.id)).where(Topic.site_id == site.id))).scalar() or 0
    d_count = (await db.execute(select(func.count(GeneratedPost.id)).where(GeneratedPost.site_id == site.id, GeneratedPost.status == "PENDING_REVIEW"))).scalar() or 0
    p_count = (await db.execute(select(func.count(GeneratedPost.id)).where(GeneratedPost.site_id == site.id, GeneratedPost.status == "SENT_TO_WP"))).scalar() or 0
    masked_key = (site.wp_api_key[:3] + "..." + site.wp_api_key[-4:]) if len(site.wp_api_key) > 7 else "••••••••"

    return SiteResponse(
        id=site.id,
        name=site.name,
        slug=site.slug,
        wp_url=site.wp_url,
        wp_api_key_masked=masked_key,
        description=site.description,
        is_active=site.is_active,
        auto_push_to_wp=site.auto_push_to_wp,
        is_scheduler_enabled=site.is_scheduler_enabled,
        schedule_interval_hours=site.schedule_interval_hours,
        topics_count=t_count,
        drafts_count=d_count,
        published_count=p_count,
        created_at=site.created_at,
        updated_at=site.updated_at
    )

@app.delete("/api/sites/{site_id}", status_code=204, dependencies=[Depends(require_developer)])
async def delete_managed_site(site_id: int, db: AsyncSession = Depends(get_db)):
    if site_id == 1:
        raise HTTPException(status_code=400, detail="The Primary Site (MedHealth Times) cannot be deleted.")
    site = await db.get(ManagedSite, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    await db.delete(site)
    await db.commit()
    return None

@app.post("/api/sites/{site_id}/test-wordpress", response_model=SiteTestResponse, dependencies=[Depends(require_developer)])
async def test_site_wordpress_connection(site_id: int, db: AsyncSession = Depends(get_db)):
    site = await db.get(ManagedSite, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")
    
    client = WordPressClient(base_url=site.wp_url, api_key=site.wp_api_key)
    res = client.check_connection()
    return SiteTestResponse(
        connected=res.get("connected", False),
        status_code=res.get("status_code", 0),
        message=res.get("message", "Connection test completed."),
        site_name=res.get("site_name"),
        plugin_version=res.get("plugin_version")
    )

@app.post("/api/sites/{site_id}/seed-presets", dependencies=[Depends(require_developer)])
async def seed_site_topic_presets(
    site_id: int,
    preset_type: str = Query("tech_ai", description="Preset category: 'tech_ai', 'finance_crypto', 'clean_energy', 'lifestyle'"),
    db: AsyncSession = Depends(get_db)
):
    site = await db.get(ManagedSite, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Website not found")

    PRESET_PACKS = {
        "tech_ai": [
            ("Generative AI & LLMs", ["large language models", "generative AI agents", "transformer architectures", "multimodal AI", "open source models"], 9),
            ("Cybersecurity & Zero Trust", ["zero trust architecture", "ransomware defense", "quantum cryptography", "cloud security vulnerabilities"], 8),
            ("Autonomous Robotics", ["humanoid robot development", "industrial autonomous robotics", "computer vision edge AI"], 7),
            ("Cloud Infrastructure", ["serverless computing", "Kubernetes orchestration", "edge computing infrastructure", "distributed systems"], 7),
            ("Quantum Computing", ["quantum supremacy algorithms", "qubit coherence error correction", "quantum annealing"], 8)
        ],
        "finance_crypto": [
            ("Decentralized Finance", ["DeFi protocols yield", "smart contract auditing", "liquid staking derivatives"], 9),
            ("Central Bank Digital Currencies", ["CBDC regulatory rollout", "cross-border digital settlement", "sovereign digital currency"], 8),
            ("Algorithmic Trading", ["high frequency trading AI", "market liquidity modeling", "quantitative arbitrage"], 7),
            ("FinTech & Open Banking", ["open banking API regulation", "embedded finance infrastructure", "neobank profitability"], 7),
            ("Crypto Asset Regulations", ["SEC crypto classification", "MiCA regulatory compliance", "spot ETF institutional flows"], 8)
        ],
        "clean_energy": [
            ("Grid-Scale Battery Storage", ["solid-state battery grid", "lithium iron phosphate storage", "flow battery renewable integration"], 9),
            ("Solar Photovoltaic Advances", ["perovskite tandem solar cells", "bifacial panel efficiency", "commercial rooftop solar"], 8),
            ("Green Hydrogen Economy", ["PEM electrolyzer efficiency", "green hydrogen industrial adoption", "clean fuel infrastructure"], 8),
            ("Next-Gen Nuclear SMRs", ["small modular reactors SMR", "molten salt nuclear safety", "nuclear fusion milestone"], 9),
            ("Electric Mobility", ["EV fast-charging infrastructure", "silicon anode battery range", "commercial fleet electrification"], 7)
        ],
        "lifestyle": [
            ("Sleep Optimization & Longevity", ["circadian rhythm optimization", "deep sleep wearable tracking", "NAD+ longevity cellular health"], 8),
            ("Nutritional Science & Gut Health", ["microbiome diversity prebiotic", "metabolic flexibility diet", "intermittent fasting biomarker"], 8),
            ("Mental Resilience & Mindfulness", ["neuroplasticity mindfulness practice", "stress cortisol biofeedback", "vagus nerve stimulation"], 7),
            ("Physical Recovery & Mobility", ["fascia release mobility training", "cold thermogenesis recovery", "zone 2 cardio mitochondrial density"], 7),
            ("Biohacking & Preventative Wellness", ["biological age epigenetic clock", "continuous biomarker tracking", "mitochondrial biogenesis wellness"], 9)
        ]
    }

    pack = PRESET_PACKS.get(preset_type, PRESET_PACKS["tech_ai"])
    created = 0
    for name, kws, weight in pack:
        exists = await db.execute(
            select(Topic).where(Topic.site_id == site_id, Topic.name == name)
        )
        if not exists.scalars().first():
            t = Topic(
                site_id=site_id,
                name=name,
                keywords=kws,
                weight=weight,
                is_active=True,
                lookback_days=7
            )
            db.add(t)
            created += 1
    await db.commit()
    return {"success": True, "created_topics_count": created, "preset": preset_type, "site_name": site.name}

# ==============================================================================
# TOPICS ENDPOINTS
# ==============================================================================

@app.get("/api/topics", response_model=List[TopicResponse])
async def list_topics(site_id: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    stmt = select(Topic)
    if site_id is not None:
        stmt = stmt.where(Topic.site_id == site_id)
    stmt = stmt.order_by(desc(Topic.weight), Topic.name)
    result = await db.execute(stmt)
    topics = result.scalars().all()

    site_cache = {}
    response = []
    for t in topics:
        sid = t.site_id or 1
        if sid not in site_cache:
            s = await db.get(ManagedSite, sid)
            site_cache[sid] = s.name if s else "MedHealth Times"
        t_dict = TopicResponse.model_validate(t).model_dump()
        t_dict["site_name"] = site_cache[sid]
        response.append(t_dict)
    return response

@app.post("/api/topics", response_model=TopicResponse, status_code=201, dependencies=[Depends(require_developer)])
async def create_topic(topic_in: TopicCreate, db: AsyncSession = Depends(get_db)):
    target_site_id = topic_in.site_id or 1
    # Check duplicate name within this specific site
    existing = await db.execute(
        select(Topic).where(Topic.site_id == target_site_id, Topic.name == topic_in.name)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"A topic category with name '{topic_in.name}' already exists on this website.")

    topic_data = topic_in.model_dump()
    topic_data["site_id"] = target_site_id
    topic = Topic(**topic_data)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)

    site = await db.get(ManagedSite, target_site_id)
    t_dict = TopicResponse.model_validate(topic).model_dump()
    t_dict["site_name"] = site.name if site else "MedHealth Times"
    return t_dict

@app.get("/api/topics/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    sid = topic.site_id or 1
    site = await db.get(ManagedSite, sid)
    t_dict = TopicResponse.model_validate(topic).model_dump()
    t_dict["site_name"] = site.name if site else "MedHealth Times"
    return t_dict

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
    
    sid = topic.site_id or 1
    site = await db.get(ManagedSite, sid)
    t_dict = TopicResponse.model_validate(topic).model_dump()
    t_dict["site_name"] = site.name if site else "MedHealth Times"
    return t_dict

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
    """
    created_topics = []
    target_site_id = payload.site_id or 1
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

        existing = await db.execute(
            select(Topic).where(Topic.site_id == target_site_id, Topic.name == name)
        )
        topic = existing.scalars().first()
        if topic:
            current_kws = set(topic.keywords or [])
            current_kws.update(keywords)
            topic.keywords = list(current_kws)
            created_topics.append(topic)
        else:
            topic = Topic(
                site_id=target_site_id,
                name=name,
                keywords=keywords,
                weight=5,
                is_active=True,
                lookback_days=7
            )
            db.add(topic)
            created_topics.append(topic)

    await db.commit()
    
    site = await db.get(ManagedSite, target_site_id)
    site_name = site.name if site else "MedHealth Times"
    
    response = []
    for t in created_topics:
        await db.refresh(t)
        t_dict = TopicResponse.model_validate(t).model_dump()
        t_dict["site_name"] = site_name
        response.append(t_dict)

    return response

# ==============================================================================
# CONTENT RULES & SEO ENDPOINTS (SITE ISOLATED)
# ==============================================================================

@app.get("/api/content-rules", response_model=ContentRuleResponse)
async def get_content_rules(site_id: Optional[int] = Query(1), db: AsyncSession = Depends(get_db)):
    target_site_id = site_id or 1
    result = await db.execute(
        select(ContentRule).where(ContentRule.site_id == target_site_id, ContentRule.is_active == True)
    )
    rule = result.scalars().first()
    if not rule:
        site = await db.get(ManagedSite, target_site_id)
        site_title = site.name if site else f"Site #{target_site_id}"
        rule = ContentRule(
            site_id=target_site_id,
            name=f"Publishing Rules for {site_title}",
            tone="Professional & Informative",
            reading_level="General Public (Clear, Accessible)",
            word_count_min=450,
            word_count_max=520,
            heading_structure="<h6><strong>Heading Title</strong></h6>",
            disclaimer_text=f"Disclaimer: This article on {site_title} is for informational purposes only.",
            style_guide_text="Maintain editorial accuracy and authoritative analysis."
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return rule

@app.put("/api/content-rules", response_model=ContentRuleResponse, dependencies=[Depends(require_developer)])
async def update_content_rules(
    rules_in: ContentRuleUpdate,
    site_id: Optional[int] = Query(1),
    db: AsyncSession = Depends(get_db)
):
    target_site_id = site_id or 1
    result = await db.execute(
        select(ContentRule).where(ContentRule.site_id == target_site_id, ContentRule.is_active == True)
    )
    rule = result.scalars().first()
    if not rule:
        rule = ContentRule(site_id=target_site_id)
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
    Trigger a run immediately for a specific topic, or all active topics of a site.
    When topic_id is None, triggers an asynchronous batch run across ALL active topics
    belonging strictly to the target website.
    """
    if payload.topic_id:
        topic = await db.get(Topic, payload.topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        background_tasks.add_task(run_pipeline_task, payload.topic_id, payload.force_fresh_search)
        return {"status": "queued", "message": f"Run queued for topic: {topic.name}"}
    else:
        target_site_id = payload.site_id or 1
        res = await batch_runner.start_batch(
            site_id=target_site_id,
            force_fresh_search=payload.force_fresh_search
        )
        if not res.get("success") and not res.get("already_running"):
            raise HTTPException(status_code=400, detail=res.get("message", "No active topics found for this selection."))

        return {
            "status": "started" if res.get("success") else "already_running",
            "message": res.get("message"),
            "total_topics": res.get("total_topics", 0),
            "site_id": target_site_id,
            "site_name": res.get("site_name", "MedHealth Times"),
            "batch_status": res.get("status")
        }

@app.get("/api/runs/batch-status")
async def get_batch_status():
    """
    Returns real-time progress, currently executing topic, and completion statistics
    for the active background batch publishing pipeline.
    """
    return batch_runner.get_status()

@app.post("/api/runs/batch-cancel", dependencies=[Depends(require_developer)])
async def cancel_batch_run():
    """
    Gracefully halts an active background batch execution after the currently processing topic completes.
    """
    res = await batch_runner.cancel_batch()
    return res

@app.get("/api/runs/history", response_model=List[RunLogResponse])
async def get_run_history(
    site_id: Optional[int] = Query(None),
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(RunLog)
    if site_id is not None:
        stmt = stmt.where(RunLog.site_id == site_id)
    stmt = stmt.order_by(desc(RunLog.started_at)).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    
    response = []
    for l in logs:
        l_dict = RunLogResponse.model_validate(l).model_dump()
        if not l_dict.get("total_tokens") or not l_dict.get("cost_breakdown"):
            t_stats = estimate_tokens_from_text()
            c_data = compute_post_cost(
                prompt_tokens=t_stats["prompt_tokens"],
                completion_tokens=t_stats["completion_tokens"],
                search_queries=1
            )
            l_dict["prompt_tokens"] = c_data["prompt_tokens"]
            l_dict["completion_tokens"] = c_data["completion_tokens"]
            l_dict["total_tokens"] = c_data["total_tokens"]
            l_dict["estimated_cost"] = c_data["total_cost_usd"]
            l_dict["cost_breakdown"] = c_data
        response.append(l_dict)
    return response

@app.get("/api/runs/{run_id}", response_model=RunLogResponse)
async def get_run_detail(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RunLog).where(RunLog.run_id == run_id))
    log_entry = result.scalars().first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Run log not found")
    l_dict = RunLogResponse.model_validate(log_entry).model_dump()
    if not l_dict.get("total_tokens") or not l_dict.get("cost_breakdown"):
        t_stats = estimate_tokens_from_text()
        c_data = compute_post_cost(
            prompt_tokens=t_stats["prompt_tokens"],
            completion_tokens=t_stats["completion_tokens"],
            search_queries=1
        )
        l_dict["prompt_tokens"] = c_data["prompt_tokens"]
        l_dict["completion_tokens"] = c_data["completion_tokens"]
        l_dict["total_tokens"] = c_data["total_tokens"]
        l_dict["estimated_cost"] = c_data["total_cost_usd"]
        l_dict["cost_breakdown"] = c_data
    return l_dict

# ==============================================================================
# DRAFTS & EDITORIAL QUEUE
# ==============================================================================

@app.get("/api/drafts", response_model=List[GeneratedPostResponse])
async def list_drafts(
    status: Optional[str] = None,
    site_id: Optional[int] = Query(None),
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    query = select(GeneratedPost)
    if status:
        query = query.where(GeneratedPost.status == status)
    if site_id is not None:
        query = query.where(GeneratedPost.site_id == site_id)
    query = query.order_by(desc(GeneratedPost.created_at)).limit(limit)
    result = await db.execute(query)
    posts = result.scalars().all()

    site_cache = {}
    response = []
    for p in posts:
        sid = p.site_id or 1
        if sid not in site_cache:
            s = await db.get(ManagedSite, sid)
            site_cache[sid] = s.name if s else "MedHealth Times"
        p_dict = GeneratedPostResponse.model_validate(p).model_dump()
        p_dict["site_name"] = site_cache[sid]
        
        # Enrich legacy drafts without token stats
        if not p_dict.get("total_tokens") or not p_dict.get("cost_breakdown"):
            t_stats = estimate_tokens_from_text(body_text=p.body_html)
            c_data = compute_post_cost(
                prompt_tokens=t_stats["prompt_tokens"],
                completion_tokens=t_stats["completion_tokens"],
                search_queries=1
            )
            p_dict["prompt_tokens"] = c_data["prompt_tokens"]
            p_dict["completion_tokens"] = c_data["completion_tokens"]
            p_dict["total_tokens"] = c_data["total_tokens"]
            p_dict["estimated_cost"] = c_data["total_cost_usd"]
            p_dict["cost_breakdown"] = c_data
        response.append(p_dict)
    return response

@app.get("/api/drafts/{post_id}", response_model=GeneratedPostResponse)
async def get_draft(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(GeneratedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Draft not found")
    sid = post.site_id or 1
    site = await db.get(ManagedSite, sid)
    p_dict = GeneratedPostResponse.model_validate(post).model_dump()
    p_dict["site_name"] = site.name if site else "MedHealth Times"
    
    if not p_dict.get("total_tokens") or not p_dict.get("cost_breakdown"):
        t_stats = estimate_tokens_from_text(body_text=post.body_html)
        c_data = compute_post_cost(
            prompt_tokens=t_stats["prompt_tokens"],
            completion_tokens=t_stats["completion_tokens"],
            search_queries=1
        )
        p_dict["prompt_tokens"] = c_data["prompt_tokens"]
        p_dict["completion_tokens"] = c_data["completion_tokens"]
        p_dict["total_tokens"] = c_data["total_tokens"]
        p_dict["estimated_cost"] = c_data["total_cost_usd"]
        p_dict["cost_breakdown"] = c_data
    return p_dict

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

    elif act == "delete":
        await db.delete(post)
        await db.commit()
        return {"success": True, "message": f"Draft #{post_id} deleted successfully."}

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
        post.body_html = clean_semantic_post_html(new_data.get("body_html", post.body_html))
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

@app.delete("/api/drafts/{post_id}", dependencies=[Depends(require_developer)])
async def delete_draft_endpoint(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(GeneratedPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(post)
    await db.commit()
    return {"success": True, "message": f"Draft #{post_id} deleted successfully."}

@app.post("/api/drafts/bulk-delete", response_model=DraftBulkDeleteResponse, dependencies=[Depends(require_developer)])
async def bulk_delete_drafts(
    payload: DraftBulkDeleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk deletes drafts by either:
    1. An explicit list of post_ids
    2. delete_all = True (optionally filtered by status, e.g. DUPLICATE_FLAGGED, REJECTED, or ALL)
    """
    if payload.delete_all:
        stmt = delete(GeneratedPost)
        if payload.status and payload.status != "ALL":
            stmt = stmt.where(GeneratedPost.status == payload.status)
        result = await db.execute(stmt)
        await db.commit()
        count = result.rowcount or 0
        return DraftBulkDeleteResponse(
            success=True,
            deleted_count=count,
            message=f"Successfully deleted {count} draft(s)."
        )
    elif payload.post_ids:
        stmt = delete(GeneratedPost).where(GeneratedPost.id.in_(payload.post_ids))
        result = await db.execute(stmt)
        await db.commit()
        count = result.rowcount or 0
        return DraftBulkDeleteResponse(
            success=True,
            deleted_count=count,
            message=f"Successfully deleted {count} draft(s)."
        )
    else:
        raise HTTPException(status_code=400, detail="Must provide post_ids or set delete_all=True.")

@app.post("/api/drafts/bulk-push", dependencies=[Depends(require_developer)])
async def bulk_push_drafts(
    payload: DraftBulkPushRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Pushes multiple approved drafts to WordPress in batch.
    Allows pushing selected IDs, or all pending/approved drafts for a specific site.
    """
    if payload.post_ids:
        stmt = select(GeneratedPost).where(GeneratedPost.id.in_(payload.post_ids))
    elif payload.all_pending:
        stmt = select(GeneratedPost).where(
            GeneratedPost.status.in_(["PENDING_REVIEW", "APPROVED"])
        )
        if payload.site_id:
            stmt = stmt.where(GeneratedPost.site_id == payload.site_id)
    else:
        raise HTTPException(status_code=400, detail="Must provide post_ids or set all_pending=true.")

    result = await db.execute(stmt)
    posts = result.scalars().all()
    if not posts:
        return {
            "success": True,
            "pushed_count": 0,
            "failed_count": 0,
            "message": "No matching drafts found to push."
        }

    pushed = []
    failed = []
    for post in posts:
        res = await pipeline.push_draft_to_wordpress(db, post.id)
        if res.get("success"):
            pushed.append({
                "id": post.id,
                "title": post.title,
                "wp_post_id": res.get("wp_post_id"),
                "edit_url": res.get("edit_url")
            })
        else:
            failed.append({
                "id": post.id,
                "title": post.title,
                "error": res.get("error")
            })

    return {
        "success": True,
        "pushed_count": len(pushed),
        "failed_count": len(failed),
        "pushed": pushed,
        "failed": failed,
        "message": f"Bulk push completed: {len(pushed)} successfully sent to WordPress, {len(failed)} failed."
    }

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
        scheduler_interval_hours=settings.SCHEDULER_INTERVAL_HOURS,
        cost_currency=settings.COST_CURRENCY,
        cost_exchange_rate=settings.COST_EXCHANGE_RATE,
        cost_prompt_per_1m=settings.COST_PROMPT_PER_1M,
        cost_completion_per_1m=settings.COST_COMPLETION_PER_1M,
        cost_per_search_query=settings.COST_PER_SEARCH_QUERY,
        cost_manual_override_enabled=settings.COST_MANUAL_OVERRIDE_ENABLED,
        cost_fixed_per_post=settings.COST_FIXED_PER_POST
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
    
    # Token Economics & Cost Analytics updates
    if payload.cost_currency is not None and payload.cost_currency.strip():
        settings.COST_CURRENCY = payload.cost_currency.strip().upper()
    if payload.cost_exchange_rate is not None and payload.cost_exchange_rate > 0:
        settings.COST_EXCHANGE_RATE = float(payload.cost_exchange_rate)
    if payload.cost_prompt_per_1m is not None and payload.cost_prompt_per_1m >= 0:
        settings.COST_PROMPT_PER_1M = float(payload.cost_prompt_per_1m)
    if payload.cost_completion_per_1m is not None and payload.cost_completion_per_1m >= 0:
        settings.COST_COMPLETION_PER_1M = float(payload.cost_completion_per_1m)
    if payload.cost_per_search_query is not None and payload.cost_per_search_query >= 0:
        settings.COST_PER_SEARCH_QUERY = float(payload.cost_per_search_query)
    if payload.cost_manual_override_enabled is not None:
        settings.COST_MANUAL_OVERRIDE_ENABLED = bool(payload.cost_manual_override_enabled)
    if payload.cost_fixed_per_post is not None and payload.cost_fixed_per_post >= 0:
        settings.COST_FIXED_PER_POST = float(payload.cost_fixed_per_post)
        if payload.cost_manual_override_enabled is None:
            settings.COST_MANUAL_OVERRIDE_ENABLED = True

    return await get_settings()

# ==============================================================================
# TOKEN ECONOMICS & COST ANALYTICS ENDPOINTS
# ==============================================================================

@app.get("/api/analytics/cost-summary", response_model=CostAnalyticsSummaryResponse)
async def get_cost_analytics_summary(
    currency: Optional[str] = Query(None),
    site_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns global API and token economics summary:
    - Cost per single post run with 3-stage breakdown
    - Cost for full catalog run (all configured topics)
    - Projections (daily, monthly, vs traditional agency)
    """
    topics_query = select(func.count(Topic.id))
    active_query = select(func.count(Topic.id)).where(Topic.is_active == True)
    if site_id is not None:
        topics_query = topics_query.where(Topic.site_id == site_id)
        active_query = active_query.where(Topic.site_id == site_id)

    total_topics = (await db.execute(topics_query)).scalar() or 0
    active_topics = (await db.execute(active_query)).scalar() or 0

    return calculate_catalog_summary(
        total_topics_count=total_topics,
        active_topics_count=active_topics,
        custom_currency=currency
    )

@app.get("/api/topics/{topic_id}/cost-breakdown", response_model=CostBreakdownResponse)
async def get_topic_cost_breakdown(
    topic_id: int,
    currency: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns authentic 3-stage token & money breakdown for executing this specific topic.
    """
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic category not found")

    search_queries = len(topic.keywords) if topic.keywords else 1
    sample_tokens = estimate_tokens_from_text(research_count=min(4, max(2, search_queries)))
    return compute_post_cost(
        prompt_tokens=sample_tokens["prompt_tokens"],
        completion_tokens=sample_tokens["completion_tokens"],
        search_queries=search_queries,
        custom_currency=currency
    )

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
    plugin_zip_path = BASE_DIR.parent / "wp-plugin" / "pulse-content-sync.zip"
    if not plugin_zip_path.exists():
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



