"""Tests for authentication security utilities."""

import os
import sys
from unittest.mock import MagicMock, patch

from flask import Flask
import pytest

# Mock external cache_db module before importing auth.utils
sys.modules['cache_db'] = MagicMock()
sys.modules['cache_db.redis_client'] = MagicMock()
sys.modules['cache_db.models'] = MagicMock()

# pylint: disable=wrong-import-position
from auth.utils import JWTUtils, PasswordUtils, login_required


def test_jwt_utils_without_secret_key():
    """Verify that JWTUtils raises RuntimeError if JWT_SECRET_KEY is missing."""
    msg = "JWT_SECRET_KEY environment variable is not configured"
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match=msg):
            JWTUtils.create_tokens("user123", "alice")

        with pytest.raises(RuntimeError, match=msg):
            JWTUtils.decode_token("some_dummy_token")


def test_jwt_utils_with_secret_key():
    """Verify that JWTUtils successfully creates and decodes tokens when key is configured."""
    with patch.dict(os.environ, {"JWT_SECRET_KEY": "super-secret-test-key"}):
        access_token, refresh_token = JWTUtils.create_tokens("user123", "alice")
        assert access_token is not None
        assert refresh_token is not None

        decoded = JWTUtils.decode_token(access_token)
        assert decoded is not None
        assert decoded["user_id"] == "user123"
        assert decoded["username"] == "alice"


def test_login_required_sanitizes_error_details():
    """Verify login_required does not leak exception details on error."""
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected_route():
        return "ok"

    with app.test_request_context("/protected"):
        with patch("auth.utils.verify_jwt_in_request",
                   side_effect=ValueError("Secret internal database error info")):
            response, status_code = protected_route()
            assert status_code == 401
            data = response.get_json()  # pylint: disable=no-member
            assert data == {"error": "Unauthorized"}
            assert "details" not in data


def test_password_utils():
    """Verify PasswordUtils hashing and verification."""
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed)
    assert not PasswordUtils.verify_password("wrongpassword", hashed)
