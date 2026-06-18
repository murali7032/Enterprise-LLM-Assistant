from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.authentication import decode_access_token, require_permission

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Resolve the authenticated user from a bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = decode_access_token(credentials.credentials)
    return {"subject": payload.get("sub"), "role": payload.get("role", "viewer")}


def require_auth_permission(permission: str):
    """Dependency factory for RBAC-protected endpoints."""

    def _dependency(user: dict = Depends(get_current_user)) -> dict:
        require_permission(user["role"], permission)
        return user

    return _dependency
