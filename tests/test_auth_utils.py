import os
import pytest
import sys

# Ensure auth module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock

# Mock cache_db module dependencies if not installed
sys.modules.setdefault("cache_db", MagicMock())
sys.modules.setdefault("cache_db.redis_client", MagicMock())
sys.modules.setdefault("cache_db.models", MagicMock())

from auth.utils import JWTUtils, PasswordUtils


def test_password_hashing():
    pwd = "securepassword123"
    hashed = PasswordUtils.hash_password(pwd)
    assert PasswordUtils.verify_password(pwd, hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False


def test_jwt_utils_requires_secret_key(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is not configured"):
        JWTUtils.create_tokens("user123", "alice")

    assert JWTUtils.decode_token("dummy.token.string") is None


def test_jwt_utils_with_secret_key(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-12345")

    access_token, refresh_token = JWTUtils.create_tokens("user123", "alice")
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded is not None
    assert decoded.get("user_id") == "user123"
    assert decoded.get("username") == "alice"
    assert decoded.get("type") == "access"
