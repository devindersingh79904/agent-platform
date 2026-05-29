import os
from app.services.llm.base import LLMProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAIProvider


_cached_providers = {}

def get_llm_provider(model: str = None) -> LLMProvider:
    global _cached_providers
    
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    if use_mock:
        if "mock" not in _cached_providers:
            _cached_providers["mock"] = MockProvider()
        return _cached_providers["mock"]

    # Determine provider by model
    provider = "openai"
    if model and ("llama" in model.lower() or "mixtral" in model.lower() or "gemma" in model.lower() or "groq" in model.lower()):
        provider = "groq"
    elif model and "gemini" in model.lower():
        provider = "google"
    elif os.getenv("LLM_PROVIDER") == "groq":
        provider = "groq"
    elif os.getenv("LLM_PROVIDER") == "google":
        provider = "google"
    
    if provider not in _cached_providers:
        if provider == "groq":
            from app.services.llm.groq_provider import GroqProvider
            _cached_providers["groq"] = GroqProvider()
        elif provider == "google":
            from app.services.llm.google_provider import GoogleProvider
            _cached_providers["google"] = GoogleProvider()
        else:
            _cached_providers["openai"] = OpenAIProvider()
            
    return _cached_providers[provider]

async def close_llm_provider():
    global _cached_providers
    for provider in _cached_providers.values():
        await provider.close()
    _cached_providers.clear()



