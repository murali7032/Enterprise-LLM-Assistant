from app.parser.output_parser import OutputParser
from app.prompt.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService


class Planner:
    """Plan the next agent action using the LLM."""

    def __init__(
        self,
        llm_service: LLMService,
        prompt_builder: PromptBuilder,
        output_parser: OutputParser,
    ) -> None:
        self._llm_service = llm_service
        self._prompt_builder = prompt_builder
        self._output_parser = output_parser

    async def plan(self, goal: str, observations: list[str], tools: list[str]) -> dict:
        """Generate the next agent step."""
        prompt = self._prompt_builder.build_agent_prompt(goal, observations, tools)
        result = await self._llm_service.generate(prompt)
        return self._output_parser.parse_tool_response(result.content)
