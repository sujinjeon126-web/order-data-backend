"""
Authentication middleware for Vercel serverless functions
"""
import os
import jwt
from functools import wraps
from http.server import BaseHTTPRequestHandler
from typing import Optional, Dict, Any, Callable

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from Supabase.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        secret = os.environ.get("SUPABASE_JWT_SECRET")
        if not secret:
            raise ValueError("SUPABASE_JWT_SECRET must be set")

        # Verify and decode token
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated"
        )

        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def get_user_from_request(request_handler: BaseHTTPRequestHandler) -> Optional[Dict[str, Any]]:
    """
    Extract user information from request headers.

    Args:
        request_handler: HTTP request handler instance

    Returns:
        User payload from JWT or None if not authenticated
    """
    # Get Authorization header
    auth_header = request_handler.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove "Bearer " prefix
    return verify_token(token)


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for an endpoint.

    Usage:
        @require_auth
        def my_handler(self, user):
            # user contains decoded JWT payload
            pass
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        user = get_user_from_request(self)

        if not user:
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"data": null, "error": {"message": "Unauthorized", "code": "UNAUTHORIZED"}}')
            return

        # Pass user to the handler function
        return func(self, user, *args, **kwargs)

    return wrapper


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role for an endpoint.

    Usage:
        @require_admin
        def my_handler(self, user):
            # user contains decoded JWT payload and is confirmed to be admin
            pass
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        user = get_user_from_request(self)

        if not user:
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"data": null, "error": {"message": "Unauthorized", "code": "UNAUTHORIZED"}}')
            return

        # Check if user has admin role
        user_metadata = user.get("user_metadata", {})
        role = user_metadata.get("role", "user")

        if role != "admin":
            self.send_response(403)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"data": null, "error": {"message": "Forbidden - Admin access required", "code": "FORBIDDEN"}}')
            return

        # Pass user to the handler function
        return func(self, user, *args, **kwargs)

    return wrapper
