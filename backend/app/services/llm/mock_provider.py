import asyncio
import os
import re
from typing import Any, Dict, List, Optional
from app.services.llm.base import LLMProvider, LLMResponse, LLMToolCall


class MockProvider(LLMProvider):
    def __init__(self):
        self.mock_delay = int(os.getenv("MOCK_LLM_DELAY_MS", "800"))

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
        if self.mock_delay > 0:
            await asyncio.sleep(self.mock_delay / 1000.0)

        available_tool_names = {
            tool.get("function", {}).get("name")
            for tool in tools or []
            if tool.get("type") == "function"
        }
        prompt_source = user_prompt or ""
        if messages:
            prompt_source = "\n".join(str(message.get("content") or "") for message in messages)
            tool_messages = [message for message in messages if message.get("role") == "tool"]
            if tool_messages:
                output = f"Mock final response using tool result: {tool_messages[-1].get('content', '')}"
                return self._response(output, system_prompt, prompt_source, model)

        prompt_lower = prompt_source.lower()
        if tools and "search" in prompt_lower and "duckduckgo_search_tool" in available_tool_names:
            return self._tool_response(
                LLMToolCall(
                    id="mock-tool-call-search-1",
                    name="duckduckgo_search_tool",
                    arguments={"query": user_prompt or prompt_source, "max_results": 5},
                ),
                system_prompt,
                prompt_source,
                model,
            )

        if tools and "calculate" in prompt_lower and "calculator_tool" in available_tool_names:
            expression_match = re.search(r"[-+*/().\d\s]{3,}", prompt_source)
            expression = expression_match.group(0).strip() if expression_match else "1 + 1"
            return self._tool_response(
                LLMToolCall(
                    id="mock-tool-call-calc-1",
                    name="calculator_tool",
                    arguments={"expression": expression},
                ),
                system_prompt,
                prompt_source,
                model,
            )

        output = f"Mock response based on: {(user_prompt or '')[:300]}"
        return self._response(output, system_prompt, user_prompt or "", model)

    def _response(self, output: str, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> LLMResponse:
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

    def _tool_response(
        self,
        tool_call: LLMToolCall,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
    ) -> LLMResponse:
        prompt_tokens = max(1, len(((system_prompt or "") + " " + (user_prompt or "")).split()) * 2)
        return LLMResponse(
            text=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=4,
            total_tokens=prompt_tokens + 4,
            model=model or os.getenv("OPENAI_MODEL", "mock-llm"),
            tool_calls=[tool_call],
        )
