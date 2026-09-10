import pytest
from backend.services.free_search_provider import FreeOnlineSearchProvider

@pytest.mark.asyncio
async def test_free_online_search_execution():
    provider = FreeOnlineSearchProvider()
    results = await provider.search(["cardiac mRNA therapy"], max_results=3)
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert "title" in first and len(first["title"]) > 0
    assert "url" in first and first["url"].startswith("http")
    assert "snippet" in first
    assert "source" in first
