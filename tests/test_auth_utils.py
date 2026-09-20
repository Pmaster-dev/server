import sys
from unittest.mock import MagicMock

# Mock external cache_db modules before importing auth.utils
mock_redis_client = MagicMock()
mock_models = MagicMock()

cache_db_mock = MagicMock()
cache_db_redis_mock = MagicMock()
cache_db_redis_mock.redis_client = mock_redis_client
cache_db_models_mock = MagicMock()
cache_db_models_mock.User = MagicMock()
cache_db_models_mock.RefreshToken = MagicMock()

sys.modules["cache_db"] = cache_db_mock
sys.modules["cache_db.redis_client"] = cache_db_redis_mock
sys.modules["cache_db.models"] = cache_db_models_mock

import pytest
from flask import Flask, jsonify
from auth.utils import PasswordUtils, JWTUtils, SessionUtils, login_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils():
    access, refresh = JWTUtils.create_tokens("user123", "testuser")
    assert access is not None
    assert refresh is not None

    decoded = JWTUtils.decode_token(access)
    assert decoded["user_id"] == "user123"
    assert decoded["username"] == "testuser"

    invalid_decoded = JWTUtils.decode_token("invalid.token.str")
    assert invalid_decoded is None


def test_login_required_does_not_leak_details():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"

    @app.route("/protected")
    @login_required
    def protected_route():
        return jsonify({"status": "ok"})

    with app.test_client() as client:
        # Request without JWT header causes verify_jwt_in_request to raise an exception
        response = client.get("/protected")
        assert response.status_code == 401
        data = response.get_json()
        assert data == {"error": "Unauthorized"}
        assert "details" not in data
