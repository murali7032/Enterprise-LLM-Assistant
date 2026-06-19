
from app.core.config import settings
from app.models.document import DocumentChunk


class PromptBuilder:
    """Build prompts with optional retrieved context and conversation history."""

    def build_chat_prompt(
        self,
        question: str,
        context_chunks: list[DocumentChunk] | None = None,
        history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Build a chat prompt with optional RAG context and conversation history."""
        system = system_prompt or (
            "You are an enterprise AI assistant. Answer accurately using the provided context when available."
        )
        sections = [system]

        if history:
            history_text = "\n".join(
                f"{message['role'].title()}: {message['content']}" for message in history
            )
            sections.extend(["Conversation History:", history_text])

        if context_chunks:
            context_text = "\n\n".join(
                f"[Source {index + 1}]\n{chunk.content}"
                for index, chunk in enumerate(context_chunks[: settings.TOP_N])
            )
            sections.extend(["Context:", context_text])

        sections.extend([f"Question:\n{question}", "Answer:"])
        return "\n\n".join(sections)

    def build_agent_prompt(self, goal: str, observations: list[str], tools: list[str]) -> str:
        """Build an agent planning prompt."""
        history = "\n".join(f"- {item}" for item in observations) or "- None"
        tool_list = ", ".join(tools)
        return (
            "You are an enterprise agent planner.\n"
            f"Goal: {goal}\n"
            f"Available tools: {tool_list}\n"
            f"Observations:\n{history}\n"
            'Respond with JSON: {"thought": "...", "action": "tool_name|finish", "input": "..."}'
        )
