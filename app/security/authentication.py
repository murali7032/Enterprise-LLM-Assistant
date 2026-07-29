from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationException, AuthorizationException

ROLE_PERMISSIONS = {
    "admin": {"chat", "documents", "agents", "metrics", "ops"},
    "user": {"chat", "documents", "agents", "ops"},
    "viewer": {"chat"},
}


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": int(expire.timestamp())}
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise AuthenticationException("Invalid or expired token") from exc


def require_permission(role: str, permission: str) -> None:
    """Ensure a role has the required permission."""
    permissions = ROLE_PERMISSIONS.get(role, set())
    if permission not in permissions:
        raise AuthorizationException(f"Role '{role}' cannot access '{permission}'")
