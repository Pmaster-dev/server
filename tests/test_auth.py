import sys
from unittest.mock import MagicMock

# Mock cache_db module before importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock
sys.modules['cache_db.models'] = cache_db_mock

from flask import Flask
import pytest
from auth.utils import login_required

def test_login_required_unauthorized_hides_error_details():
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.route('/test')
    @login_required
    def protected():
        return 'success'

    with app.test_client() as client:
        # Request without JWT will raise an exception during verify_jwt_in_request
        response = client.get('/test')
        assert response.status_code == 401
        data = response.get_json()
        assert data == {'error': 'Unauthorized'}
        assert 'details' not in data
