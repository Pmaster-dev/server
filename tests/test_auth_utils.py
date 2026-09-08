import os
import sys
from unittest.mock import MagicMock

# Mock external dependency cache_db before auth.utils is imported
sys.modules['cache_db'] = MagicMock()
sys.modules['cache_db.redis_client'] = MagicMock()
sys.modules['cache_db.models'] = MagicMock()

import pytest
from auth.utils import JWTUtils


def test_jwt_utils_requires_secret_key():
    """Test that JWTUtils raises ValueError when JWT_SECRET_KEY is not set."""
    os.environ.pop("JWT_SECRET_KEY", None)
    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is not set"):
        JWTUtils.create_tokens("user123", "testuser")

    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is not set"):
        JWTUtils.decode_token("some.jwt.token")


def test_jwt_utils_create_and_decode_tokens():
    """Test creating and decoding JWT tokens when JWT_SECRET_KEY is configured."""
    os.environ["JWT_SECRET_KEY"] = "super-secret-key-for-testing"
    try:
        access_token, refresh_token = JWTUtils.create_tokens("user123", "testuser")
        assert access_token is not None
        assert refresh_token is not None

        decoded = JWTUtils.decode_token(access_token)
        assert decoded is not None
        assert decoded["user_id"] == "user123"
        assert decoded["username"] == "testuser"
        assert decoded["type"] == "access"

        decoded_refresh = JWTUtils.decode_token(refresh_token)
        assert decoded_refresh is not None
        assert decoded_refresh["user_id"] == "user123"
        assert decoded_refresh["username"] == "testuser"
        assert decoded_refresh["type"] == "refresh"
    finally:
        os.environ.pop("JWT_SECRET_KEY", None)
