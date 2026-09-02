"""
Unit tests for auth/utils.py security fixes and utilities.
"""

import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock.redis_client
sys.modules['cache_db.models'] = cache_db_mock.models

import pytest
from flask import Flask, jsonify
from auth.utils import PasswordUtils, JWTUtils, login_required


@pytest.fixture
def app():
    """Create a test Flask application."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret-key'

    @app.route('/protected')
    @login_required
    def protected():
        return jsonify({'message': 'success'})

    return app


def test_password_hashing():
    """Test password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = PasswordUtils.hash_password(password)
    assert hashed != password
    assert PasswordUtils.verify_password(password, hashed) is True
    assert PasswordUtils.verify_password("WrongPassword", hashed) is False


def test_password_length_validation():
    """Test password length requirement."""
    with pytest.raises(ValueError, match="at least 8 characters"):
        PasswordUtils.hash_password("short")


def test_jwt_token_creation_and_decoding():
    """Test JWT token creation and decoding."""
    access_token, refresh_token = JWTUtils.create_tokens("user123", "testuser")
    assert access_token is not None
    assert refresh_token is not None

    decoded_access = JWTUtils.decode_token(access_token)
    assert decoded_access is not None
    assert decoded_access["user_id"] == "user123"
    assert decoded_access["username"] == "testuser"
    assert decoded_access["type"] == "access"


def test_login_required_unauthorized_no_leak(app):
    """Test that login_required returns 401 and does NOT leak internal exception details."""
    with app.test_client() as client:
        response = client.get('/protected')
        assert response.status_code == 401
        data = response.get_json()
        assert data == {'error': 'Unauthorized'}
        assert 'details' not in data
