import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock
sys.modules['cache_db.models'] = cache_db_mock

from flask import Flask
from auth.utils import PasswordUtils, JWTUtils, login_required


def test_password_hashing():
    pw = "secret_password123"
    hashed = PasswordUtils.hash_password(pw)
    assert PasswordUtils.verify_password(pw, hashed) is True
    assert PasswordUtils.verify_password("wrong_password", hashed) is False


def test_jwt_utils():
    access, refresh = JWTUtils.create_tokens("u123", "alice")
    decoded_access = JWTUtils.decode_token(access)
    assert decoded_access["user_id"] == "u123"
    assert decoded_access["username"] == "alice"
    assert decoded_access["type"] == "access"


def test_login_required_does_not_leak_details(monkeypatch):
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected():
        return "success", 200

    def mock_verify():
        raise RuntimeError("Sensitive DB exception with stack trace or internal connection details")

    import flask_jwt_extended
    monkeypatch.setattr(flask_jwt_extended, "verify_jwt_in_request", mock_verify)

    client = app.test_client()
    response = client.get("/protected")

    assert response.status_code == 401
    data = response.get_json()
    assert data == {"error": "Unauthorized"}
    assert "details" not in data
