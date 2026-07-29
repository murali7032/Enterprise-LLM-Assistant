from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DocumentRecord
from app.repositories.document_repository import DocumentRepository


class PostgresDocumentRepository(DocumentRepository):
    """PostgreSQL-backed document metadata repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_document(
        self,
        document_id: str,
        filename: str,
        collection: str,
        chunk_count: int,
        metadata: dict[str, Any],
    ) -> None:
        record = DocumentRecord(
            document_id=document_id,
            filename=filename,
            collection=collection,
            chunk_count=chunk_count,
            metadata_json=metadata,
        )
        self._session.add(record)
        await self._session.commit()

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        result = await self._session.execute(
            select(DocumentRecord).where(DocumentRecord.document_id == document_id)
        )
        record = result.scalar_one_or_none()
        return record.to_dict() if record else None

    async def list_documents(
        self, collection: str | None = None
    ) -> list[dict[str, Any]]:
        query = select(DocumentRecord)
        if collection:
            query = query.where(DocumentRecord.collection == collection)
        result = await self._session.execute(
            query.order_by(DocumentRecord.created_at.desc())
        )
        return [record.to_dict() for record in result.scalars().all()]

    async def delete_document(self, document_id: str) -> bool:
        result = await self._session.execute(
            select(DocumentRecord).where(DocumentRecord.document_id == document_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        self._session.delete(record)
        await self._session.commit()
        return True

    async def list_documents_by_session(
        self,
        session_id: str,
        collection: str | None = None,
        ephemeral_only: bool = False,
    ) -> list[dict[str, Any]]:
        query = select(DocumentRecord).where(
            DocumentRecord.metadata_json.contains({"session_id": session_id})
        )
        if ephemeral_only:
            query = query.where(
                DocumentRecord.metadata_json.contains({"ephemeral": True})
            )
        if collection:
            query = query.where(DocumentRecord.collection == collection)
        result = await self._session.execute(
            query.order_by(DocumentRecord.created_at.desc())
        )
        return [record.to_dict() for record in result.scalars().all()]

    async def delete_documents_by_session(
        self,
        session_id: str,
        ephemeral_only: bool = True,
    ) -> list[str]:
        records = await self.list_documents_by_session(
            session_id, ephemeral_only=ephemeral_only
        )
        deleted_ids: list[str] = []
        for record in records:
            if await self.delete_document(record["document_id"]):
                deleted_ids.append(record["document_id"])
        return deleted_ids
