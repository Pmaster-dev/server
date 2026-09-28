import sys
from unittest.mock import MagicMock

# Mock cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis = MagicMock()
mock_user = MagicMock()

mock_cache_db.redis_client.redis_client = mock_redis
mock_cache_db.models.User = mock_user

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db.redis_client
sys.modules['cache_db.models'] = mock_cache_db.models

import pytest
from flask import Flask, jsonify
from auth.utils import PasswordUtils, JWTUtils, login_required, admin_required, verify_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed)
    assert not PasswordUtils.verify_password("wrongpassword", hashed)

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils():
    access_token, refresh_token = JWTUtils.create_tokens("user123", "testuser")
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded["user_id"] == "user123"
    assert decoded["username"] == "testuser"
    assert decoded["type"] == "access"

    assert JWTUtils.decode_token("invalid.token.str") is None


def test_login_required_does_not_leak_exception_details():
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected():
        return jsonify({"status": "ok"})

    with app.test_client() as client:
        # Requesting protected route without JWT token raises exception inside verify_jwt_in_request
        response = client.get("/protected")
        assert response.status_code == 401
        data = response.get_json()
        assert data == {"error": "Unauthorized"}
        assert "details" not in data
