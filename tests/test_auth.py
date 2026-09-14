import os
import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_user = MagicMock()
mock_refresh_token = MagicMock()

mock_cache_db.redis_client = mock_redis_client
mock_cache_db.models = MagicMock()
mock_cache_db.models.User = mock_user
mock_cache_db.models.RefreshToken = mock_refresh_token

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db.redis_client
sys.modules['cache_db.models'] = mock_cache_db.models

import pytest
from flask import Flask
from auth.utils import JWTUtils, PasswordUtils, login_required


def test_jwt_utils_requires_secret(monkeypatch):
    monkeypatch.delenv('JWT_SECRET_KEY', raising=False)

    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is not set"):
        JWTUtils.create_tokens("user123", "alice")

    assert JWTUtils.decode_token("some.invalid.token") is None


def test_jwt_utils_with_secret(monkeypatch):
    monkeypatch.setenv('JWT_SECRET_KEY', 'super-secret-key-12345')

    access_token, refresh_token = JWTUtils.create_tokens("user123", "alice")
    assert access_token is not None
    assert refresh_token is not None

    payload = JWTUtils.decode_token(access_token)
    assert payload is not None
    assert payload["user_id"] == "user123"
    assert payload["username"] == "alice"


def test_login_required_does_not_leak_error_details(monkeypatch):
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected_route():
        return "ok"

    # Mock verify_jwt_in_request to raise an exception with internal details
    def mock_verify():
        raise Exception("Internal database connection failed: secret_db_uri")

    monkeypatch.setattr("auth.utils.verify_jwt_in_request", mock_verify)

    client = app.test_client()
    response = client.get("/protected")

    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data == {"error": "Unauthorized"}
    assert "details" not in json_data
