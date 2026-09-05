import sys
from unittest.mock import MagicMock, patch

# Mock cache_db module dependencies required by auth.utils
mock_redis = MagicMock()
mock_models = MagicMock()
sys.modules['cache_db'] = MagicMock()
sys.modules['cache_db.redis_client'] = mock_redis
sys.modules['cache_db.models'] = mock_models

from flask import Flask
from auth.utils import login_required, PasswordUtils, JWTUtils


def test_login_required_unauthorized_error_no_details_leak():
    """Verify login_required does not leak internal exception details in response."""
    app = Flask(__name__)

    @app.route('/protected')
    @login_required
    def protected_route():
        return {'status': 'ok'}

    with app.test_request_context('/protected'):
        with patch('auth.utils.verify_jwt_in_request', side_effect=Exception('Secret internal stack trace detail')):
            response, status_code = protected_route()

            assert status_code == 401
            json_data = response.get_json()
            assert json_data == {'error': 'Unauthorized'}
            assert 'details' not in json_data


def test_password_utils_hash_and_verify():
    """Verify password hashing and verification functionality."""
    pwd = "securepassword123"
    hashed = PasswordUtils.hash_password(pwd)
    assert PasswordUtils.verify_password(pwd, hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False
