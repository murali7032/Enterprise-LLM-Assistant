import pytest

from app.memory.conversation_memory import ConversationMemory
from app.models.chat_request import ChatRequest
from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.security.guardrails import PromptGuardrails
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService
from tests.conftest import FakeProvider


def test_prompt_builder_includes_history() -> None:
    builder = PromptBuilder()
    prompt = builder.build_chat_prompt(
        question="What did I ask before?",
        history=[
            {"role": "user", "content": "My name is Murali"},
            {"role": "assistant", "content": "Hello Murali"},
        ],
    )
    assert "Conversation History:" in prompt
    assert "My name is Murali" in prompt
    assert "What did I ask before?" in prompt


def test_conversation_memory_char_trim() -> None:
    memory = ConversationMemory()
    memory.append("s1", "user", "a" * 100)
    memory.append("s1", "assistant", "b" * 100)
    memory.append("s1", "user", "recent question")

    history = memory.get_history("s1", limit=10, max_chars=120)
    assert history[-1]["content"] == "recent question"
    assert sum(len(message["content"]) for message in history) <= 120


@pytest.mark.asyncio
async def test_chat_service_uses_memory_in_prompt(monkeypatch) -> None:
    monkeypatch.setattr("app.services.chat_service.settings.MEMORY_ENABLED", True)
    memory = ConversationMemory()
    memory.append("session-1", "user", "My favorite color is blue")
    memory.append("session-1", "assistant", "Noted.")

    captured_prompts: list[str] = []

    class CapturingLLMService:
        async def generate(self, prompt: str):
            captured_prompts.append(prompt)
            from app.models.llm_response import LLMResult

            return LLMResult(content="Your favorite color is blue.", model="fake")

    service = ChatService(
        llm_service=CapturingLLMService(),
        prompt_builder=PromptBuilder(),
        output_parser=OutputParser(),
        guardrails=PromptGuardrails(),
        memory=memory,
    )
    response = await service.chat(
        ChatRequest(question="What is my favorite color?", session_id="session-1")
    )

    assert "My favorite color is blue" in captured_prompts[0]
    assert response.answer == "Your favorite color is blue."
    assert len(memory.get_history("session-1")) == 4


@pytest.mark.asyncio
async def test_chat_service_disables_memory_when_requested(monkeypatch) -> None:
    monkeypatch.setattr("app.services.chat_service.settings.MEMORY_ENABLED", True)
    memory = ConversationMemory()
    memory.append("session-1", "user", "Secret context")

    captured_prompts: list[str] = []

    class CapturingLLMService:
        async def generate(self, prompt: str):
            captured_prompts.append(prompt)
            from app.models.llm_response import LLMResult

            return LLMResult(content="ok", model="fake")

    service = ChatService(
        llm_service=CapturingLLMService(),
        prompt_builder=PromptBuilder(),
        output_parser=OutputParser(),
        guardrails=PromptGuardrails(),
        memory=memory,
    )
    await service.chat(
        ChatRequest(question="hello", session_id="session-1", use_memory=False)
    )

    assert "Secret context" not in captured_prompts[0]
    assert len(memory.get_history("session-1")) == 1
