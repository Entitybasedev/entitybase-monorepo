"""Password hashing and signed-token helpers for authentication.

Uses only the standard library: scrypt for password hashing and an
HMAC-SHA256 signed compact token (JWT-style header.payload.signature) for
sessions. The secret comes from settings.auth_secret; when it is empty
auth is disabled and no token is required.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time

from models.data.rest_api.v1.entitybase.response.auth import TokenPayload

logger = logging.getLogger(__name__)

HASH_PREFIX = "scrypt"
TOKEN_ALG = "HS256"


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """Hash a password with scrypt and a random salt.

    Returns "scrypt$salt_hex$hash_hex".
    """
    if not password:
        raise ValueError("Password must not be empty")
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{HASH_PREFIX}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored scrypt hash."""
    if not password or not stored:
        return False
    parts = stored.split("$")
    if len(parts) != 3 or parts[0] != HASH_PREFIX:
        return False
    try:
        salt = bytes.fromhex(parts[1])
        expected = bytes.fromhex(parts[2])
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(digest, expected)
    except ValueError:
        return False


def create_token(
    user_id: int, username: str, secret: str, expiry_hours: int
) -> str:
    """Create a signed token for the user (JWT-style, HS256)."""
    if not secret:
        raise ValueError("auth_secret is not configured")
    header = {"alg": TOKEN_ALG, "typ": "JWT"}
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + expiry_hours * 3600,
    }
    segments = [
        _b64url_encode(json.dumps(header).encode()),
        _b64url_encode(json.dumps(payload).encode()),
    ]
    signing_input = ".".join(segments).encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


def decode_token(token: str, secret: str) -> TokenPayload:
    """Verify a token's signature and expiry; return its payload.

    Raises ValueError when the token is malformed, tampered with,
    expired, or when the secret does not match.
    """
    if not secret:
        raise ValueError("auth_secret is not configured")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    try:
        signature = _b64url_decode(parts[2])
    except ValueError as e:
        raise ValueError("Malformed token") from e
    expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid token signature")
    try:
        payload = json.loads(_b64url_decode(parts[1]))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError("Malformed token payload") from e
    if not isinstance(payload, dict):
        raise ValueError("Malformed token payload")
    exp = payload.get("exp", 0)
    if not isinstance(exp, (int, float)) or exp < time.time():
        logger.info("Token rejected: expired")
        raise ValueError("Token expired")
    user_id = payload.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Invalid user_id in token")
    exp = int(exp)
    username = payload.get("username", "")
    if not isinstance(username, str):
        raise ValueError("Invalid username in token")
    return TokenPayload(user_id=user_id, username=username, exp=exp)
