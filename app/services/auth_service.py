"""Authentication application service."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.repositories.user_repository import UserRepository
from app.security.auth_limits import LoginLockoutStore
from app.security.authentication import verify_password
from app.security.oauth_providers import OAuthUserInfo
from app.security.sessions import SessionStore


def _sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "is_active": user["is_active"],
        "email_verified": bool(user.get("email_verified")),
    }


class AuthService:
    """Register/login/session/OAuth orchestration."""

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionStore,
        lockout: LoginLockoutStore | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._lockout = lockout or LoginLockoutStore()

    async def register(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        if len(password) < settings.AUTH_MIN_PASSWORD_LENGTH:
            raise AuthenticationException(
                f"Password must be at least {settings.AUTH_MIN_PASSWORD_LENGTH} characters"
            )
        try:
            user = await self._users.create_user(
                email=email,
                password=password,
                role=settings.DEFAULT_USER_ROLE,
                email_verified=False,
            )
        except ValueError as exc:
            raise AuthenticationException(str(exc)) from exc

        verify_token = await self._users.create_email_verification_token(user["id"])
        await self._users.record_audit(
            "register",
            user_id=user["id"],
            email=user["email"],
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return _sanitize_user(user), verify_token

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        await self._lockout.assert_not_locked(email)
        user = await self._users.get_by_email(email)
        if (
            user is None
            or not user.get("password_hash")
            or not verify_password(password, user["password_hash"])
        ):
            await self._lockout.record_failure(email)
            await self._users.record_audit(
                "login_failed",
                email=email.strip().lower(),
                ip_address=ip_address,
                user_agent=user_agent,
            )
            raise AuthenticationException("Invalid email or password")

        if not user.get("is_active", True):
            raise AuthorizationException("Account is disabled")

        await self._lockout.clear_failures(email)
        session_id = await self._create_session(user, ip_address=ip_address, user_agent=user_agent)
        await self._users.record_audit(
            "login_success",
            user_id=user["id"],
            email=user["email"],
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return _sanitize_user(user), session_id

    async def logout(
        self,
        session_id: str | None,
        *,
        user_id: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if session_id:
            await self._sessions.delete(session_id)
        await self._users.record_audit(
            "logout",
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def logout_all(self, user_id: str) -> int:
        return await self._sessions.delete_all_for_user(user_id)

    async def resolve_session(self, session_id: str | None) -> dict[str, Any] | None:
        if not session_id:
            return None
        data = await self._sessions.get(session_id)
        if not data:
            return None
        user = await self._users.get_by_id(str(data["user_id"]))
        if user is None or not user.get("is_active", True):
            await self._sessions.delete(session_id)
            return None
        await self._sessions.touch(session_id)
        return {
            "subject": user["email"],
            "role": user["role"],
            "user_id": user["id"],
            "email": user["email"],
            "email_verified": bool(user.get("email_verified")),
        }

    async def me(self, user_id: str) -> dict[str, Any]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AuthenticationException("User not found")
        return _sanitize_user(user)

    async def verify_email(self, token: str) -> dict[str, Any]:
        user_id = await self._users.consume_email_verification_token(token)
        if not user_id:
            raise AuthenticationException("Invalid or expired verification token")
        user = await self._users.set_email_verified(user_id)
        if user is None:
            raise AuthenticationException("User not found")
        await self._users.record_audit("email_verified", user_id=user_id, email=user["email"])
        return _sanitize_user(user)

    async def request_password_reset(self, email: str) -> str | None:
        user = await self._users.get_by_email(email)
        if user is None:
            return None
        token = await self._users.create_password_reset_token(user["id"])
        await self._users.record_audit("password_reset_requested", user_id=user["id"], email=user["email"])
        return token

    async def reset_password(self, token: str, new_password: str) -> None:
        if len(new_password) < settings.AUTH_MIN_PASSWORD_LENGTH:
            raise AuthenticationException(
                f"Password must be at least {settings.AUTH_MIN_PASSWORD_LENGTH} characters"
            )
        user_id = await self._users.consume_password_reset_token(token)
        if not user_id:
            raise AuthenticationException("Invalid or expired reset token")
        await self._users.set_password(user_id, new_password)
        await self._sessions.delete_all_for_user(user_id)
        user = await self._users.get_by_id(user_id)
        await self._users.record_audit(
            "password_reset_completed",
            user_id=user_id,
            email=user["email"] if user else None,
        )

    async def login_with_oauth(
        self,
        info: OAuthUserInfo,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[dict[str, Any], str]:
        linked = await self._users.get_oauth_account(info.provider, info.provider_user_id)
        if linked:
            user = await self._users.get_by_id(linked["user_id"])
            if user is None or not user.get("is_active", True):
                raise AuthorizationException("Account is disabled")
        else:
            email = (info.email or "").strip().lower()
            if not email:
                raise AuthenticationException("OAuth provider did not return an email")
            user = await self._users.get_by_email(email)
            if user is None:
                user = await self._users.create_user(
                    email=email,
                    password=None,
                    role=settings.DEFAULT_USER_ROLE,
                    email_verified=info.email_verified,
                )
            elif info.email_verified and not user.get("email_verified"):
                user = await self._users.set_email_verified(user["id"]) or user
            await self._users.link_oauth_account(
                user["id"],
                info.provider,
                info.provider_user_id,
                info.email,
            )

        session_id = await self._create_session(user, ip_address=ip_address, user_agent=user_agent)
        await self._users.record_audit(
            "oauth_login",
            user_id=user["id"],
            email=user["email"],
            ip_address=ip_address,
            user_agent=user_agent,
            detail=info.provider,
        )
        return _sanitize_user(user), session_id

    async def _create_session(
        self,
        user: dict[str, Any],
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> str:
        return await self._sessions.create(
            {
                "user_id": user["id"],
                "role": user["role"],
                "email": user["email"],
                "ip": ip_address,
                "user_agent": (user_agent or "")[:512],
            }
        )
