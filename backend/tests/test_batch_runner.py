import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models import ManagedSite, Topic, GeneratedPost
from backend.services.batch_runner import BatchExecutionManager, BatchExecutionState

@pytest.mark.asyncio
async def test_batch_runner_initial_state():
    manager = BatchExecutionManager()
    status = manager.get_status()
    assert status["is_running"] is False
    assert status["status"] == "IDLE"
    assert status["total_topics"] == 0
    assert status["progress_percentage"] == 0

@pytest.mark.asyncio
async def test_batch_runner_state_tracking():
    state = BatchExecutionState()
    state.site_id = 1
    state.site_name = "MedHealth Times"
    state.total_topics = 10
    state.completed_topics = 3
    state.failed_topics = 1

    d = state.to_dict()
    assert d["site_id"] == 1
    assert d["site_name"] == "MedHealth Times"
    assert d["total_topics"] == 10
    assert d["completed_topics"] == 3
    assert d["failed_topics"] == 1
    assert d["processed_topics"] == 4
    assert d["progress_percentage"] == 40

@pytest.mark.asyncio
async def test_batch_runner_cancellation():
    manager = BatchExecutionManager()
    manager.state.is_running = True
    manager.state.site_name = "MedHealth Times"

    cancel_res = await manager.cancel_batch()
    assert cancel_res["success"] is True
    assert manager._cancel_requested is True
    assert manager.state.status == "CANCELLING"

@pytest.mark.asyncio
async def test_batch_runner_worker_loop_isolation(test_session: AsyncSession):
    # Setup test site and topics
    site1 = ManagedSite(id=1, name="MedHealth Times", slug="medhealth", wp_url="http://med.com", wp_api_key="k1")
    site2 = ManagedSite(id=2, name="TechPulse", slug="techpulse", wp_url="http://tech.com", wp_api_key="k2")
    test_session.add_all([site1, site2])

    t1 = Topic(site_id=1, name="Topic 1", keywords=["k1"], is_active=True)
    t2 = Topic(site_id=1, name="Topic 2", keywords=["k2"], is_active=True)
    t3 = Topic(site_id=1, name="Topic 3 (Inactive)", keywords=["k3"], is_active=False)
    t4 = Topic(site_id=2, name="Other Site Topic", keywords=["k4"], is_active=True)
    test_session.add_all([t1, t2, t3, t4])
    await test_session.commit()

    # Mock pipeline execution
    mock_pipeline = MagicMock()
    mock_pipeline.execute_run_for_topic = AsyncMock(return_value={"success": True, "post_id": 99, "post_title": "Test Title"})

    manager = BatchExecutionManager(pipeline=mock_pipeline)

    # Worker loop directly with topic records for site 1
    topics_to_run = [{"id": t1.id, "name": t1.name}, {"id": t2.id, "name": t2.name}]
    manager.state.total_topics = 2
    manager.state.site_id = 1
    manager.state.site_name = "MedHealth Times"

    with patch("backend.services.batch_runner.AsyncSessionLocal") as mock_session_local:
        mock_ctx = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_ctx
        mock_session_local.return_value.__aexit__.return_value = None

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await manager._worker_loop(topics_to_run, force_fresh_search=True)

    assert manager.state.completed_topics == 2
    assert manager.state.failed_topics == 0
    assert manager.state.status == "COMPLETED"
    assert mock_pipeline.execute_run_for_topic.call_count == 2

@pytest.mark.asyncio
async def test_batch_status_and_cancel_endpoints():
    from httpx import AsyncClient, ASGITransport
    from backend.main import app
    from backend.services.auth_service import create_developer_token

    token = create_developer_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/runs/batch-status")
        assert res.status_code == 200
        data = res.json()
        assert "is_running" in data
        assert "total_topics" in data
        assert "progress_percentage" in data

        cancel_res = await ac.post("/api/runs/batch-cancel", headers=headers)
        assert cancel_res.status_code == 200

@pytest.mark.asyncio
async def test_bulk_push_drafts_endpoint(test_session: AsyncSession):
    from httpx import AsyncClient, ASGITransport
    from backend.main import app, pipeline
    from backend.database import get_db
    from backend.services.auth_service import create_developer_token

    # Add posts to test_session
    p1 = GeneratedPost(id=101, site_id=1, title="Article 1", slug="article-1", body_html="<p>Test</p>", status="PENDING_REVIEW")
    p2 = GeneratedPost(id=102, site_id=1, title="Article 2", slug="article-2", body_html="<p>Test 2</p>", status="APPROVED")
    test_session.add_all([p1, p2])
    await test_session.commit()

    token = create_developer_token()
    headers = {"Authorization": f"Bearer {token}"}

    app.dependency_overrides[get_db] = lambda: test_session
    try:
        with patch.object(pipeline, "push_draft_to_wordpress", new_callable=AsyncMock) as mock_push:
            mock_push.return_value = {"success": True, "wp_post_id": 555, "edit_url": "http://wp/edit/555"}

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Test push by IDs
                res = await ac.post("/api/drafts/bulk-push", json={"post_ids": [101, 102]}, headers=headers)
                assert res.status_code == 200
                data = res.json()
                assert data["success"] is True
                assert data["pushed_count"] == 2
                assert len(data["pushed"]) == 2

                # Test push all pending for site 1
                res2 = await ac.post("/api/drafts/bulk-push", json={"all_pending": True, "site_id": 1}, headers=headers)
                assert res2.status_code == 200
                data2 = res2.json()
                assert data2["success"] is True
    finally:
        app.dependency_overrides.pop(get_db, None)
