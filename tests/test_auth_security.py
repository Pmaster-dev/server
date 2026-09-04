import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db.redis_client
sys.modules['cache_db.models'] = mock_cache_db.models

import pytest
from flask import Flask
from auth.utils import login_required


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'

    @app.route('/protected')
    @login_required
    def protected():
        return 'success'

    return app


def test_login_required_does_not_leak_error_details(app, monkeypatch):
    """Test that authentication exceptions do not leak internal error details to clients."""
    # Simulate an internal exception during auth check (e.g. DB or Redis failure)
    def mock_verify():
        raise RuntimeError("Internal database connection failed: postgres://user:secretpass@internal-host:5432/db")

    monkeypatch.setattr('auth.utils.verify_jwt_in_request', mock_verify)

    client = app.test_client()
    response = client.get('/protected')

    assert response.status_code == 401
    data = response.get_json()
    assert data == {'error': 'Unauthorized'}
    assert 'details' not in data
    assert 'secretpass' not in response.get_data(as_text=True)
    assert 'postgres' not in response.get_data(as_text=True)
