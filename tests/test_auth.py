import os
import sys
from unittest.mock import MagicMock

# Mock external module cache_db before importing auth.utils
cache_db_mock = MagicMock()
sys.modules["cache_db"] = cache_db_mock
sys.modules["cache_db.redis_client"] = cache_db_mock
sys.modules["cache_db.models"] = cache_db_mock

import pytest
from auth.utils import JWTUtils, PasswordUtils


def test_password_hashing():
    password = "securepassword123"
    hashed = PasswordUtils.hash_password(password)
    assert hashed != password
    assert PasswordUtils.verify_password(password, hashed)
    assert not PasswordUtils.verify_password("wrongpassword", hashed)


def test_password_hash_short():
    with pytest.raises(ValueError, match="Password must be at least 8 characters"):
        PasswordUtils.hash_password("short")


def test_jwt_tokens_without_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is not set"):
        JWTUtils.create_tokens("user-123", "testuser")

    assert JWTUtils.decode_token("some.jwt.token") is None


def test_jwt_tokens_with_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-12345")
    access, refresh = JWTUtils.create_tokens("user-123", "testuser")
    assert access
    assert refresh

    decoded = JWTUtils.decode_token(access)
    assert decoded is not None
    assert decoded["user_id"] == "user-123"
    assert decoded["username"] == "testuser"
    assert decoded["type"] == "access"
