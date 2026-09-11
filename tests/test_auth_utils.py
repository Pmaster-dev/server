"""Unit tests for auth/utils.py."""

import sys
from unittest.mock import MagicMock, patch
import pytest
from flask import Flask, jsonify


# Mock the external cache_db module before importing auth.utils
mock_redis_client = MagicMock()
mock_user_model = MagicMock()
mock_refresh_token_model = MagicMock()

cache_db_mock = MagicMock()
cache_db_redis_mock = MagicMock()
cache_db_redis_mock.redis_client = mock_redis_client
cache_db_models_mock = MagicMock()
cache_db_models_mock.User = mock_user_model
cache_db_models_mock.RefreshToken = mock_refresh_token_model

sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_redis_mock
sys.modules['cache_db.models'] = cache_db_models_mock

from auth.utils import (
    PasswordUtils,
    JWTUtils,
    SessionUtils,
    login_required,
    admin_required,
    verify_required,
)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    return app


def test_password_utils_hash_and_verify():
    with pytest.raises(ValueError, match="at least 8 characters"):
        PasswordUtils.hash_password("short")

    password = "securePassword123!"
    hashed = PasswordUtils.hash_password(password)
    assert hashed != password
    assert PasswordUtils.verify_password(password, hashed) is True
    assert PasswordUtils.verify_password("wrongPassword", hashed) is False


def test_jwt_utils_create_and_decode(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-key")
    user_id = "user-123"
    username = "testuser"

    access_token, refresh_token = JWTUtils.create_tokens(user_id, username)
    assert access_token is not None
    assert refresh_token is not None

    decoded_access = JWTUtils.decode_token(access_token)
    assert decoded_access["user_id"] == user_id
    assert decoded_access["username"] == username
    assert decoded_access["type"] == "access"

    decoded_invalid = JWTUtils.decode_token("invalid.token.str")
    assert decoded_invalid is None


def test_session_utils():
    session_id1 = SessionUtils.generate_session_id()
    session_id2 = SessionUtils.generate_session_id()
    assert len(session_id1) > 20
    assert session_id1 != session_id2

    mobile_info = SessionUtils.get_device_info("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) Mobile")
    assert mobile_info["device_type"] == "mobile"

    desktop_info = SessionUtils.get_device_info("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    assert desktop_info["device_type"] == "desktop"


def test_login_required_cached_inactive_user_blocked(app):
    """Test security fix: cached user with is_active=False must be rejected with 401."""
    @app.route("/protected")
    @login_required
    def protected_route():
        return jsonify({"message": "success"}), 200

    # User exists in cache, but is marked inactive
    mock_redis_client.get_cached_user.return_value = {
        "user_id": "u-123",
        "username": "cached_inactive",
        "is_active": False,
    }

    with app.test_client() as client:
        with patch("auth.utils.verify_jwt_in_request"), \
             patch("auth.utils.get_jwt_identity", return_value="u-123"):
            response = client.get("/protected")
            assert response.status_code == 401
            data = response.get_json()
            assert data["error"] == "User not found or inactive"


def test_login_required_cached_active_user_allowed(app):
    """Test cached active user passes authentication."""
    @app.route("/protected")
    @login_required
    def protected_route():
        return jsonify({"message": "success"}), 200

    mock_redis_client.get_cached_user.return_value = {
        "user_id": "u-456",
        "username": "cached_active",
        "is_active": True,
    }

    with app.test_client() as client:
        with patch("auth.utils.verify_jwt_in_request"), \
             patch("auth.utils.get_jwt_identity", return_value="u-456"):
            response = client.get("/protected")
            assert response.status_code == 200
            assert response.get_json() == {"message": "success"}


def test_login_required_error_does_not_leak_details(app):
    """Test security fix: exception details are not exposed in response."""
    @app.route("/protected")
    @login_required
    def protected_route():
        return jsonify({"message": "success"}), 200

    with app.test_client() as client:
        with patch("auth.utils.verify_jwt_in_request", side_effect=Exception("Database connection sensitive string")):
            response = client.get("/protected")
            assert response.status_code == 401
            data = response.get_json()
            assert data == {"error": "Unauthorized"}
            assert "details" not in data


def test_admin_required_and_verify_required(app):
    @app.route("/admin")
    @admin_required
    def admin_route():
        return jsonify({"message": "admin"}), 200

    @app.route("/verify")
    @verify_required
    def verify_route():
        return jsonify({"message": "verified"}), 200

    # User is active, but NOT admin and NOT verified
    mock_redis_client.get_cached_user.return_value = {
        "user_id": "u-789",
        "is_active": True,
        "is_admin": False,
        "is_verified": False,
    }

    with app.test_client() as client:
        with patch("auth.utils.verify_jwt_in_request"), \
             patch("auth.utils.get_jwt_identity", return_value="u-789"):
            res_admin = client.get("/admin")
            assert res_admin.status_code == 403
            assert res_admin.get_json()["error"] == "Admin access required"

            res_verify = client.get("/verify")
            assert res_verify.status_code == 403
            assert res_verify.get_json()["error"] == "Email verification required"

    # User is active, admin, and verified
    mock_redis_client.get_cached_user.return_value = {
        "user_id": "u-789",
        "is_active": True,
        "is_admin": True,
        "is_verified": True,
    }

    with app.test_client() as client:
        with patch("auth.utils.verify_jwt_in_request"), \
             patch("auth.utils.get_jwt_identity", return_value="u-789"):
            res_admin = client.get("/admin")
            assert res_admin.status_code == 200

            res_verify = client.get("/verify")
            assert res_verify.status_code == 200
