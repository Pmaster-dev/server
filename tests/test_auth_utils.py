import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Mock external cache_db module before importing auth.utils
sys.modules['cache_db'] = MagicMock()
sys.modules['cache_db.redis_client'] = MagicMock()
sys.modules['cache_db.models'] = MagicMock()

from flask import Flask, jsonify
from auth.utils import login_required

class TestLoginRequiredSecurity(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        @self.app.route('/protected')
        @login_required
        def protected_route():
            return jsonify({'message': 'success'})

        self.client = self.app.test_client()

    @patch('auth.utils.verify_jwt_in_request')
    def test_login_required_does_not_leak_exception_details(self, mock_verify):
        # Simulate an exception with sensitive internal details during JWT verification
        sensitive_error_msg = "Database connection string postgresql://user:secretpass@localhost/db failed"
        mock_verify.side_effect = Exception(sensitive_error_msg)

        response = self.client.get('/protected')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertEqual(data.get('error'), 'Unauthorized')
        self.assertNotIn('details', data)
        self.assertNotIn('secretpass', str(data))

if __name__ == '__main__':
    unittest.main()
