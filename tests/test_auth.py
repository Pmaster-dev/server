import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock cache_db module before importing auth.utils
mock_redis_client = MagicMock()
mock_user_model = MagicMock()
mock_refresh_token_model = MagicMock()

cache_db_mock = MagicMock()
cache_db_mock.redis_client = MagicMock()
cache_db_mock.redis_client.redis_client = mock_redis_client
cache_db_mock.models = MagicMock()
cache_db_mock.models.User = mock_user_model
cache_db_mock.models.RefreshToken = mock_refresh_token_model

sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock.redis_client
sys.modules['cache_db.models'] = cache_db_mock.models

from flask import Flask, jsonify
from auth.utils import PasswordUtils, JWTUtils, login_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False


def test_password_utils_short_password():
    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_login_required_does_not_leak_exception_details():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'

    @app.route('/protected')
    @login_required
    def protected_route():
        return jsonify({'message': 'success'})

    with app.test_client() as client:
        sensitive_error_msg = "Database connection failed with sensitive credentials secret_123"
        with patch('auth.utils.verify_jwt_in_request', side_effect=Exception(sensitive_error_msg)):
            response = client.get('/protected')
            assert response.status_code == 401
            data = response.get_json()
            assert data == {'error': 'Unauthorized'}
            assert 'details' not in data
            assert 'secret_123' not in str(response.data)
