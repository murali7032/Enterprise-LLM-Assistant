from abc import ABC
from abc import abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def generate(
        self,
        prompt: str
    ) -> str:
        """
        Generate response from an LLM.
        """
        pass