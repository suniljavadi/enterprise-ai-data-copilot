from functools import lru_cache

from app.core.config import get_settings
from app.llm.provider import LLMProvider
from app.llm.providers.mock import MockLLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.llm_api_key:
        from app.llm.providers.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider()
    return MockLLMProvider()
