import sys
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify

# Mock external cache_db module dependencies before importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock
sys.modules['cache_db.models'] = cache_db_mock

from auth.utils import (
    PasswordUtils,
    JWTUtils,
    SessionUtils,
    login_required,
    admin_required,
    verify_required
)


def create_test_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'

    @app.route('/protected')
    @login_required
    def protected_route():
        return jsonify({'message': 'success'})

    @app.route('/admin')
    @admin_required
    def admin_route():
        return jsonify({'message': 'admin_success'})

    @app.route('/verified')
    @verify_required
    def verified_route():
        return jsonify({'message': 'verified_success'})

    return app


def test_login_required_hides_exception_details():
    app = create_test_app()
    client = app.test_client()

    # Simulate an exception in verify_jwt_in_request (e.g., missing or invalid JWT)
    with patch('auth.utils.verify_jwt_in_request', side_effect=Exception('Sensitive DB credentials or internal stack detail')):
        response = client.get('/protected')

        assert response.status_code == 401
        data = response.get_json()
        assert data == {'error': 'Unauthorized'}
        assert 'details' not in data
        assert 'Sensitive DB credentials' not in str(data)


def test_password_utils():
    hashed = PasswordUtils.hash_password('supersecret123')
    assert PasswordUtils.verify_password('supersecret123', hashed)
    assert not PasswordUtils.verify_password('wrongpassword', hashed)


def test_jwt_utils():
    access_token, refresh_token = JWTUtils.create_tokens('user123', 'alice')
    assert access_token is not None
    assert refresh_token is not None

    decoded = JWTUtils.decode_token(access_token)
    assert decoded is not None
    assert decoded['user_id'] == 'user123'
    assert decoded['username'] == 'alice'


def test_session_utils():
    session_id = SessionUtils.generate_session_id()
    assert len(session_id) > 20
