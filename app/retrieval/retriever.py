from typing import Any

from app.clients.qdrant_client import QdrantClientWrapper
from app.core.config import settings
from app.models.document import DocumentChunk


class HybridSearch:
    """Combine vector similarity with lexical overlap scoring."""

    def score(self, query: str, content: str, vector_score: float) -> float:
        """Compute a hybrid relevance score."""
        query_terms = {term.lower() for term in query.split() if term}
        content_terms = {term.lower() for term in content.split() if term}
        overlap = len(query_terms & content_terms)
        lexical_score = overlap / max(len(query_terms), 1)
        return (0.7 * vector_score) + (0.3 * lexical_score)

    def rank(self, query: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Rank search hits using hybrid scoring."""
        ranked = []
        for hit in hits:
            payload = hit.get("payload", {})
            content = str(payload.get("content", ""))
            hybrid_score = self.score(query, content, float(hit.get("score", 0.0)))
            ranked.append({**hit, "hybrid_score": hybrid_score})
        return sorted(ranked, key=lambda item: item["hybrid_score"], reverse=True)


class Reranker:
    """Rerank retrieved chunks."""

    def __init__(self, hybrid_search: HybridSearch) -> None:
        self._hybrid_search = hybrid_search

    def rerank(self, query: str, hits: list[dict[str, Any]], top_n: int | None = None) -> list[DocumentChunk]:
        """Rerank and convert hits into document chunks."""
        limit = top_n or settings.TOP_N
        ranked_hits = self._hybrid_search.rank(query, hits)[:limit]
        return [
            DocumentChunk(
                id=str(hit["id"]),
                content=str(hit.get("payload", {}).get("content", "")),
                score=float(hit.get("hybrid_score", hit.get("score", 0.0))),
                metadata=hit.get("payload", {}),
            )
            for hit in ranked_hits
        ]


class Retriever:
    """Retrieve relevant document chunks from Qdrant."""

    def __init__(
        self,
        qdrant_client: QdrantClientWrapper,
        hybrid_search: HybridSearch,
        reranker: Reranker,
    ) -> None:
        self._qdrant_client = qdrant_client
        self._hybrid_search = hybrid_search
        self._reranker = reranker

    async def retrieve(
        self,
        query_vector: list[float],
        query_text: str,
        collection: str,
        top_k: int | None = None,
        top_n: int | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """Retrieve and rerank document chunks."""
        limit_k = top_k or settings.TOP_K
        hits = await self._qdrant_client.search(
            collection=collection,
            query_vector=query_vector,
            top_k=limit_k,
            metadata_filter=metadata_filter,
        )
        return self._reranker.rerank(query_text, hits, top_n=top_n or limit_k)
