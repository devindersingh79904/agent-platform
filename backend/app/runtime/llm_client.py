import asyncio
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - exercised only when dependencies are not installed yet.
    AsyncOpenAI = None


MODEL_PRICING = {
    "gpt-4o-mini": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
    }
}


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str

    @property
    def estimated_cost(self) -> float:
        return estimate_cost(self.model, self.prompt_tokens, self.completion_tokens)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    input_cost = (prompt_tokens / 1_000_000) * pricing["input_per_1m"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output_per_1m"]
    return input_cost + output_cost


class BaseLLMClient:
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        raise NotImplementedError

    async def invoke(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: List[Any] | None = None,
        limits: dict | None = None,
    ) -> Dict[str, Any]:
        system_prompt = ""
        user_parts = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system" and not system_prompt:
                system_prompt = content
            elif content:
                user_parts.append(content)

        response = await self.generate(
            system_prompt=system_prompt,
            user_prompt="\n\n".join(user_parts),
            model=model,
        )
        return {
            "content": response.text,
            "usage": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
                "estimated_cost": f"{response.estimated_cost:.8f}",
                "model": response.model,
            },
        }


class MockLLMClient(BaseLLMClient):
    def __init__(self):
        self.mock_delay = int(os.getenv("MOCK_LLM_DELAY_MS", "800"))

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        if self.mock_delay > 0:
            await asyncio.sleep(self.mock_delay / 1000.0)

        output = f"Mock response based on: {(user_prompt or '')[:300]}"
        prompt_tokens = max(1, len(((system_prompt or "") + " " + (user_prompt or "")).split()) * 2)
        completion_tokens = max(1, len(output.split()) * 2)
        total_tokens = prompt_tokens + completion_tokens
        return LLMResponse(
            text=output,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model or os.getenv("OPENAI_MODEL", "mock-llm"),
        )


class OpenAIClient(BaseLLMClient):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required when USE_MOCK_LLM=false")
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is required when USE_MOCK_LLM=false")
        self.client = AsyncOpenAI(api_key=api_key)
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        selected_model = model or self.default_model

        response = await self.client.chat.completions.create(
            model=selected_model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful AI agent."},
                {"role": "user", "content": user_prompt or ""},
            ],
        )

        text = response.choices[0].message.content or ""
        usage = response.usage

        return LLMResponse(
            text=text,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=selected_model,
        )


def get_llm_client() -> BaseLLMClient:
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    if use_mock:
        return MockLLMClient()
    return OpenAIClient()


class LLMClient(BaseLLMClient):
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> LLMResponse:
        return await get_llm_client().generate(system_prompt, user_prompt, model, temperature)
