
from app.core.config import settings
from app.models.document import DocumentChunk


class PromptBuilder:
    """Build prompts with optional retrieved context."""

    def build_chat_prompt(
        self,
        question: str,
        context_chunks: list[DocumentChunk] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Build a chat prompt with optional RAG context."""
        system = system_prompt or (
            "You are an enterprise AI assistant. Answer accurately using the provided context when available."
        )
        if not context_chunks:
            return f"{system}\n\nQuestion:\n{question}\n\nAnswer:"

        context_text = "\n\n".join(
            f"[Source {index + 1}]\n{chunk.content}"
            for index, chunk in enumerate(context_chunks[: settings.TOP_N])
        )
        return (
            f"{system}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question:\n{question}\n\n"
            f"Answer using the context when relevant:"
        )

    def build_agent_prompt(self, goal: str, observations: list[str], tools: list[str]) -> str:
        """Build an agent planning prompt."""
        history = "\n".join(f"- {item}" for item in observations) or "- None"
        tool_list = ", ".join(tools)
        return (
            "You are an enterprise agent planner.\n"
            f"Goal: {goal}\n"
            f"Available tools: {tool_list}\n"
            f"Observations:\n{history}\n"
            "Respond with JSON: {\"thought\": \"...\", \"action\": \"tool_name|finish\", \"input\": \"...\"}"
        )
