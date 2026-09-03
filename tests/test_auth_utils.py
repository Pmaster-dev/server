import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis = MagicMock()
mock_user = MagicMock()
mock_refresh_token = MagicMock()

mock_cache_db.redis_client.redis_client = mock_redis
mock_cache_db.models.User = mock_user
mock_cache_db.models.RefreshToken = mock_refresh_token

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db.redis_client
sys.modules['cache_db.models'] = mock_cache_db.models

import pytest
from flask import Flask
from auth.utils import login_required, PasswordUtils, JWTUtils


@pytest.fixture
def app():
    app_inst = Flask(__name__)
    app_inst.config['SECRET_KEY'] = 'test-secret'
    app_inst.config['JWT_SECRET_KEY'] = 'test-secret'

    @app_inst.route('/protected')
    @login_required
    def protected_route():
        return {'message': 'success'}

    return app_inst


def test_login_required_unauthorized_does_not_leak_details(app, monkeypatch):
    sensitive_error_msg = "Database connection string or internal trace details"

    def mock_verify():
        raise Exception(sensitive_error_msg)

    monkeypatch.setattr('auth.utils.verify_jwt_in_request', mock_verify)

    client = app.test_client()
    response = client.get('/protected')

    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data == {'error': 'Unauthorized'}
    assert sensitive_error_msg not in str(json_data)


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False


def test_jwt_utils():
    access_token, _ = JWTUtils.create_tokens("123", "testuser")
    decoded = JWTUtils.decode_token(access_token)
    assert decoded is not None
    assert decoded['user_id'] == "123"
    assert decoded['username'] == "testuser"
