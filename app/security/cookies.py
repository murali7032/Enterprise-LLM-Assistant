"""HttpOnly session and CSRF cookie helpers."""

from __future__ import annotations

import secrets

from fastapi import Response

from app.core.config import settings


def set_session_cookie(response: Response, session_id: str) -> None:
    """Attach the opaque session cookie to a response."""
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Expire the session cookie."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
    )


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    """Set a readable CSRF cookie (double-submit pattern)."""
    value = token or new_csrf_token()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=value,
        max_age=settings.SESSION_TTL_SECONDS,
        httponly=False,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
        path="/",
    )
    return value


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path="/",
        secure=settings.SESSION_COOKIE_SECURE,
        samesite=settings.SESSION_COOKIE_SAMESITE,  # type: ignore[arg-type]
    )
