import sys
from unittest.mock import MagicMock

# Mock cache_db modules before auth.utils is imported
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock
sys.modules['cache_db.models'] = cache_db_mock

from flask import Flask, jsonify
from auth.utils import login_required


def test_login_required_does_not_leak_exception_details(monkeypatch):
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.route('/protected')
    @login_required
    def protected_route():
        return jsonify({'message': 'success'})

    def mock_verify():
        raise RuntimeError("Sensitive DB Connection String: postgresql://admin:secret@localhost:5432/db")

    monkeypatch.setattr('auth.utils.verify_jwt_in_request', mock_verify)

    with app.test_client() as client:
        response = client.get('/protected')
        assert response.status_code == 401
        data = response.get_json()
        assert data == {'error': 'Unauthorized'}
        assert 'details' not in data
        assert 'Sensitive' not in str(data)
