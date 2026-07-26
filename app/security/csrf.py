"""CSRF double-submit cookie validation."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from app.core.config import settings


def validate_csrf(request: Request) -> None:
    """Require matching CSRF cookie and header for state-changing browser requests."""
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
