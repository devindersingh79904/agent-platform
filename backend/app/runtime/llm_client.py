from typing import Any, Dict, List, Optional
from app.services.llm.base import LLMResponse, estimate_cost, LLMProvider as BaseLLMClient
from app.services.llm.mock_provider import MockProvider as MockLLMClient
from app.services.llm.openai_provider import OpenAIProvider as OpenAIClient
from app.services.llm.provider_factory import get_llm_provider


def get_llm_client() -> BaseLLMClient:
    return get_llm_provider()


class LLMClient(BaseLLMClient):
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        tools: List[Dict[str, Any]] | None = None,
        tool_choice: str | Dict[str, Any] | None = "auto",
        messages: List[Dict[str, Any]] | None = None,
    ) -> LLMResponse:
        return await get_llm_client().generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            tools=tools,
            tool_choice=tool_choice,
            messages=messages,
        )
