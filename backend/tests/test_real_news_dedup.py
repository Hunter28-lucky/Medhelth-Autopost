import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.free_search_provider import FreeOnlineSearchProvider
from backend.services.research_engine import ResearchEngine
from backend.services.dedup_engine import DeduplicationEngine
from backend.services.pipeline import PublishingPipeline
from backend.models import Topic, ContentRule, GeneratedPost, ResearchArticle

@pytest.mark.asyncio
async def test_pubmed_eutilities_real_news():
    """Verify FreeOnlineSearchProvider connects to PubMed and retrieves real clinical research."""
    provider = FreeOnlineSearchProvider()
    results = provider._search_pubmed_clinical("endoscopy AI", max_per_query=2)
    assert len(results) > 0
    article = results[0]
    assert "title" in article and len(article["title"]) > 10
    assert "source" in article and len(article["source"]) > 0
    assert "url" in article and article["url"].startswith("http")
    assert "snippet" in article and len(article["snippet"]) > 20
    assert article.get("is_peer_reviewed") is True

@pytest.mark.asyncio
async def test_research_engine_zero_synthetic_text():
    """Verify ResearchEngine never outputs generic synthetic text."""
    engine = ResearchEngine(search_provider_name="mock")
    res = engine.extract_article_text("https://example.com/clinical-paper", fallback_snippet="In a prospective trial of 500 patients, diagnostic sensitivity reached 94.2% (p < 0.001).")
    assert "synthetic_grounded" not in res["extraction_method"]
    assert "In a prospective trial of 500 patients" in res["text"]
    assert "In a multi-center randomized cohort evaluation, investigators evaluated therapeutic efficacy" not in res["text"]

    # Test key claims extraction on genuine clinical metrics
    claims = engine.extract_key_claims(res["text"])
    assert len(claims) > 0
    assert any("94.2%" in c or "p < 0.001" in c for c in claims)

@pytest.mark.asyncio
async def test_strict_zero_overlap_pre_dedup(test_session: AsyncSession):
    """Verify DeduplicationEngine rejects 70% similar headlines and token overlap."""
    dedup = DeduplicationEngine(threshold=0.70)
    
    # Add an existing post
    p = GeneratedPost(
        title="Benefit of Linked-Color Imaging in AI Endoscopy Trials",
        slug="benefit-linked-color-imaging",
        body_html="<p>Test body</p>",
        status="APPROVED"
    )
    test_session.add(p)
    await test_session.commit()

    # 1. Test 70%+ sequence similarity
    candidate_titles = ["Benefit of Linked-Color Imaging in AI Clinical Endoscopy"]
    is_dup, reason = await dedup.check_pre_generation_duplicate(test_session, [], candidate_titles)
    assert is_dup is True
    assert "similar to past post" in reason or "shares" in reason

    # 2. Test completely distinct story passes
    candidate_distinct = ["Novel CAR-T Cell Therapy Shows High Response in Multiple Myeloma"]
    is_dup_distinct, _ = await dedup.check_pre_generation_duplicate(test_session, [], candidate_distinct)
    assert is_dup_distinct is False
