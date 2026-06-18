from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import AuthenticationException, AuthorizationException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_PERMISSIONS = {
    "admin": {"chat", "documents", "agents", "metrics"},
    "user": {"chat", "documents"},
    "viewer": {"chat"},
}


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthenticationException("Invalid or expired token") from exc


def require_permission(role: str, permission: str) -> None:
    """Ensure a role has the required permission."""
    permissions = ROLE_PERMISSIONS.get(role, set())
    if permission not in permissions:
        raise AuthorizationException(f"Role '{role}' cannot access '{permission}'")
