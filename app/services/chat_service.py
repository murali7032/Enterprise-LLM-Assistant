from collections.abc import AsyncIterator
from uuid import uuid4

from app.clients.openai_client import OpenAIClient
from app.core.config import settings
from app.memory.conversation_memory import ConversationMemory
from app.models.chat_request import ChatRequest
from app.models.chat_response import ChatResponse
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.retrieval.retriever import Retriever
from app.security.guardrails import PromptGuardrails
from app.services.llm_service import LLMService


class ChatService:
    """Chat business logic with optional RAG and guardrails."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        output_parser: OutputParser,
        guardrails: PromptGuardrails,
        retriever: Retriever | None = None,
        openai_client: OpenAIClient | None = None,
        memory: ConversationMemory | None = None,
    ) -> None:
        self._llm_service = llm_service
        self._prompt_builder = prompt_builder
        self._output_parser = output_parser
        self._guardrails = guardrails
        self._retriever = retriever
        self._openai_client = openai_client
        self._memory = memory or ConversationMemory()

    def _detect_intent(self, question: str) -> str:
        """Simple intent detection for routing."""
        lowered = question.lower()
        if any(keyword in lowered for keyword in ("search", "document", "policy", "knowledge")):
            return "rag"
        return "chat"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Process a chat request."""
        self._guardrails.validate(request.question)
        session_id = request.session_id or str(uuid4())
        intent = self._detect_intent(request.question)
        use_rag = request.use_rag or intent == "rag"

        context_chunks = []
        if use_rag and self._retriever is not None and self._openai_client is not None:
            embeddings = await self._openai_client.embed([request.question], model=settings.EMBEDDING_MODEL)
            context_chunks = await self._retriever.retrieve(
                query_vector=embeddings[0],
                query_text=request.question,
                collection=request.collection,
                metadata_filter=request.metadata_filter or None,
            )

        prompt = self._prompt_builder.build_chat_prompt(request.question, context_chunks)
        result = await self._llm_service.generate(prompt)
        answer = self._output_parser.parse_text(result.content)

        self._memory.append(session_id, "user", request.question)
        self._memory.append(session_id, "assistant", answer)

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
        prompt = self._prompt_builder.build_chat_prompt(request.question)
        async for chunk in self._llm_service.stream(prompt):
            yield chunk
