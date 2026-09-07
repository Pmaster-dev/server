import sys
from unittest.mock import MagicMock

# Mock cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis = MagicMock()
mock_user = MagicMock()
mock_cache_db.redis_client.redis_client = mock_redis
mock_cache_db.models.User = mock_user
sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db.redis_client
sys.modules['cache_db.models'] = mock_cache_db.models

import pytest
from flask import Flask, jsonify
from unittest.mock import patch
from auth.utils import login_required, PasswordUtils, JWTUtils


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'

    @app.route('/protected')
    @login_required
    def protected():
        return jsonify({'message': 'success'})

    return app


def test_login_required_unauthorized_does_not_leak_details(app):
    with app.test_request_context('/protected'):
        with patch('auth.utils.verify_jwt_in_request', side_effect=RuntimeError("Sensitive DB internal error details")):
            client = app.test_client()
            response = client.get('/protected')

            assert response.status_code == 401
            json_data = response.get_json()
            assert json_data == {'error': 'Unauthorized'}
            assert 'details' not in json_data
            assert 'Sensitive DB internal error details' not in str(json_data)


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed)
    assert not PasswordUtils.verify_password("wrongpassword", hashed)


def test_jwt_utils():
    access, refresh = JWTUtils.create_tokens("123", "testuser")
    assert access is not None
    assert refresh is not None
    payload = JWTUtils.decode_token(access)
    assert payload['user_id'] == "123"
    assert payload['username'] == "testuser"
