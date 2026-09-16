import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock cache_db modules prior to importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock
sys.modules['cache_db.models'] = cache_db_mock

from flask import Flask, jsonify
from auth.utils import login_required, PasswordUtils, JWTUtils


class TestAuthUtils(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'test-secret'

        @self.app.route('/protected')
        @login_required
        def protected_route():
            return jsonify({'message': 'success'})

        self.client = self.app.test_client()

    @patch('auth.utils.verify_jwt_in_request')
    def test_login_required_unauthorized_does_not_leak_details(self, mock_verify):
        mock_verify.side_effect = Exception("Internal DB error: connection timeout at 10.0.0.5:5432")

        response = self.client.get('/protected')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()

        self.assertEqual(data, {'error': 'Unauthorized'})
        self.assertNotIn('details', data)
        self.assertNotIn('10.0.0.5', str(data))

    def test_password_utils_hash_and_verify(self):
        password = "securePassword123!"
        hashed = PasswordUtils.hash_password(password)
        self.assertTrue(PasswordUtils.verify_password(password, hashed))
        self.assertFalse(PasswordUtils.verify_password("wrongPassword", hashed))

    def test_jwt_utils_create_and_decode(self):
        access_token, refresh_token = JWTUtils.create_tokens("user123", "alice")
        decoded = JWTUtils.decode_token(access_token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.get("user_id"), "user123")
        self.assertEqual(decoded.get("username"), "alice")


if __name__ == '__main__':
    unittest.main()
