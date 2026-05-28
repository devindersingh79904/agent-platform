import os
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAIProvider


def get_llm_provider() -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER")
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"

    if use_mock:
        # Backward compatibility
        provider = "mock"
    
    if not provider:
        provider = "mock" if use_mock else "openai"

    if provider == "mock":
        return MockProvider()
    elif provider == "openai":
        return OpenAIProvider()
    else:
        # Default to mock
        return MockProvider()
