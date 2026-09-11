import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.database import Base
from backend.models import Topic, ContentRule, GeneratedPost
from backend.services.search_providers import MockSearchProvider
from backend.services.research_engine import ResearchEngine
from backend.services.dedup_engine import DeduplicationEngine
from backend.services.generator_engine import ContentGenerator
from backend.services.wp_client import WordPressClient
from backend.services.pipeline import PublishingPipeline

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_search_provider():
    provider = MockSearchProvider()
    results = await provider.search(queries=["diagnostics", "radiology"], max_results=2)
    assert len(results) > 0
    assert "url" in results[0]
    assert "title" in results[0]

@pytest.mark.asyncio
async def test_research_engine_extraction():
    engine = ResearchEngine(search_provider_name="mock")
    # Avoid live robots.txt network check during unit test by setting mock host
    engine.robots_cache["https://www.nature.com"] = type("MockRobots", (), {"can_fetch": lambda *a: True})()
    articles = await engine.execute_research(
        topic_name="AI in Diagnostics",
        keywords=["medical imaging AI"],
        max_articles=2
    )
    assert len(articles) > 0
    assert "url_hash" in articles[0]
    assert len(articles[0]["full_text"]) > 100
    assert isinstance(articles[0]["key_claims"], list)

@pytest.mark.asyncio
async def test_deduplication_engine(test_session: AsyncSession):
    dedup = DeduplicationEngine(threshold=0.80)

    # 1. Clean HTML
    html = "<p>Hello <strong>World</strong>!</p>"
    assert dedup.clean_html(html) == "hello world!"

    # 2. Test empty historical corpus returns 0.0
    res = await dedup.check_post_generation_similarity(test_session, "<p>Initial novel article about neurology.</p>")
    assert res["is_duplicate"] is False
    assert res["max_score"] == 0.0

    # 3. Add a baseline post to database
    base_text = (
        "In a multi-center clinical study published today, researchers evaluated an open-weights "
        "foundation model that achieves high diagnostic sensitivity in chest CT screening across diverse hospitals."
    )
    post1 = GeneratedPost(
        title="FDA Clears Chest CT AI Model",
        slug="fda-clears-chest-ct-ai-model",
        body_html=f"<p>{base_text}</p>",
        status="APPROVED"
    )
    test_session.add(post1)
    await test_session.commit()

    # 4. Compare near-identical text (should exceed threshold)
    near_identical = (
        "<p>In a multi-center clinical study published today, researchers evaluated an open-weights "
        "foundation model achieving high diagnostic sensitivity in chest CT screening across diverse hospital networks.</p>"
    )
    res_dup = await dedup.check_post_generation_similarity(test_session, near_identical)
    assert res_dup["is_duplicate"] is True
    assert res_dup["max_score"] >= 0.80
    assert res_dup["matched_post_id"] == post1.id

    # 5. Compare completely different article (should pass)
    different_text = (
        "<p>New pediatric psychiatric digital biomarkers assess sleep disturbance actigraphy "
        "and speech patterns to predict depression cycles.</p>"
    )
    res_unique = await dedup.check_post_generation_similarity(test_session, different_text)
    assert res_unique["is_duplicate"] is False
    assert res_unique["max_score"] < 0.40

@pytest.mark.asyncio
async def test_content_generator():
    gen = ContentGenerator(openrouter_api_key="", anthropic_api_key="")
    rules = ContentRule(
        tone="Professional",
        word_count_min=500,
        word_count_max=900,
        disclaimer_text="Test disclaimer notice"
    )
    research = [{
        "title": "Novel Cardiac Repair",
        "url": "https://example.com/cardiac",
        "source": "NEJM",
        "source_domain": "example.com",
        "key_claims": ["14.8% ejection fraction improvement"],
        "full_text": "Study of lipid nanoparticle mRNA delivery in myocardial infarction."
    }]

    draft = await gen.generate_draft("Cardiology Breakthroughs", research, rules)
    assert "title" in draft
    assert "body_html" in draft
    assert "key_takeaways" in draft
    assert "meta_title" in draft
    assert len(draft["body_html"]) > 100
    assert "Test disclaimer notice" in draft["disclaimer"]

def test_wp_client_headers():
    client = WordPressClient(base_url="https://mysite.com", api_key="secret-key-123")
    headers = client.get_headers()
    assert headers["X-WP-AI-Key"] == "secret-key-123"
    assert headers["Content-Type"] == "application/json"

@pytest.mark.asyncio
async def test_pipeline_execution(test_session: AsyncSession):
    topic = Topic(
        name="AI in Diagnostics",
        keywords=["imaging AI"],
        weight=9,
        is_active=True,
        lookback_days=7
    )
    test_session.add(topic)
    rule = ContentRule(is_active=True, auto_push_to_wp=False)
    test_session.add(rule)
    await test_session.commit()

    pipeline = PublishingPipeline()
    pipeline.generator = ContentGenerator(openrouter_api_key="", anthropic_api_key="")
    pipeline.research_engine.robots_cache["https://www.nature.com"] = type("MockRobots", (), {"can_fetch": lambda *a: True})()
    result = await pipeline.execute_run_for_topic(
        session=test_session,
        topic_id=topic.id,
        trigger_type="MANUAL"
    )
    assert result["success"] is True
    assert "post_id" in result
    assert result["status"] == "PENDING_REVIEW"

@pytest.mark.asyncio
async def test_single_and_bulk_delete(test_session: AsyncSession):
    # 1. Create test posts
    p1 = GeneratedPost(
        title="Draft Delete Test 1",
        slug="draft-delete-test-1",
        body_html="<p>Sample</p>",
        similarity_score=0.1,
        similarity_status="UNIQUE",
        status="PENDING_REVIEW"
    )
    p2 = GeneratedPost(
        title="Draft Delete Test 2",
        slug="draft-delete-test-2",
        body_html="<p>Sample</p>",
        similarity_score=0.9,
        similarity_status="DUPLICATE_FLAGGED",
        status="DUPLICATE_FLAGGED"
    )
    p3 = GeneratedPost(
        title="Draft Delete Test 3",
        slug="draft-delete-test-3",
        body_html="<p>Sample</p>",
        similarity_score=0.9,
        similarity_status="DUPLICATE_FLAGGED",
        status="DUPLICATE_FLAGGED"
    )
    test_session.add_all([p1, p2, p3])
    await test_session.commit()
    await test_session.refresh(p1)
    await test_session.refresh(p2)
    await test_session.refresh(p3)

    # 2. Test single delete
    await test_session.delete(p1)
    await test_session.commit()
    check_p1 = await test_session.get(GeneratedPost, p1.id)
    assert check_p1 is None

    # 3. Test bulk delete by IDs
    from sqlalchemy import delete
    stmt = delete(GeneratedPost).where(GeneratedPost.id.in_([p2.id, p3.id]))
    res = await test_session.execute(stmt)
    await test_session.commit()
    assert res.rowcount == 2

@pytest.mark.asyncio
async def test_scheduler_lifecycle():
    from backend.services.scheduler import PublishingScheduler
    sched = PublishingScheduler()
    sched.start(interval_hours=2)
    assert sched.is_running is True
    sched.stop()
    assert sched.is_running is False
    # Re-starting should succeed without SchedulerAlreadyRunningError
    sched.start(interval_hours=2)
    assert sched.is_running is True
    sched.shutdown()
    assert sched.is_running is False
