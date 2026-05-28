import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


MODEL_PRICING = {
    "gpt-4o-mini": {
        "input_per_1m": 0.15,
        "output_per_1m": 0.60,
    }
}


@dataclass
class LLMToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    estimated_cost: float | None = None
    tool_calls: List[LLMToolCall] = field(default_factory=list)

    def __post_init__(self):
        if self.estimated_cost is None:
            self.estimated_cost = estimate_cost(self.model, self.prompt_tokens, self.completion_tokens)


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4o-mini"])
    input_cost = (prompt_tokens / 1_000_000) * pricing["input_per_1m"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output_per_1m"]
    return input_cost + output_cost


class LLMProvider:
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
            tools=tools,
            messages=messages,
        )
        return {
            "content": response.text or "",
            "tool_calls": [
                {"id": tool_call.id, "name": tool_call.name, "arguments": tool_call.arguments}
                for tool_call in response.tool_calls
            ],
            "usage": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
                "estimated_cost": f"{response.estimated_cost:.8f}",
                "model": response.model,
            },
        }

    async def close(self):
        pass
