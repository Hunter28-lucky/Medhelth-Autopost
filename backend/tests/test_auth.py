import pytest
from backend.services.auth_service import create_developer_token, verify_developer_token
from backend.config import settings

def test_developer_token_lifecycle():
    token = create_developer_token(settings.DEVELOPER_NAME)
    assert token is not None
    assert settings.DEVELOPER_NAME in token
    assert verify_developer_token(token) is True

def test_tampered_or_invalid_tokens():
    assert verify_developer_token(None) is False
    assert verify_developer_token("") is False
    assert verify_developer_token("invalid.token") is False
    assert verify_developer_token("123.Krish Goswami.fakehash") is False
