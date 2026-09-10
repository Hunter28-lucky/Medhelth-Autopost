import pytest
from unittest.mock import patch, MagicMock
from backend.services.openrouter_client import OpenRouterClient, POPULAR_FREE_MODELS, FREE_MODEL_CASCADE

def test_openrouter_free_models_list():
    assert len(POPULAR_FREE_MODELS) >= 5
    model_ids = [m["id"] for m in POPULAR_FREE_MODELS]
    assert "openrouter/free" in model_ids
    assert "inclusionai/ling-3.0-flash-sante:free" in model_ids
    assert "google/gemma-4-31b-it:free" in model_ids

def test_openrouter_configured_check():
    client_unconfigured = OpenRouterClient(api_key="")
    assert client_unconfigured.is_configured() is False
    res = client_unconfigured.check_connection()
    assert res["connected"] is False

    client_configured = OpenRouterClient(api_key="sk-or-test-dummy-key")
    assert client_configured.is_configured() is True

def test_openrouter_cascade_fallback_success():
    client = OpenRouterClient(api_key="sk-or-test-dummy-key")
    
    # Mock _send_request so the first model fails (e.g., rate limit 429), and the second succeeds
    mock_responses = [
        RuntimeError("HTTP 429: Rate limit exceeded"),
        {
            "choices": [{
                "message": {
                    "content": '{"title": "OpenRouter Success", "body_html": "<p>Content</p>"}'
                }
            }]
        }
    ]

    with patch.object(client, "_send_request", side_effect=mock_responses):
        res = client.generate_chat_completion("System prompt", "User prompt")
        assert res["title"] == "OpenRouter Success"
