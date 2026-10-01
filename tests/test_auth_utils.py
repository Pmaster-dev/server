import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_models = MagicMock()

sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_redis_client
sys.modules['cache_db.models'] = mock_models

from flask import Flask, jsonify
import auth.utils as auth_utils


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.route('/protected')
    @auth_utils.login_required
    def protected():
        return jsonify({'message': 'success'})

    return app


def test_login_required_unauthorized_does_not_leak_details(app):
    """Test that when an exception occurs in login_required, details are not leaked in the response."""
    with app.test_request_context('/protected'):
        with patch('auth.utils.verify_jwt_in_request', side_effect=Exception('Internal DB Connection Failed Secret Details')):
            client = app.test_client()
            response = client.get('/protected')

            assert response.status_code == 401
            data = response.get_json()
            assert data == {'error': 'Unauthorized'}
            assert 'details' not in data
            assert 'Internal DB Connection Failed Secret Details' not in str(data)
