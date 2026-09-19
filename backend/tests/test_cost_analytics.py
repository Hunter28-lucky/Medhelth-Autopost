import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from backend.main import app
from backend.config import settings
from backend.services.cost_engine import (
    compute_post_cost, format_currency_amount,
    estimate_tokens_from_text, calculate_catalog_summary
)
from backend.services.auth_service import create_developer_token

@pytest.mark.asyncio
async def test_cost_engine_computation():
    tokens = estimate_tokens_from_text(body_text="<h6><strong>Clinical Finding</strong></h6><p>Sample paragraph.</p>")
    assert tokens["prompt_tokens"] > 1500
    assert tokens["completion_tokens"] > 500

    cost_data = compute_post_cost(
        prompt_tokens=2200,
        completion_tokens=800,
        search_queries=1,
        custom_currency="USD"
    )
    assert cost_data["currency"] == "USD"
    assert cost_data["currency_symbol"] == "$"
    assert cost_data["total_cost_usd"] > 0
    assert len(cost_data["stages"]) == 3
    
    # Verify stages
    stage_ids = [s["id"] for s in cost_data["stages"]]
    assert "research" in stage_ids
    assert "writing" in stage_ids
    assert "assembling" in stage_ids
    assert sum(s["percentage"] for s in cost_data["stages"]) == 100

@pytest.mark.asyncio
async def test_currency_conversion():
    usd_val = 0.0035
    inr_res = format_currency_amount(usd_val, "INR")
    assert inr_res["currency"] == "INR"
    assert inr_res["currency_symbol"] == "₹"
    assert inr_res["amount_converted"] > 0.20

    eur_res = format_currency_amount(usd_val, "EUR")
    assert eur_res["currency"] == "EUR"
    assert eur_res["currency_symbol"] == "€"

@pytest.mark.asyncio
async def test_manual_override_mode():
    original_override = settings.COST_MANUAL_OVERRIDE_ENABLED
    original_fixed = settings.COST_FIXED_PER_POST
    try:
        settings.COST_MANUAL_OVERRIDE_ENABLED = True
        settings.COST_FIXED_PER_POST = 0.0050
        cost_data = compute_post_cost(2000, 800, search_queries=1, custom_currency="USD")
        assert cost_data["is_manual_override"] is True
        assert cost_data["total_cost_usd"] == 0.0050
    finally:
        settings.COST_MANUAL_OVERRIDE_ENABLED = original_override
        settings.COST_FIXED_PER_POST = original_fixed

@pytest.mark.asyncio
async def test_cost_summary_api_endpoint(test_session: AsyncSession):
    from backend.database import get_db
    from backend.models import Topic
    
    # Add a test topic in test DB
    test_topic = Topic(id=1, site_id=1, name="AI Oncology", keywords=["cancer AI"], weight=7)
    test_session.add(test_topic)
    await test_session.commit()

    app.dependency_overrides[get_db] = lambda: test_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/api/analytics/cost-summary?currency=USD")
            assert res.status_code == 200
            data = res.json()
            assert "single_post" in data
            assert "full_catalog_run" in data
            assert "projections" in data
            assert data["currency"] == "USD"
            assert data["currency_symbol"] == "$"

            # Test topic cost breakdown endpoint
            res_topic = await ac.get("/api/topics/1/cost-breakdown?currency=INR")
            assert res_topic.status_code == 200
            topic_data = res_topic.json()
            assert topic_data["currency"] == "INR"
            assert topic_data["currency_symbol"] == "₹"
            assert len(topic_data["stages"]) == 3
    finally:
        app.dependency_overrides.pop(get_db, None)

@pytest.mark.asyncio
async def test_update_cost_settings_via_api():
    token = create_developer_token()
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Update settings with INR currency and custom rate
        update_payload = {
            "cost_currency": "INR",
            "cost_manual_override_enabled": True,
            "cost_fixed_per_post": 0.0042
        }
        put_res = await ac.put("/api/settings", json=update_payload, headers=headers)
        assert put_res.status_code == 200
        res_data = put_res.json()
        assert res_data["cost_currency"] == "INR"
        assert res_data["cost_manual_override_enabled"] is True
        assert res_data["cost_fixed_per_post"] == 0.0042

        # Reset back to USD clean default
        reset_payload = {
            "cost_currency": "USD",
            "cost_manual_override_enabled": False,
            "cost_fixed_per_post": 0.0035
        }
        await ac.put("/api/settings", json=reset_payload, headers=headers)
