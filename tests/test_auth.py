"""Tests for authentication utilities."""

import sys
from unittest.mock import MagicMock, patch

# Mock cache_db module dependencies prior to importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_models = MagicMock()

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_redis_client
sys.modules['cache_db.models'] = mock_models

from flask import Flask, jsonify  # pylint: disable=wrong-import-position
import pytest  # pylint: disable=wrong-import-position

from auth.utils import (  # pylint: disable=wrong-import-position
    JWTUtils,
    PasswordUtils,
    SessionUtils,
    login_required,
)


@pytest.fixture
def app():
    """Create Flask test app."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['JWT_SECRET_KEY'] = 'test-secret'

    @test_app.route('/protected')
    @login_required
    def protected():
        return jsonify({'message': 'success'})

    return test_app


def test_password_utils():
    """Test password hashing and verification."""
    password = "securePassword123"
    hashed = PasswordUtils.hash_password(password)
    assert hashed != password
    assert PasswordUtils.verify_password(password, hashed) is True
    assert PasswordUtils.verify_password("wrongPassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils():
    """Test JWT creation and decoding."""
    access, refresh = JWTUtils.create_tokens("user-1", "testuser")
    assert access is not None
    assert refresh is not None

    decoded = JWTUtils.decode_token(access)
    assert decoded is not None
    assert decoded['user_id'] == "user-1"
    assert decoded['username'] == "testuser"


def test_session_utils():
    """Test session ID generation."""
    session_id = SessionUtils.generate_session_id()
    assert isinstance(session_id, str)
    assert len(session_id) > 0


def test_login_required_sanitizes_error_details(app):
    """Verify login_required does not leak sensitive internal exception details."""
    with app.test_client() as client:
        with patch('auth.utils.verify_jwt_in_request', side_effect=Exception("Sensitive DB error connection string: postgresql://user:pass@localhost:5432/db")):
            response = client.get('/protected')
            assert response.status_code == 401
            data = response.get_json()
            assert data == {'error': 'Unauthorized'}
            assert 'details' not in data
            assert 'Sensitive DB error' not in str(data)
