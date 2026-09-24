import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock
sys.modules['cache_db.models'] = cache_db_mock

from flask import Flask, jsonify
import pytest
from auth.utils import PasswordUtils, JWTUtils, login_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils():
    access_token, refresh_token = JWTUtils.create_tokens("user123", "testuser")
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded is not None
    assert decoded["user_id"] == "user123"
    assert decoded["username"] == "testuser"
    assert decoded["type"] == "access"


def test_login_required_does_not_leak_details(monkeypatch):
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected_route():
        return jsonify({"message": "success"})

    # Mock verify_jwt_in_request to raise an exception with sensitive details
    def mock_verify_jwt():
        raise Exception("Sensitive DB error or internal stack trace info")

    monkeypatch.setattr("auth.utils.verify_jwt_in_request", mock_verify_jwt)

    client = app.test_client()
    response = client.get("/protected")

    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data == {"error": "Unauthorized"}
    assert "details" not in json_data
