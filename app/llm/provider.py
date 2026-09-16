from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface so business logic never depends on a specific LLM vendor."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        ...

    @abstractmethod
    def generate_structured(self, prompt: str, schema: dict) -> dict:
        ...
