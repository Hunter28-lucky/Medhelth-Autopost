import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.database import engine, AsyncSessionLocal
from backend.models import ManagedSite, Topic, ContentRule, GeneratedPost
from backend.services.free_search_provider import FreeOnlineSearchProvider
from backend.services.generator_engine import ContentGenerator
from backend.services.yoast_optimizer import yoast_optimizer
from backend.services.dedup_engine import DeduplicationEngine
from backend.services.pipeline import PublishingPipeline
from backend.services.wp_client import WordPressClient


def test_1_search_query_routing():
    print("[1/5] Testing Search Query Isolation & Routing...", flush=True)
    hr_queries = [
        "AI in HR",
        "Applicant Tracking Systems",
        "Recruitment Process Outsourcing",
        "Human Capital Management",
        "Compensation Management",
        "Employee Onboarding"
    ]
    med_queries = [
        "Cardiology Clinical Trials",
        "Oncology FDA Approval",
        "Neurosurgery Innovations"
    ]
    for q in hr_queries:
        assert FreeOnlineSearchProvider._is_hr_workforce_query(q) is True, f"Failed to identify HR query: {q}"
    for q in med_queries:
        assert FreeOnlineSearchProvider._is_hr_workforce_query(q) is False, f"Incorrectly marked clinical query as HR: {q}"
    print("  -> PASS: HR queries correctly routed to HR search; clinical queries untouched.", flush=True)


def test_2_sandbox_generator_and_yoast():
    print("[2/5] Testing HR Content Generator & Yoast SEO Scores...", flush=True)
    gen = ContentGenerator()
    rule = ContentRule(
        site_id=2,
        name="Publishing Rules for The HR Review",
        disclaimer_text="Notice: Information provided is for workplace strategy and management insights only."
    )
    draft = gen._generate_sandbox_draft(
        topic_name="Applicant Tracking Systems",
        research_articles=[{"title": "ATS Innovations", "summary": "New AI algorithms streamline candidate resume filtering."}],
        rules=rule,
        site_name="The HR Review"
    )
    assert "Applicant Tracking Systems" in draft["title"]
    assert "<h6><strong>" in draft["body_html"]
    
    # Check no medical terms leaked into HR article
    forbidden_terms = ["patient", "clinical trial", "hospital", "diagnosis", "pathology", "oncology"]
    for term in forbidden_terms:
        assert term not in draft["body_html"].lower(), f"Medical term '{term}' leaked into HR article!"

    audit = yoast_optimizer.analyze_full_post(draft)
    assert audit["seo_score"] >= 80, f"Yoast SEO score too low: {audit['seo_score']}"
    assert audit["readability_score"] >= 80, f"Yoast Readability score too low: {audit['readability_score']}"
    print(f"  -> PASS: Yoast SEO={audit['seo_score']}/100, Readability={audit['readability_score']}/100 (100% Green). Zero medical leakage.", flush=True)


async def test_3_database_live_state():
    print("[3/5] Testing Live SQLite Database (publisher.db)...", flush=True)
    async with AsyncSessionLocal() as session:
        # Check Sites
        res = await session.execute(select(ManagedSite).order_by(ManagedSite.id))
        sites = res.scalars().all()
        assert len(sites) >= 2, f"Expected at least 2 sites, found {len(sites)}"
        site1 = sites[0]
        site2 = sites[1]
        assert site1.id == 1 and site1.slug == "medhealthtimes", f"Site 1 mismatch: {site1.name}"
        assert site2.id == 2 and site2.slug == "thehrreview", f"Site 2 mismatch: {site2.name}"
        assert site2.wp_url == "https://thehrreview.com", f"Site 2 URL mismatch: {site2.wp_url}"

        # Check Site 2 Topics (60 categories)
        res = await session.execute(select(Topic).where(Topic.site_id == 2))
        hr_topics = res.scalars().all()
        assert len(hr_topics) == 60, f"Expected 60 HR categories on Site 2, found {len(hr_topics)}"

        # Check Site 1 Topics
        res = await session.execute(select(Topic).where(Topic.site_id == 1))
        med_topics = res.scalars().all()
        assert len(med_topics) == 69, f"Expected 69 topics on Site 1, found {len(med_topics)}"

        # Check Content Rules
        res = await session.execute(select(ContentRule).where(ContentRule.site_id == 2))
        hr_rule = res.scalars().first()
        assert hr_rule is not None, "ContentRule for Site 2 not found"
        assert "The HR Review" in hr_rule.name

    print(f"  -> PASS: Site 1 (MedHealth Times, 69 topics), Site 2 (The HR Review, 60 topics) verified in publisher.db.", flush=True)


async def test_4_cross_site_dedup_isolation():
    print("[4/5] Testing Cross-Site Deduplication Isolation (Zero Collision)...", flush=True)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    from backend.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mem_session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with mem_session_factory() as session:
        # Create identical headline on Site 1
        p1 = GeneratedPost(
            site_id=1,
            title="Future of AI in Talent Management",
            body_html="<p>Hospital management AI systems.</p>",
            slug="future-of-ai-in-talent-management",
            status="SENT_TO_WP"
        )
        session.add(p1)
        await session.commit()

        # Check pre-generation dedup for Site 2 with same headline
        dedup = DeduplicationEngine()
        is_dup, reason = await dedup.check_pre_generation_duplicate(
            session=session,
            candidate_urls=["https://example.com/unique-url-hr"],
            candidate_titles=["Future of AI in Talent Management"],
            site_id=2
        )
        assert is_dup is False, f"Site 2 candidate collided with Site 1 post: {reason}"

    await engine.dispose()
    print("  -> PASS: Deduplication strictly isolated per site. Identical headlines across sites do not collide.", flush=True)


async def test_5_wordpress_push_routing():
    print("[5/5] Testing WordPress Push Isolation...", flush=True)
    captured_urls = []

    def mock_submit_draft_post(self, payload, max_retries=3):
        captured_urls.append(self.base_url)
        return {
            "success": True,
            "wp_post_id": 999,
            "edit_url": f"{self.base_url}/wp-admin/post.php?post=999"
        }

    # Monkeypatch
    orig_push = WordPressClient.submit_draft_post
    WordPressClient.submit_draft_post = mock_submit_draft_post

    try:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        from backend.database import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        mem_session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with mem_session_factory() as session:
            s1 = ManagedSite(id=1, name="MedHealth Times", slug="medhealthtimes", wp_url="http://medhealthtimes.com", wp_api_key="k1")
            s2 = ManagedSite(id=2, name="The HR Review", slug="thehrreview", wp_url="https://thehrreview.com", wp_api_key="k2")
            p2 = GeneratedPost(
                site_id=2,
                title="AI in HR Recruitment Systems",
                body_html="<p>Streamlined hiring workflows.</p>",
                slug="ai-in-hr-recruitment-systems",
                status="PENDING_REVIEW"
            )
            session.add_all([s1, s2, p2])
            await session.commit()
            await session.refresh(p2)

            pipeline = PublishingPipeline()
            res = await pipeline.push_draft_to_wordpress(session, p2.id)
            assert res["success"] is True
            assert len(captured_urls) == 1
            assert captured_urls[0] == "https://thehrreview.com", f"Post for Site 2 pushed to wrong URL: {captured_urls[0]}"
    finally:
        WordPressClient.submit_draft_post = orig_push

    await engine.dispose()
    print("  -> PASS: WordPress drafts for Site 2 route exclusively to https://thehrreview.com (never Site 1).", flush=True)


async def main():
    print("=================================================================", flush=True)
    print("   VERIFICATION SUITE: 'The HR Review' MULTI-SITE INTEGRATION    ", flush=True)
    print("=================================================================", flush=True)
    test_1_search_query_routing()
    test_2_sandbox_generator_and_yoast()
    await test_3_database_live_state()
    await test_4_cross_site_dedup_isolation()
    await test_5_wordpress_push_routing()
    print("=================================================================", flush=True)
    print("   ALL 5 VERIFICATION SUITES PASSED FLAWLESSLY!                  ", flush=True)
    print("=================================================================", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
