import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Mock cache_db dependencies before importing auth.utils
mock_cache_db = MagicMock()
mock_redis_client = MagicMock()
mock_models = MagicMock()
sys.modules['cache_db'] = mock_cache_db
sys.modules['cache_db.redis_client'] = mock_redis_client
sys.modules['cache_db.models'] = mock_models

from flask import Flask, jsonify, g
import auth.utils as auth_utils


class TestAuthUtilsSecurity(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

    @patch('auth.utils.verify_jwt_in_request')
    @patch('auth.utils.get_jwt_identity')
    def test_login_required_error_leakage(self, mock_get_identity, mock_verify_jwt):
        mock_verify_jwt.side_effect = Exception("Internal DB error: connection timeout on 10.0.0.1:5432")

        @self.app.route('/protected')
        @auth_utils.login_required
        def protected_route():
            return "OK"

        with self.app.test_client() as client:
            response = client.get('/protected')
            data = response.get_json()
            self.assertEqual(response.status_code, 401)
            self.assertEqual(data.get('error'), 'Unauthorized')
            self.assertNotIn('details', data, "Sensitive exception details were leaked in error response!")

    @patch.dict(os.environ, {}, clear=True)
    def test_jwt_secret_key_fallback_raises(self):
        with self.assertRaises(RuntimeError) as ctx:
            auth_utils.JWTUtils.create_tokens("123", "testuser")
        self.assertIn("JWT_SECRET_KEY environment variable is not set", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
