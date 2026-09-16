import json

from openai import OpenAI

from app.core.config import get_settings
from app.core.exceptions import LLMUnavailableError
from app.llm.provider import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Adapter for OpenAI and any OpenAI-compatible endpoint (Azure OpenAI, vLLM, Ollama, etc.)."""

    def __init__(self):
        settings = get_settings()
        self._model = settings.llm_model
        self._client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url or None)

    def generate(self, prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            raise LLMUnavailableError(f"LLM request failed: {exc.__class__.__name__}") from exc

    def generate_structured(self, prompt: str, schema: dict) -> dict:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as exc:
            raise LLMUnavailableError(f"LLM structured request failed: {exc.__class__.__name__}") from exc
