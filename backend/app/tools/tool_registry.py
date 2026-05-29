from typing import Iterable

from app.tools.core_tools import ALL_TOOLS, TOOL_REGISTRY

TOOL_ALIASES = {
    "calculator_tool": "calculator",
    "summarizer_tool": "summarizer",
    "knowledge_base_tool": "knowledge_base_lookup",
    "draft_generator": "draft_response_tool",
    "draft_generator_tool": "draft_response_tool",
    "web_search": "duckduckgo_search_tool",
    "search": "duckduckgo_search_tool",
}


def resolve_tool_alias(name: str) -> str:
    return TOOL_ALIASES.get(name, name)


def get_tool_registry():
    return TOOL_REGISTRY


def get_openai_tool_schemas(tool_names: list[str] | None) -> list[dict]:
    schemas = []
    seen: set[str] = set()
    for tool_name in tool_names or []:
        canonical_name = resolve_tool_alias(tool_name)
        if canonical_name in seen:
            continue
        tool = TOOL_REGISTRY.get(canonical_name)
        if not tool:
            continue
        seen.add(canonical_name)
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": canonical_name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
        )
    return schemas


def available_tool_names(tool_names: Iterable[str] | None = None) -> set[str]:
    if tool_names is None:
        return set(TOOL_REGISTRY.keys())
    return {name for name in tool_names if name in TOOL_REGISTRY}
