import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock cache_db module before importing auth.utils
cache_db_mock = MagicMock()
sys.modules['cache_db'] = cache_db_mock
sys.modules['cache_db.redis_client'] = cache_db_mock.redis_client
sys.modules['cache_db.models'] = cache_db_mock.models

from flask import Flask
from auth.utils import login_required, PasswordUtils, JWTUtils


class TestAuthUtils(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

    def test_login_required_does_not_leak_exception_details(self):
        @self.app.route('/protected')
        @login_required
        def protected_route():
            return "success"

        with patch('auth.utils.verify_jwt_in_request', side_effect=RuntimeError("Internal database connection error - secret_db_uri")):
            client = self.app.test_client()
            response = client.get('/protected')

            self.assertEqual(response.status_code, 401)
            data = response.get_json()
            self.assertEqual(data, {'error': 'Unauthorized'})
            # Verify details or stack trace are not in response payload
            self.assertNotIn('details', data)
            self.assertNotIn('secret_db_uri', str(data))

    def test_password_utils_hash_and_verify(self):
        hashed = PasswordUtils.hash_password("supersecret123")
        self.assertTrue(PasswordUtils.verify_password("supersecret123", hashed))
        self.assertFalse(PasswordUtils.verify_password("wrongpassword", hashed))

    def test_jwt_utils_create_and_decode(self):
        access_token, refresh_token = JWTUtils.create_tokens("user123", "testuser")
        decoded = JWTUtils.decode_token(access_token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded['user_id'], "user123")
        self.assertEqual(decoded['username'], "testuser")


if __name__ == '__main__':
    unittest.main()
