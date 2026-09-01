import sys
from unittest.mock import MagicMock

# Mock cache_db module dependencies before importing auth.utils
cache_db_mock = MagicMock()
redis_client_mock = MagicMock()
models_mock = MagicMock()
cache_db_mock.redis_client = redis_client_mock
cache_db_mock.models = models_mock

sys.modules["cache_db"] = cache_db_mock
sys.modules["cache_db.redis_client"] = redis_client_mock
sys.modules["cache_db.models"] = models_mock

import pytest
from flask import Flask
from auth.utils import PasswordUtils, JWTUtils, login_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("password123")
    assert PasswordUtils.verify_password("password123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils():
    access, refresh = JWTUtils.create_tokens("user1", "alice")
    decoded_access = JWTUtils.decode_token(access)
    assert decoded_access["user_id"] == "user1"
    assert decoded_access["username"] == "alice"
    assert decoded_access["type"] == "access"

    assert JWTUtils.decode_token("invalid.token.here") is None


def test_login_required_sanitizes_errors(monkeypatch):
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected():
        return "ok"

    client = app.test_client()

    # Force verify_jwt_in_request to raise an exception with sensitive internal details
    def mock_verify():
        raise Exception("Sensitive DB connection error or stack info")

    monkeypatch.setattr("auth.utils.verify_jwt_in_request", mock_verify)

    response = client.get("/protected")
    assert response.status_code == 401
    data = response.get_json()
    assert data == {"error": "Unauthorized"}
    assert "details" not in data
