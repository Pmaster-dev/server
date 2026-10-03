import sys
from unittest.mock import MagicMock, patch
import os
import pytest
from flask import Flask

# Mock cache_db modules before importing auth.utils
mock_redis_client_mod = MagicMock()
mock_models_mod = MagicMock()
mock_cache_db = MagicMock()

mock_cache_db.redis_client = mock_redis_client_mod
mock_cache_db.models = mock_models_mod

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_redis_client_mod
sys.modules['cache_db.models'] = mock_models_mod

from auth.utils import JWTUtils, PasswordUtils, login_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False


def test_jwt_utils_without_secret():
    with patch.dict(os.environ, {}, clear=True):
        if "JWT_SECRET_KEY" in os.environ:
            del os.environ["JWT_SECRET_KEY"]
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is not configured"):
            JWTUtils.create_tokens("123", "user1")

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is not configured"):
            JWTUtils.decode_token("some_token")


def test_jwt_utils_with_secret():
    with patch.dict(os.environ, {"JWT_SECRET_KEY": "supersecretkey123"}):
        access, refresh = JWTUtils.create_tokens("123", "user1")
        assert access is not None
        assert refresh is not None

        decoded = JWTUtils.decode_token(access)
        assert decoded is not None
        assert decoded["user_id"] == "123"
        assert decoded["username"] == "user1"


def test_login_required_unauthorized_does_not_leak_details():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "secret"

    @app.route("/protected")
    @login_required
    def protected():
        return "ok"

    with app.test_client() as client:
        # Requesting protected endpoint without JWT token
        resp = client.get("/protected")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data == {"error": "Unauthorized"}
        assert "details" not in data
