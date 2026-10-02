import sys
from unittest.mock import MagicMock, patch

# Mock cache_db module before auth.utils import
sys.modules['cache_db'] = MagicMock()
sys.modules['cache_db.redis_client'] = MagicMock()
sys.modules['cache_db.models'] = MagicMock()

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


def test_jwt_utils():
    access_token, refresh_token = JWTUtils.create_tokens("u123", "testuser")
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded["user_id"] == "u123"
    assert decoded["username"] == "testuser"

    assert JWTUtils.decode_token("invalid.jwt.token") is None


def test_session_utils():
    session_id = SessionUtils.generate_session_id()
    assert len(session_id) > 10


def test_login_required_unauthorized_does_not_leak_details():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"

    @app.route("/protected")
    @login_required
    def protected():
        return "secret data"

    with app.test_client() as client:
        with patch("auth.utils.verify_jwt_in_request", side_effect=Exception("Database connection sensitive error")):
            resp = client.get("/protected")
            assert resp.status_code == 401
            data = resp.get_json()
            assert data == {"error": "Unauthorized"}
            assert "details" not in data
            assert "sensitive" not in str(data)
