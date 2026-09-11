import pytest
from backend.services.generator_engine import ContentGenerator
from backend.models import ContentRule

@pytest.mark.asyncio
async def test_style_reference_in_generator():
    generator = ContentGenerator(openrouter_api_key="", anthropic_api_key="")
    rule = ContentRule(
        name="Test Style",
        style_reference_sample="""
        <div class="editorial-hero">
            <span class="badge">CLINICAL BRIEF</span>
            <p class="lead" style="font-family: Georgia, serif;">Groundbreaking trial results demonstrate 40% survival increase.</p>
        </div>
        <div class="custom-footer">Review conducted by Clinical Oncology Board.</div>
        """,
        style_reference_font="Georgia, serif",
        style_reference_header="Editorial Hero with Clinical Badge",
        style_reference_footer="Clinical Oncology Board Footer",
        disclaimer_text="Test disclaimer"
    )

    draft = await generator.generate_draft(
        topic_name="AI in Oncology",
        research_articles=[{
            "title": "Oncology Foundation Models",
            "url": "https://nature.com/oncology",
            "source": "Nature Medicine",
            "key_claims": ["Survival rates improved significantly."]
        }],
        rules=rule
    )

    assert draft is not None
    assert "body_html" in draft
    assert "Georgia, serif" in draft["body_html"]
    assert draft["focus_keyphrase"] is not None
