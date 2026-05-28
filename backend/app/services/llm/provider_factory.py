import os
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAIProvider


_cached_provider = None


def get_llm_provider() -> LLMProvider:
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider

    provider = os.getenv("LLM_PROVIDER")
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"

    if use_mock:
        # Backward compatibility
        provider = "mock"
    
    if not provider:
        provider = "mock" if use_mock else "openai"

    if provider == "mock":
        _cached_provider = MockProvider()
    elif provider == "openai":
        _cached_provider = OpenAIProvider()
    else:
        # Default to mock
        _cached_provider = MockProvider()

    return _cached_provider


async def close_llm_provider():
    global _cached_provider
    if _cached_provider is not None:
        await _cached_provider.close()
        _cached_provider = None
