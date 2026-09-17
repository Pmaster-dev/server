import sys
from unittest.mock import MagicMock, patch
from flask import Flask

# Mock cache_db modules before importing auth.utils
mock_redis = MagicMock()
mock_models = MagicMock()
sys.modules['cache_db'] = MagicMock()
sys.modules['cache_db.redis_client'] = MagicMock(redis_client=mock_redis)
sys.modules['cache_db.models'] = MagicMock(User=mock_models.User, RefreshToken=mock_models.RefreshToken)

from auth.utils import PasswordUtils, JWTUtils, login_required, admin_required, verify_required


def test_password_utils():
    hashed = PasswordUtils.hash_password("securepassword123")
    assert PasswordUtils.verify_password("securepassword123", hashed)
    assert not PasswordUtils.verify_password("wrongpassword", hashed)


def test_login_required_does_not_leak_exception_details():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-secret"

    @app.route("/protected")
    @login_required
    def protected():
        return "ok"

    with app.test_client() as client:
        # Simulate a request where JWT verification raises an exception with sensitive internal details
        with patch("auth.utils.verify_jwt_in_request", side_effect=RuntimeError("Database host 10.0.0.5 connection failed")):
            response = client.get("/protected")
            assert response.status_code == 401
            json_data = response.get_json()
            assert json_data == {"error": "Unauthorized"}
            # Ensure sensitive internal exception string is NOT in response
            assert "details" not in json_data
            assert "10.0.0.5" not in response.get_data(as_text=True)
            assert "Database" not in response.get_data(as_text=True)
