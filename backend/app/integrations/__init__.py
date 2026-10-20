from backend.app.core.config import settings
from backend.app.integrations.llm_base import BaseLLMProvider
from backend.app.integrations.gemini_provider import GeminiProvider
from backend.app.integrations.mock_llm_provider import MockLLMProvider
from backend.app.integrations.speech_provider import get_speech_provider, BaseSpeechProvider

def get_llm_provider() -> BaseLLMProvider:
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider()
    elif settings.LLM_PROVIDER == "gemini":
        # Still return GeminiProvider because it internally gracefully falls back if key is missing or invalid
        return GeminiProvider()
    return MockLLMProvider()

__all__ = [
    "BaseLLMProvider",
    "GeminiProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "get_speech_provider",
    "BaseSpeechProvider"
]
