from collections.abc import AsyncIterator
from uuid import uuid4

from app.clients.embedding_client import EmbeddingClient
from app.core.config import settings
from app.memory.conversation_memory import ConversationMemory
from app.models.chat_request import ChatRequest
from app.models.chat_response import ChatResponse
from app.models.document import DocumentChunk
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.retrieval.retriever import Retriever
from app.security.guardrails import PromptGuardrails
from app.services.llm_service import LLMService


class ChatService:
    """Chat business logic with optional RAG, guardrails, and conversation memory."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        output_parser: OutputParser,
        guardrails: PromptGuardrails,
        retriever: Retriever | None = None,
        embedding_client: EmbeddingClient | None = None,
        memory: ConversationMemory | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._prompt_builder = prompt_builder
        self._output_parser = output_parser
        self._guardrails = guardrails
        self._retriever = retriever
        self._embedding_client = embedding_client
        self._memory = memory or ConversationMemory()

    def _detect_intent(self, question: str) -> str:
        """Simple intent detection for routing."""
        lowered = question.lower()
        if any(keyword in lowered for keyword in ("search", "document", "policy", "knowledge")):
            return "rag"
        return "chat"

    def _get_history(self, session_id: str, use_memory: bool) -> list[dict[str, str]]:
        """Load conversation history when memory is enabled."""
        if not use_memory or not settings.MEMORY_ENABLED:
            return []
        return self._memory.get_history(session_id)

    async def _retrieve_context(self, request: ChatRequest, use_rag: bool) -> list[DocumentChunk]:
        """Retrieve RAG context chunks when enabled."""
        if not use_rag or self._retriever is None or self._embedding_client is None:
            return []

        embeddings = await self._embedding_client.embed([request.question])
        return await self._retriever.retrieve(
            query_vector=embeddings[0],
            query_text=request.question,
            collection=request.collection,
            metadata_filter=request.metadata_filter or None,
        )

    async def _build_prompt(
        self,
        request: ChatRequest,
        session_id: str,
        use_rag: bool,
    ) -> tuple[str, list[DocumentChunk]]:
        """Build the LLM prompt with optional memory and RAG context."""
        history = self._get_history(session_id, request.use_memory)
        context_chunks = await self._retrieve_context(request, use_rag)
        prompt = self._prompt_builder.build_chat_prompt(
            question=request.question,
            context_chunks=context_chunks,
            history=history,
        )
        return prompt, context_chunks

    def _save_exchange(self, session_id: str, question: str, answer: str, use_memory: bool) -> None:
        """Persist the user and assistant messages for a session."""
        if not use_memory or not settings.MEMORY_ENABLED:
            return
        self._memory.append(session_id, "user", question)
        self._memory.append(session_id, "assistant", answer)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request."""
        self._guardrails.validate(request.question)
        session_id = request.session_id or str(uuid4())
        use_rag = request.use_rag or self._detect_intent(request.question) == "rag"

        prompt, context_chunks = await self._build_prompt(request, session_id, use_rag)
        result = await self._llm_service.generate(prompt)
        answer = self._output_parser.parse_text(result.content)

        self._save_exchange(session_id, request.question, answer, request.use_memory)

        return ChatResponse(
            answer=answer,
            session_id=session_id,
            sources=[chunk.model_dump() for chunk in context_chunks],
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            total_tokens=result.total_tokens,
            cost_usd=result.cost_usd,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream a chat response."""
        self._guardrails.validate(request.question)
        session_id = request.session_id or str(uuid4())
        use_rag = request.use_rag or self._detect_intent(request.question) == "rag"

        prompt, _context_chunks = await self._build_prompt(request, session_id, use_rag)
        chunks: list[str] = []
        async for chunk in self._llm_service.stream(prompt):
            chunks.append(chunk)
            yield chunk

        answer = "".join(chunks)
        self._save_exchange(session_id, request.question, answer, request.use_memory)
