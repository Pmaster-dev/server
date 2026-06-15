import bcrypt
import jwt
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from cache_db.redis_client import redis_client
from cache_db.models import User, RefreshToken
from typing import Tuple, Optional


class PasswordUtils:
    """Password hashing and verification utilities"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hash_: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hash_.encode('utf-8'))
        except Exception:
            return False


class JWTUtils:
    """JWT token utilities"""
    
    @staticmethod
    def create_tokens(user_id: str, username: str) -> Tuple[str, str]:
        """Create access and refresh tokens"""
        access_token = jwt.encode(
            {
                'user_id': user_id,
                'username': username,
                'exp': datetime.utcnow() + timedelta(hours=1),
                'type': 'access'
            },
            os.getenv('JWT_SECRET_KEY', 'jwt-secret'),
            algorithm='HS256'
        )
        
        refresh_token = jwt.encode(
            {
                'user_id': user_id,
                'username': username,
                'exp': datetime.utcnow() + timedelta(days=30),
                'type': 'refresh'
            },
            os.getenv('JWT_SECRET_KEY', 'jwt-secret'),
            algorithm='HS256'
        )
        
        return access_token, refresh_token
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and verify token"""
        try:
            payload = jwt.decode(
                token,
                os.getenv('JWT_SECRET_KEY', 'jwt-secret'),
                algorithms=['HS256']
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


class SessionUtils:
    """Session management utilities"""
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate unique session ID"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def get_device_info(user_agent: str = None) -> dict:
        """Extract device info from user agent"""
        if not user_agent:
            user_agent = request.headers.get('User-Agent', 'Unknown')
        
        # Simple device detection
        if 'Mobile' in user_agent or 'Android' in user_agent:
            device_type = 'mobile'
        elif 'Tablet' in user_agent or 'iPad' in user_agent:
            device_type = 'tablet'
        else:
            device_type = 'desktop'
        
        return {
            'user_agent': user_agent,
            'device_type': device_type,
            'ip_address': request.remote_addr if request else '0.0.0.0',
        }


# Decorators for auth protection

def login_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # Try to get user from cache first
            user_data = redis_client.get_cached_user(user_id)
            if not user_data:
                user = User.query.get(user_id)
                if not user or not user.is_active:
                    return jsonify({'error': 'User not found or inactive'}), 401
                user_data = user.to_dict()
                redis_client.cache_user(user_id, user_data)
            
            g.user_id = user_id
            g.user = user_data
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Unauthorized', 'details': str(e)}), 401
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        user_data = g.user
        if not user_data.get('is_admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def verify_required(f):
    """Decorator to require verified email"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        user_data = g.user
        if not user_data.get('is_verified'):
            return jsonify({'error': 'Email verification required'}), 403
        return f(*args, **kwargs)
    return decorated_function
