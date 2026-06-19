from typing import Any
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings


class QdrantClientWrapper:
    """Thin wrapper around the Qdrant SDK."""

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.QDRANT_URL
        self._client = AsyncQdrantClient(url=self._url)

    async def health(self) -> bool:
        """Check Qdrant connectivity."""
        await self._client.get_collections()
        return True

    async def ensure_collection(self, collection: str, vector_size: int) -> None:
        """Create a collection when it does not exist."""
        collections = await self._client.get_collections()
        names = {item.name for item in collections.collections}
        if collection not in names:
            await self._client.create_collection(
                collection_name=collection,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
            )

    async def upsert(
        self,
        collection: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        ids: list[str] | None = None,
    ) -> None:
        """Upsert vectors with payloads."""
        point_ids = ids or [str(uuid4()) for _ in vectors]
        points = [
            qmodels.PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(point_ids, vectors, payloads, strict=True)
        ]
        await self._client.upsert(collection_name=collection, points=points)

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search vectors in a collection."""
        query_filter = None
        if metadata_filter:
            conditions = [
                qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=value))
                for key, value in metadata_filter.items()
            ]
            query_filter = qmodels.Filter(must=conditions)

        results = await self._client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in results
        ]

    async def delete_by_document_id(self, collection: str, document_id: str) -> int:
        """Delete all vectors belonging to a document."""
        document_filter = qmodels.Filter(
            must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=document_id))]
        )
        point_ids: list[str | int] = []
        offset = None
        while True:
            records, offset = await self._client.scroll(
                collection_name=collection,
                scroll_filter=document_filter,
                limit=100,
                offset=offset,
                with_payload=False,
            )
            point_ids.extend(record.id for record in records)
            if offset is None:
                break

        if not point_ids:
            return 0

        await self._client.delete(
            collection_name=collection,
            points_selector=qmodels.PointIdsList(points=point_ids),
        )
        return len(point_ids)
