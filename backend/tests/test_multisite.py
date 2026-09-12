import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ManagedSite, Topic, ContentRule, GeneratedPost, RunLog
from backend.services.pipeline import PublishingPipeline
from backend.services.wp_client import WordPressClient

@pytest.mark.asyncio
async def test_managed_site_creation_and_primary_site(test_session: AsyncSession):
    # Seed primary site #1 (MedHealth Times)
    site1 = ManagedSite(
        id=1,
        name="MedHealth Times",
        slug="medhealthtimes",
        wp_url="http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes",
        wp_api_key="k60pRp6jNGAf9CdjexXHfsofXGqzlyoq",
        description="Primary Medical & Clinical AI Journalism",
        is_active=True,
        auto_push_to_wp=False
    )
    test_session.add(site1)

    # Add secondary site #2 (TechPulse AI)
    site2 = ManagedSite(
        name="TechPulse AI",
        slug="techpulse",
        wp_url="https://techpulse.example.com",
        wp_api_key="tech-pulse-secret-key-456",
        description="Enterprise Artificial Intelligence & Cloud Security",
        is_active=True,
        auto_push_to_wp=True
    )
    test_session.add(site2)
    await test_session.commit()
    await test_session.refresh(site2)

    assert site2.id == 2
    assert site2.slug == "techpulse"
    assert site2.auto_push_to_wp is True

@pytest.mark.asyncio
async def test_site_topic_isolation(test_session: AsyncSession):
    # Create sites
    s1 = ManagedSite(name="MedHealth Times", slug="medhealth", wp_url="http://med.com", wp_api_key="k1")
    s2 = ManagedSite(name="TechPulse AI", slug="techpulse", wp_url="http://tech.com", wp_api_key="k2")
    test_session.add_all([s1, s2])
    await test_session.commit()
    await test_session.refresh(s1)
    await test_session.refresh(s2)

    # Add medical topic to Site 1
    t1 = Topic(site_id=s1.id, name="Cardiology Breakthroughs", keywords=["mRNA heart repair"])
    # Add tech topic to Site 2
    t2 = Topic(site_id=s2.id, name="Quantum Cryptography", keywords=["qubit encryption"])
    # Same name on different sites should be allowed
    t3 = Topic(site_id=s2.id, name="Cardiology Breakthroughs", keywords=["digital health cardiology"])
    test_session.add_all([t1, t2, t3])
    await test_session.commit()

    # Query site 1 topics
    res1 = await test_session.execute(select(Topic).where(Topic.site_id == s1.id))
    s1_topics = [t.name for t in res1.scalars().all()]
    assert "Cardiology Breakthroughs" in s1_topics
    assert "Quantum Cryptography" not in s1_topics

    # Query site 2 topics
    res2 = await test_session.execute(select(Topic).where(Topic.site_id == s2.id))
    s2_topics = [t.name for t in res2.scalars().all()]
    assert "Quantum Cryptography" in s2_topics
    assert len(s2_topics) == 2

@pytest.mark.asyncio
async def test_site_content_rules_isolation(test_session: AsyncSession):
    s1 = ManagedSite(name="MedHealth Times", slug="medhealth", wp_url="http://med.com", wp_api_key="k1")
    s2 = ManagedSite(name="TechPulse AI", slug="techpulse", wp_url="http://tech.com", wp_api_key="k2")
    test_session.add_all([s1, s2])
    await test_session.commit()
    await test_session.refresh(s1)
    await test_session.refresh(s2)

    # Site 1 rules: Medical, 450-520 words
    r1 = ContentRule(
        site_id=s1.id,
        name="MedHealth Rules",
        tone="Professional & Journalistic",
        word_count_min=450,
        word_count_max=520,
        disclaimer_text="Clinical disclaimer"
    )
    # Site 2 rules: Tech, 800-1200 words
    r2 = ContentRule(
        site_id=s2.id,
        name="TechPulse Rules",
        tone="Cutting-Edge & Analytical",
        word_count_min=800,
        word_count_max=1200,
        disclaimer_text="Tech opinion disclaimer"
    )
    test_session.add_all([r1, r2])
    await test_session.commit()

    # Verify site 1 rules
    res1 = await test_session.execute(select(ContentRule).where(ContentRule.site_id == s1.id))
    rule1 = res1.scalars().first()
    assert rule1.word_count_max == 520
    assert rule1.tone == "Professional & Journalistic"

    # Verify site 2 rules
    res2 = await test_session.execute(select(ContentRule).where(ContentRule.site_id == s2.id))
    rule2 = res2.scalars().first()
    assert rule2.word_count_max == 1200
    assert rule2.tone == "Cutting-Edge & Analytical"

@pytest.mark.asyncio
async def test_pipeline_multisite_push_routing(test_session: AsyncSession, monkeypatch):
    # Setup two managed sites
    s1 = ManagedSite(id=1, name="MedHealth Times", slug="medhealth", wp_url="http://medhealth.test", wp_api_key="key-med-1")
    s2 = ManagedSite(id=2, name="TechPulse AI", slug="techpulse", wp_url="http://techpulse.test", wp_api_key="key-tech-2")
    test_session.add_all([s1, s2])

    post_for_site2 = GeneratedPost(
        site_id=2,
        title="Autonomous AI Agents in Cloud Defense",
        slug="autonomous-ai-cloud-defense",
        body_html="<h6><strong>Cloud Security Shift</strong></h6><p>Enterprise workloads adopt autonomous detection.</p>",
        status="PENDING_REVIEW"
    )
    test_session.add(post_for_site2)
    await test_session.commit()
    await test_session.refresh(post_for_site2)

    captured_calls = []

    def mock_submit(self, payload, max_retries=3):
        captured_calls.append({
            "base_url": self.base_url,
            "api_key": self.api_key,
            "title": payload["title"]
        })
        return {
            "success": True,
            "wp_post_id": 999,
            "edit_url": f"{self.base_url}/wp-admin/post.php?post=999&action=edit"
        }

    monkeypatch.setattr(WordPressClient, "submit_draft_post", mock_submit)

    pipeline = PublishingPipeline()
    result = await pipeline.push_draft_to_wordpress(test_session, post_for_site2.id)

    assert result["success"] is True
    assert len(captured_calls) == 1
    # Verify it routed strictly to site 2!
    assert captured_calls[0]["base_url"] == "http://techpulse.test"
    assert captured_calls[0]["api_key"] == "key-tech-2"
    assert captured_calls[0]["title"] == "Autonomous AI Agents in Cloud Defense"

    # Verify post status updated
    await test_session.refresh(post_for_site2)
    assert post_for_site2.status == "SENT_TO_WP"
    assert post_for_site2.wp_post_id == 999

def test_system_grade_additive_only_guarantee(monkeypatch):
    """
    System-Grade Safety Verification:
    1. Verify WordPressClient has NO destructive methods (no delete_post, trash_post, update_post).
    2. Verify submit_draft_post defensively strips any 'id', 'post_id', or 'import_id' from payload.
    3. Verify outgoing HTTP requests ONLY create new drafts with no ID overwrites.
    """
    # 1. No destructive methods exist on WordPressClient
    client = WordPressClient(base_url="https://mysite.com", api_key="secret-key")
    assert not hasattr(client, "delete_post"), "WordPressClient must not contain any delete_post method"
    assert not hasattr(client, "trash_post"), "WordPressClient must not contain any trash_post method"
    assert not hasattr(client, "update_post"), "WordPressClient must not contain any update_post method"

    # 2. Verify payload sanitization strips ID keys
    captured_payloads = []
    def mock_requests_post(url, json=None, headers=None, timeout=None):
        captured_payloads.append(json)
        class MockResponse:
            status_code = 201
            headers = {"content-type": "application/json"}
            def json(self):
                return {
                    "success": True,
                    "data": {
                        "post_id": 12345,
                        "edit_url": "https://mysite.com/wp-admin/post.php?post=12345&action=edit",
                        "title": json.get("title")
                    }
                }
        return MockResponse()

    import requests
    monkeypatch.setattr(requests, "post", mock_requests_post)

    # Attempt to send a payload that includes existing post ID
    risky_payload = {
        "id": 1,
        "post_id": 42,
        "import_id": 99,
        "title": "Safe Additive Article",
        "body_html": "<p>Content</p>"
    }

    res = client.submit_draft_post(risky_payload)
    assert res["success"] is True
    assert len(captured_payloads) == 1

    sent_payload = captured_payloads[0]
    # Verify ID keys were strictly stripped!
    assert "id" not in sent_payload
    assert "post_id" not in sent_payload
    assert "import_id" not in sent_payload
    assert sent_payload["title"] == "Safe Additive Article"

