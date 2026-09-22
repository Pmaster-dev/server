import os
import sys
from unittest.mock import MagicMock

# Mock cache_db module dependencies for auth.utils unit tests
if 'cache_db' not in sys.modules:
    cache_db_mock = MagicMock()
    sys.modules['cache_db'] = cache_db_mock
    sys.modules['cache_db.redis_client'] = cache_db_mock.redis_client
    sys.modules['cache_db.models'] = cache_db_mock.models

import pytest
from auth.utils import JWTUtils, PasswordUtils


def test_jwt_utils_without_secret_key():
    os.environ.pop('JWT_SECRET_KEY', None)

    with pytest.raises(ValueError, match="JWT_SECRET_KEY environment variable is not configured"):
        JWTUtils.create_tokens("user123", "alice")

    assert JWTUtils.decode_token("some_token") is None


def test_jwt_utils_with_secret_key():
    os.environ['JWT_SECRET_KEY'] = 'super-secret-key-for-testing'
    try:
        access_token, refresh_token = JWTUtils.create_tokens("user123", "alice")
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)

        decoded_access = JWTUtils.decode_token(access_token)
        assert decoded_access is not None
        assert decoded_access['user_id'] == "user123"
        assert decoded_access['username'] == "alice"
        assert decoded_access['type'] == 'access'

        decoded_refresh = JWTUtils.decode_token(refresh_token)
        assert decoded_refresh is not None
        assert decoded_refresh['user_id'] == "user123"
        assert decoded_refresh['type'] == 'refresh'
    finally:
        os.environ.pop('JWT_SECRET_KEY', None)


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")
