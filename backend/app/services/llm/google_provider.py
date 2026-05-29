import os
import json
from typing import Any, Dict, List, Optional
from app.services.llm.base import LLMProvider, LLMResponse, LLMToolCall

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class GoogleProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for GoogleProvider")
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is required for GoogleProvider")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.default_model = os.getenv("GOOGLE_MODEL", "gemini-1.5-pro")

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
        selected_model = model or self.default_model
        request_messages = messages or [
            {"role": "system", "content": system_prompt or "You are a helpful AI agent."},
            {"role": "user", "content": user_prompt or ""},
        ]

        request_kwargs = {
            "model": selected_model,
            "temperature": temperature,
            "messages": request_messages,
        }
        if tools:
            request_kwargs["tools"] = tools
            request_kwargs["tool_choice"] = tool_choice or "auto"

        response = await self.client.chat.completions.create(**request_kwargs)
        message = response.choices[0].message
        text = message.content or None
        tool_calls = []
        for raw_tool_call in getattr(message, "tool_calls", None) or []:
            raw_arguments = getattr(raw_tool_call.function, "arguments", "") or "{}"
            try:
                arguments = json.loads(raw_arguments)
            except Exception:
                arguments = {}
            tool_calls.append(
                LLMToolCall(
                    id=getattr(raw_tool_call, "id", "") or f"tool-call-{len(tool_calls) + 1}",
                    name=raw_tool_call.function.name,
                    arguments=arguments,
                )
            )
        usage = response.usage

        return LLMResponse(
            text=text,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=selected_model,
            tool_calls=tool_calls,
        )

    async def close(self):
        if hasattr(self, "client") and self.client:
            await self.client.close()
