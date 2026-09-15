import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_models = MagicMock()
sys.modules["cache_db"] = mock_cache_db
sys.modules["cache_db.redis_client"] = mock_cache_db
mock_cache_db.redis_client = mock_redis_client
sys.modules["cache_db.models"] = mock_models
mock_models.User = MagicMock()
mock_models.RefreshToken = MagicMock()

import os
import pytest
from flask import Flask
from auth.utils import (
    PasswordUtils,
    JWTUtils,
    SessionUtils,
    login_required,
    admin_required,
    verify_required,
)


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils_missing_secret(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is not set"):
        JWTUtils.create_tokens("user123", "alice")

    assert JWTUtils.decode_token("some.jwt.token") is None


def test_jwt_utils_with_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-key-12345")
    access_token, refresh_token = JWTUtils.create_tokens("user123", "alice")
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded is not None
    assert decoded["user_id"] == "user123"
    assert decoded["username"] == "alice"
    assert decoded["type"] == "access"


def test_login_required_does_not_leak_error_details(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/protected")
    @login_required
    def protected_route():
        return "success"

    client = app.test_client()

    # Mock verify_jwt_in_request to raise an exception with internal sensitive info
    def raise_sensitive_error():
        raise RuntimeError("Sensitive DB / JWT Exception Internal Stack Trace Details")

    monkeypatch.setattr("auth.utils.verify_jwt_in_request", raise_sensitive_error)

    response = client.get("/protected")
    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data == {"error": "Unauthorized"}
    # Ensure details field is not present and no stack trace is leaked
    assert "details" not in json_data
    assert "Sensitive DB" not in response.get_data(as_text=True)
