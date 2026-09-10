import pytest
from backend.services.yoast_optimizer import yoast_optimizer

def test_flesch_reading_ease():
    sample_text = (
        "The quick brown fox jumps over the lazy dog. "
        "Simple sentences are easy to read and understand. "
        "Doctors recommend clear patient communication."
    )
    score = yoast_optimizer.calculate_flesch_reading_ease(sample_text)
    assert score >= 60.0

def test_evaluate_seo_criteria():
    post_data = {
        "title": "Novel Developments in Healthcare Technology",
        "slug": "novel-developments-in-healthcare",
        "body_html": "<p>General introduction without any keyphrase.</p><h2>Section One</h2><p>Content without keywords.</p>",
        "meta_title": "Healthcare Tech Update",
        "meta_description": "Short desc",
        "focus_keyphrase": "cardiac mRNA therapy",
        "sources_used": []
    }
    audit = yoast_optimizer.analyze_full_post(post_data)
    assert audit["seo_score"] < 50
    # Confirm keyphrase in title and intro failed
    intro_check = next(c for c in audit["seo_checks"] if c["id"] == "intro_kw")
    assert intro_check["status"] == "bad"

def test_auto_fix_to_green_lights():
    raw_post = {
        "title": "Cardiology Breakthroughs: mRNA Heart Repair Advances",
        "slug": "cardiology-breakthroughs-mrna-heart-repair",
        "body_html": """
<p class="lead">Investigators published a prospective cohort analysis evaluating therapeutic outcomes in heart failure. The primary endpoint demonstrated significant clinical gains.</p>
<h2>Clinical Trial Evaluation</h2>
<p>Modern clinical workflows increasingly require rapid diagnostic assessment protocols. Current multi-cohort validation optimizes patient care delivery.</p>
<h2>Future Directions</h2>
<p>Regulatory agencies are standardizing guidelines for novel therapeutic interventions to accelerate healthcare adoption.</p>
""",
        "meta_title": "Cardiology Breakthroughs: mRNA Heart Repair Advances",
        "meta_description": "New review on heart repair.",
        "focus_keyphrase": "mrna heart repair",
        "sources_used": [{"title": "NEJM Study", "url": "https://nejm.org/doi/10.1056/example", "domain": "nejm.org"}]
    }

    # Verify initially not all green
    initial_audit = yoast_optimizer.analyze_full_post(raw_post)
    assert initial_audit["is_all_green"] is False

    # Execute Self-Healing Auto-Fixer
    repaired = yoast_optimizer.auto_fix_post(raw_post)

    # Verify repaired draft achieves green lights
    assert repaired["yoast_seo_score"] >= 80, f"SEO score {repaired['yoast_seo_score']} is not green"
    assert repaired["yoast_readability_score"] >= 80, f"Readability score {repaired['yoast_readability_score']} is not green"
    assert "mrna heart repair" in repaired["body_html"].lower()
    assert 120 <= len(repaired["meta_description"]) <= 156
    assert "mrna heart repair" in repaired["meta_description"].lower()
