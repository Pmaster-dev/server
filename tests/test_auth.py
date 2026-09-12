import sys
from unittest.mock import MagicMock

# Mock external cache_db dependency before importing auth.utils
mock_cache_db = MagicMock()
sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_cache_db.redis_client
sys.modules['cache_db.models'] = mock_cache_db.models

from flask import Flask, jsonify
from auth.utils import login_required

def test_login_required_unauthorized_does_not_leak_details(monkeypatch):
    app = Flask(__name__)

    @app.route("/protected")
    @login_required
    def protected_route():
        return jsonify({"message": "success"})

    # Force verify_jwt_in_request to raise an Exception with sensitive details
    def mock_verify():
        raise RuntimeError("Sensitive internal database stack trace or token parsing error")

    monkeypatch.setattr("auth.utils.verify_jwt_in_request", mock_verify)

    with app.test_client() as client:
        response = client.get("/protected")
        assert response.status_code == 401
        data = response.get_json()
        assert data == {"error": "Unauthorized"}
        assert "details" not in data
        assert "Sensitive internal" not in str(data)
