import sys
from unittest.mock import MagicMock, patch
import pytest
from flask import Flask

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_models = MagicMock()

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db
sys.modules['cache_db.redis_client'].redis_client = mock_redis_client
sys.modules['cache_db.models'] = mock_models

from auth.utils import PasswordUtils, JWTUtils, SessionUtils, login_required, admin_required, verify_required


def test_password_utils():
    password = "securepassword123"
    hashed = PasswordUtils.hash_password(password)
    assert hashed != password
    assert PasswordUtils.verify_password(password, hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False

    with pytest.raises(ValueError):
        PasswordUtils.hash_password("short")


def test_jwt_utils():
    user_id = "user_123"
    username = "testuser"
    access_token, refresh_token = JWTUtils.create_tokens(user_id, username)
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded is not None
    assert decoded['user_id'] == user_id
    assert decoded['username'] == username
    assert decoded['type'] == 'access'

    assert JWTUtils.decode_token("invalid_token") is None


def test_session_utils():
    session_id = SessionUtils.generate_session_id()
    assert len(session_id) > 20

    app = Flask(__name__)
    with app.test_request_context(headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) Mobile/15E148'}):
        device_info = SessionUtils.get_device_info()
        assert device_info['device_type'] == 'mobile'


def test_login_required_does_not_leak_exception_details():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'

    @app.route('/protected')
    @login_required
    def protected_route():
        return "success", 200

    client = app.test_client()

    # Simulate an error during JWT verification that raises a detailed exception
    with patch('auth.utils.verify_jwt_in_request', side_effect=Exception("Database connection string postgres://user:secret@localhost/db failed")):
        response = client.get('/protected')
        assert response.status_code == 401
        json_data = response.get_json()
        assert json_data == {'error': 'Unauthorized'}
        # Explicitly verify sensitive details are NOT leaked in response
        assert 'details' not in json_data
        assert 'postgres' not in str(json_data)
        assert 'secret' not in str(json_data)
