import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock cache_db module before importing auth.utils
mock_redis = MagicMock()
mock_user = MagicMock()
mock_refresh = MagicMock()

cache_db_mock = MagicMock()
cache_db_mock.redis_client = MagicMock()
cache_db_mock.redis_client.redis_client = mock_redis
cache_db_mock.models = MagicMock()
cache_db_mock.models.User = mock_user
cache_db_mock.models.RefreshToken = mock_refresh

sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock.redis_client
sys.modules['cache_db.models'] = cache_db_mock.models

from auth.utils import JWTUtils, PasswordUtils, login_required
from flask import Flask, jsonify


def test_jwt_secret_required():
    with patch.dict(os.environ, {}, clear=True):
        if 'JWT_SECRET_KEY' in os.environ:
            del os.environ['JWT_SECRET_KEY']

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is not set"):
            JWTUtils.create_tokens("u123", "testuser")

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable is not set"):
            JWTUtils.decode_token("some.token.here")


def test_jwt_token_creation_and_decoding():
    with patch.dict(os.environ, {'JWT_SECRET_KEY': 'super-secret-key-12345'}):
        access_token, refresh_token = JWTUtils.create_tokens("u123", "testuser")
        assert access_token is not None
        assert refresh_token is not None

        decoded = JWTUtils.decode_token(access_token)
        assert decoded is not None
        assert decoded['user_id'] == "u123"
        assert decoded['username'] == "testuser"
        assert decoded['type'] == 'access'


def test_login_required_error_sanitization():
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.route('/protected')
    @login_required
    def protected_route():
        return jsonify({'message': 'success'})

    with app.test_client() as client:
        with patch('auth.utils.verify_jwt_in_request', side_effect=Exception("Database connection sensitive stack trace")):
            response = client.get('/protected')
            assert response.status_code == 401
            data = response.get_json()
            assert data == {'error': 'Unauthorized'}
            assert 'details' not in data
            assert 'sensitive' not in str(data)
