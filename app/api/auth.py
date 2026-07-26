from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AppException, AuthenticationException
from app.dependencies import get_auth_rate_limiter, get_auth_service, get_oauth_registry, get_session_store
from app.middleware.auth import get_current_user
from app.security.auth_limits import AuthRateLimiter
from app.security.authentication import create_access_token
from app.security.cookies import clear_csrf_cookie, clear_session_cookie, set_csrf_cookie, set_session_cookie
from app.security.csrf import validate_csrf
from app.security.oauth_providers import (
    OAuthProviderRegistry,
    new_oauth_state,
    provider_redirect_uri,
)
from app.security.sessions import SessionStore
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=1)


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.get("/csrf")
async def issue_csrf(response: Response) -> dict[str, str]:
    """Issue a CSRF cookie + token for browser forms."""
    token = set_csrf_cookie(response)
    return {"csrf_token": token}


@router.post("/register")
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    rate_limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
) -> dict[str, Any]:
    """Register a local email/password account."""
    validate_csrf(request)
    ip, ua = _client_meta(request)
    await rate_limiter.check(f"register:{ip or 'unknown'}")
    user, verify_token = await auth_service.register(
        _normalize_email(body.email),
        body.password,
        ip_address=ip,
        user_agent=ua,
    )
    payload: dict[str, Any] = {"user": user, "message": "Registration successful. Verify your email."}
    if settings.DEBUG or settings.AUTH_DEV_TOKEN_ENABLED:
        payload["verification_token"] = verify_token
    set_csrf_cookie(response)
    return payload


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    rate_limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
) -> dict[str, Any]:
    """Password login; sets HttpOnly session cookie."""
    validate_csrf(request)
    ip, ua = _client_meta(request)
    email = _normalize_email(body.email)
    await rate_limiter.check(f"login:{ip or 'unknown'}:{email}")
    user, session_id = await auth_service.login(
        email,
        body.password,
        ip_address=ip,
        user_agent=ua,
    )
    set_session_cookie(response, session_id)
    set_csrf_cookie(response)
    return {"user": user}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Destroy the current session cookie."""
    validate_csrf(request)
    ip, ua = _client_meta(request)
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    resolved = await auth_service.resolve_session(session_id)
    await auth_service.logout(
        session_id,
        user_id=resolved["user_id"] if resolved else None,
        email=resolved["email"] if resolved else None,
        ip_address=ip,
        user_agent=ua,
    )
    clear_session_cookie(response)
    clear_csrf_cookie(response)
    set_csrf_cookie(response)
    return {"message": "Logged out"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Return the currently authenticated user."""
    return {
        "id": user.get("user_id"),
        "email": user.get("email") or user.get("subject"),
        "role": user.get("role"),
        "email_verified": user.get("email_verified", False),
    }


@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Revoke all sessions for the current user."""
    validate_csrf(request)
    user_id = user.get("user_id")
    if not user_id:
        raise AuthenticationException("Session-backed account required")
    count = await auth_service.logout_all(str(user_id))
    clear_session_cookie(response)
    set_csrf_cookie(response)
    return {"message": "All sessions revoked", "revoked": count}


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Confirm email ownership via one-time token."""
    validate_csrf(request)
    user = await auth_service.verify_email(body.token)
    return {"user": user, "message": "Email verified"}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    rate_limiter: AuthRateLimiter = Depends(get_auth_rate_limiter),
) -> dict[str, Any]:
    """Request a password reset token (always returns generic success)."""
    validate_csrf(request)
    ip, _ = _client_meta(request)
    await rate_limiter.check(f"forgot:{ip or 'unknown'}")
    token = await auth_service.request_password_reset(_normalize_email(body.email))
    payload: dict[str, Any] = {"message": "If that email exists, a reset link was issued."}
    if token and (settings.DEBUG or settings.AUTH_DEV_TOKEN_ENABLED):
        payload["reset_token"] = token
    return payload


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Set a new password using a reset token."""
    validate_csrf(request)
    await auth_service.reset_password(body.token, body.password)
    return {"message": "Password updated"}


@router.get("/oauth/providers")
async def list_oauth_providers(
    oauth_registry: OAuthProviderRegistry = Depends(get_oauth_registry),
) -> dict[str, list[str]]:
    """List configured OAuth providers."""
    return {"providers": oauth_registry.list_configured()}


@router.get("/oauth/{provider}/start")
async def oauth_start(
    provider: str,
    sessions: SessionStore = Depends(get_session_store),
    oauth_registry: OAuthProviderRegistry = Depends(get_oauth_registry),
) -> RedirectResponse:
    """Begin OAuth authorization-code flow."""
    oauth_provider = oauth_registry.get(provider)
    state = new_oauth_state()
    redirect_uri = provider_redirect_uri(provider)
    await sessions.set_oauth_state(state, {"provider": provider, "redirect_uri": redirect_uri})
    return RedirectResponse(url=oauth_provider.build_authorize_url(state, redirect_uri))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    auth_service: AuthService = Depends(get_auth_service),
    sessions: SessionStore = Depends(get_session_store),
    oauth_registry: OAuthProviderRegistry = Depends(get_oauth_registry),
) -> RedirectResponse:
    """Finish OAuth flow and set session cookie."""
    if error:
        raise AppException(f"OAuth error: {error}", status_code=400)
    if not code or not state:
        raise AppException("Missing OAuth code or state", status_code=400)

    stored = await sessions.pop_oauth_state(state)
    if not stored or stored.get("provider") != provider:
        raise AppException("Invalid OAuth state", status_code=400)

    oauth_provider = oauth_registry.get(provider)
    redirect_uri = stored.get("redirect_uri") or provider_redirect_uri(provider)
    info = await oauth_provider.exchange_code(code, redirect_uri)
    ip, ua = _client_meta(request)
    _, session_id = await auth_service.login_with_oauth(info, ip_address=ip, user_agent=ua)

    redirect = RedirectResponse(url="/chat/", status_code=303)
    set_session_cookie(redirect, session_id)
    set_csrf_cookie(redirect)
    return redirect


@router.post("/token")
async def create_token(subject: str = "demo-user", role: str = "admin") -> dict[str, str]:
    """Issue a development JWT access token (disabled unless AUTH_DEV_TOKEN_ENABLED)."""
    if not settings.AUTH_DEV_TOKEN_ENABLED and not settings.DEBUG:
        raise AppException("Dev token endpoint is disabled", status_code=404)
    token = create_access_token(subject=subject, role=role)
    return {"access_token": token, "token_type": "bearer"}
