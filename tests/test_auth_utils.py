import sys
from unittest.mock import MagicMock

# Mock external cache_db module before importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_user_model = MagicMock()
mock_cache_db.redis_client.redis_client = mock_redis_client
mock_cache_db.models.User = mock_user_model

sys.modules["cache_db"] = mock_cache_db
sys.modules["cache_db.redis_client"] = mock_cache_db.redis_client
sys.modules["cache_db.models"] = mock_cache_db.models

import json
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from auth.utils import PasswordUtils, JWTUtils, SessionUtils, login_required, admin_required, verify_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed) is True
    assert PasswordUtils.verify_password("wrongpassword", hashed) is False


def test_login_required_exception_does_not_leak_details():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test-secret"
    JWTManager(app)

    @app.route("/protected")
    @login_required
    def protected():
        return jsonify({"message": "success"})

    with app.test_client() as client:
        # Request without JWT token triggers an exception in verify_jwt_in_request
        response = client.get("/protected")
        assert response.status_code == 401
        data = response.get_json()
        assert data == {"error": "Unauthorized"}
        # Ensure details field is not present (no exception detail leakage)
        assert "details" not in data
