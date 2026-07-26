from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.dependencies import get_auth_service
from app.security.authentication import decode_access_token, require_permission
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    """Resolve the authenticated user from session cookie or bearer token."""
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if session_id:
        session_user = await auth_service.resolve_session(session_id)
        if session_user is not None:
            return session_user

    if credentials is not None:
        payload = decode_access_token(credentials.credentials)
        return {
            "subject": payload.get("sub"),
            "role": payload.get("role", "viewer"),
            "user_id": payload.get("user_id"),
            "email": payload.get("sub"),
            "email_verified": True,
        }

    raise HTTPException(status_code=401, detail="Authentication required")


def require_auth_permission(permission: str):
    """Dependency factory for RBAC-protected endpoints."""

    async def _dependency(user: dict = Depends(get_current_user)) -> dict:
        require_permission(user["role"], permission)
        return user

    return _dependency
