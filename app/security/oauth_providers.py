"""Pluggable OAuth provider registry (Google first)."""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass

# from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import AppException


@dataclass
class OAuthUserInfo:
    provider: str
    provider_user_id: str
    email: str | None
    email_verified: bool = False
    name: str | None = None


class OAuthProvider(ABC):
    """OAuth 2.0 authorization-code provider."""

    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Whether client credentials are present."""

    @abstractmethod
    def build_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Build the provider authorize URL."""

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthUserInfo:
        """Exchange authorization code for normalized user info."""


class GoogleOAuthProvider(OAuthProvider):
    name = "google"
    authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"

    def is_configured(self) -> bool:
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

    def build_authorize_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthUserInfo:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_response = await client.post(
                self.token_endpoint,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_response.status_code >= 400:
                raise AppException("OAuth token exchange failed", status_code=400)
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            if not access_token:
                raise AppException(
                    "OAuth provider did not return an access token", status_code=400
                )

            userinfo_response = await client.get(
                self.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_response.status_code >= 400:
                raise AppException("Failed to fetch OAuth user info", status_code=400)
            profile = userinfo_response.json()

        provider_user_id = str(profile.get("sub") or "")
        if not provider_user_id:
            raise AppException("OAuth provider user id missing", status_code=400)
        return OAuthUserInfo(
            provider=self.name,
            provider_user_id=provider_user_id,
            email=(profile.get("email") or None),
            email_verified=bool(profile.get("email_verified")),
            name=profile.get("name"),
        )


class OAuthProviderRegistry:
    """Register and resolve OAuth providers by name."""

    def __init__(self) -> None:
        self._providers: dict[str, OAuthProvider] = {}

    def register(self, provider: OAuthProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> OAuthProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise AppException(f"Unknown OAuth provider '{name}'", status_code=404)
        if not provider.is_configured():
            raise AppException(
                f"OAuth provider '{name}' is not configured", status_code=503
            )
        return provider

    def list_configured(self) -> list[str]:
        return [
            name
            for name, provider in self._providers.items()
            if provider.is_configured()
        ]


def build_default_oauth_registry() -> OAuthProviderRegistry:
    registry = OAuthProviderRegistry()
    registry.register(GoogleOAuthProvider())
    return registry


def new_oauth_state() -> str:
    return secrets.token_urlsafe(24)


def provider_redirect_uri(provider: str) -> str:
    base = settings.APP_PUBLIC_URL.rstrip("/")
    return f"{base}/api/v1/auth/oauth/{provider}/callback"
