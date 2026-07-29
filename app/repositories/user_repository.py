"""User persistence interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuthAuditEventRecord,
    EmailVerificationTokenRecord,
    OAuthAccountRecord,
    PasswordResetTokenRecord,
    UserRecord,
)
from app.security.authentication import hash_password


class UserRepository(ABC):
    """Identity store for local and OAuth users."""

    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str | None,
        role: str,
        *,
        email_verified: bool = False,
    ) -> dict[str, Any]:
        """Create a user. Password may be None for OAuth-only accounts."""

    @abstractmethod
    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch user by email (includes password_hash)."""

    @abstractmethod
    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Fetch user by id (includes password_hash)."""

    @abstractmethod
    async def set_email_verified(self, user_id: str) -> dict[str, Any] | None:
        """Mark email verified now."""

    @abstractmethod
    async def set_password(self, user_id: str, password: str) -> None:
        """Update password hash."""

    @abstractmethod
    async def link_oauth_account(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        email: str | None,
    ) -> None:
        """Attach an OAuth identity to a user."""

    @abstractmethod
    async def get_oauth_account(
        self, provider: str, provider_user_id: str
    ) -> dict[str, Any] | None:
        """Lookup OAuth link."""

    @abstractmethod
    async def create_email_verification_token(
        self, user_id: str, ttl_hours: int = 24
    ) -> str:
        """Issue email verification token."""

    @abstractmethod
    async def consume_email_verification_token(self, token: str) -> str | None:
        """Mark verification token used; return user_id if valid."""

    @abstractmethod
    async def create_password_reset_token(
        self, user_id: str, ttl_hours: int = 1
    ) -> str:
        """Issue password reset token."""

    @abstractmethod
    async def consume_password_reset_token(self, token: str) -> str | None:
        """Mark reset token used; return user_id if valid."""

    @abstractmethod
    async def record_audit(
        self,
        event_type: str,
        *,
        user_id: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Append an auth audit event."""


def _public_user(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "email": record["email"],
        "role": record["role"],
        "is_active": record["is_active"],
        "email_verified": record.get("email_verified", False),
        "password_hash": record.get("password_hash"),
        "created_at": record.get("created_at"),
    }


class InMemoryUserRepository(UserRepository):
    """In-process user store for tests and local runs without Postgres."""

    def __init__(self) -> None:
        self._users: dict[str, dict[str, Any]] = {}
        self._by_email: dict[str, str] = {}
        self._oauth: dict[tuple[str, str], dict[str, Any]] = {}
        self._verify_tokens: dict[str, dict[str, Any]] = {}
        self._reset_tokens: dict[str, dict[str, Any]] = {}
        self._audit: list[dict[str, Any]] = []

    async def create_user(
        self,
        email: str,
        password: str | None,
        role: str,
        *,
        email_verified: bool = False,
    ) -> dict[str, Any]:
        normalized = email.strip().lower()
        if normalized in self._by_email:
            raise ValueError("Email already registered")
        user_id = str(uuid4())
        now = datetime.now(UTC).isoformat()
        record = {
            "id": user_id,
            "email": normalized,
            "password_hash": hash_password(password) if password else None,
            "role": role,
            "is_active": True,
            "email_verified": email_verified,
            "created_at": now,
        }
        self._users[user_id] = record
        self._by_email[normalized] = user_id
        return _public_user(record)

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        user_id = self._by_email.get(email.strip().lower())
        if not user_id:
            return None
        return _public_user(self._users[user_id])

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        record = self._users.get(user_id)
        return _public_user(record) if record else None

    async def set_email_verified(self, user_id: str) -> dict[str, Any] | None:
        record = self._users.get(user_id)
        if not record:
            return None
        record["email_verified"] = True
        return _public_user(record)

    async def set_password(self, user_id: str, password: str) -> None:
        record = self._users[user_id]
        record["password_hash"] = hash_password(password)

    async def link_oauth_account(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        email: str | None,
    ) -> None:
        self._oauth[(provider, provider_user_id)] = {
            "user_id": user_id,
            "provider": provider,
            "provider_user_id": provider_user_id,
            "email": email,
        }

    async def get_oauth_account(
        self, provider: str, provider_user_id: str
    ) -> dict[str, Any] | None:
        return self._oauth.get((provider, provider_user_id))

    async def create_email_verification_token(
        self, user_id: str, ttl_hours: int = 24
    ) -> str:
        token = uuid4().hex
        self._verify_tokens[token] = {
            "user_id": user_id,
            "expires_at": datetime.now(UTC) + timedelta(hours=ttl_hours),
            "used": False,
        }
        return token

    async def consume_email_verification_token(self, token: str) -> str | None:
        data = self._verify_tokens.get(token)
        if not data or data["used"] or data["expires_at"] < datetime.now(UTC):
            return None
        data["used"] = True
        return data["user_id"]

    async def create_password_reset_token(
        self, user_id: str, ttl_hours: int = 1
    ) -> str:
        token = uuid4().hex
        self._reset_tokens[token] = {
            "user_id": user_id,
            "expires_at": datetime.now(UTC) + timedelta(hours=ttl_hours),
            "used": False,
        }
        return token

    async def consume_password_reset_token(self, token: str) -> str | None:
        data = self._reset_tokens.get(token)
        if not data or data["used"] or data["expires_at"] < datetime.now(UTC):
            return None
        data["used"] = True
        return data["user_id"]

    async def record_audit(
        self,
        event_type: str,
        *,
        user_id: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
    ) -> None:
        self._audit.append(
            {
                "event_type": event_type,
                "user_id": user_id,
                "email": email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "detail": detail,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )


class PostgresUserRepository(UserRepository):
    """PostgreSQL-backed user identity store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_dict(self, user: UserRecord) -> dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "password_hash": user.password_hash,
            "role": user.role,
            "is_active": user.is_active,
            "email_verified": user.email_verified_at is not None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }

    async def create_user(
        self,
        email: str,
        password: str | None,
        role: str,
        *,
        email_verified: bool = False,
    ) -> dict[str, Any]:
        normalized = email.strip().lower()
        existing = await self.get_by_email(normalized)
        if existing:
            raise ValueError("Email already registered")
        user = UserRecord(
            id=str(uuid4()),
            email=normalized,
            password_hash=hash_password(password) if password else None,
            role=role,
            is_active=True,
            email_verified_at=datetime.now(UTC) if email_verified else None,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return self._to_dict(user)

    async def get_by_email(self, email: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.email == email.strip().lower())
        )
        user = result.scalar_one_or_none()
        return self._to_dict(user) if user else None

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        )
        user = result.scalar_one_or_none()
        return self._to_dict(user) if user else None

    async def set_email_verified(self, user_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.email_verified_at = datetime.now(UTC)
        user.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(user)
        return self._to_dict(user)

    async def set_password(self, user_id: str, password: str) -> None:
        result = await self._session.execute(
            select(UserRecord).where(UserRecord.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return
        user.password_hash = hash_password(password)
        user.updated_at = datetime.now(UTC)
        await self._session.commit()

    async def link_oauth_account(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        email: str | None,
    ) -> None:
        existing = await self.get_oauth_account(provider, provider_user_id)
        if existing:
            return
        self._session.add(
            OAuthAccountRecord(
                id=str(uuid4()),
                user_id=user_id,
                provider=provider,
                provider_user_id=provider_user_id,
                email=email,
            )
        )
        await self._session.commit()

    async def get_oauth_account(
        self, provider: str, provider_user_id: str
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(OAuthAccountRecord).where(
                OAuthAccountRecord.provider == provider,
                OAuthAccountRecord.provider_user_id == provider_user_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            return None
        return {
            "user_id": account.user_id,
            "provider": account.provider,
            "provider_user_id": account.provider_user_id,
            "email": account.email,
        }

    async def create_email_verification_token(
        self, user_id: str, ttl_hours: int = 24
    ) -> str:
        token = uuid4().hex
        self._session.add(
            EmailVerificationTokenRecord(
                token=token,
                user_id=user_id,
                expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
            )
        )
        await self._session.commit()
        return token

    async def consume_email_verification_token(self, token: str) -> str | None:
        result = await self._session.execute(
            select(EmailVerificationTokenRecord).where(
                EmailVerificationTokenRecord.token == token
            )
        )
        row = result.scalar_one_or_none()
        if not row or row.used_at is not None or row.expires_at < datetime.now(UTC):
            return None
        row.used_at = datetime.now(UTC)
        await self._session.commit()
        return row.user_id

    async def create_password_reset_token(
        self, user_id: str, ttl_hours: int = 1
    ) -> str:
        token = uuid4().hex
        self._session.add(
            PasswordResetTokenRecord(
                token=token,
                user_id=user_id,
                expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
            )
        )
        await self._session.commit()
        return token

    async def consume_password_reset_token(self, token: str) -> str | None:
        result = await self._session.execute(
            select(PasswordResetTokenRecord).where(
                PasswordResetTokenRecord.token == token
            )
        )
        row = result.scalar_one_or_none()
        if not row or row.used_at is not None or row.expires_at < datetime.now(UTC):
            return None
        row.used_at = datetime.now(UTC)
        await self._session.commit()
        return row.user_id

    async def record_audit(
        self,
        event_type: str,
        *,
        user_id: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
    ) -> None:
        self._session.add(
            AuthAuditEventRecord(
                user_id=user_id,
                email=email,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=(user_agent or "")[:512] or None,
                detail=detail,
            )
        )
        await self._session.commit()
