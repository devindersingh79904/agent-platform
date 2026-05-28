from typing import Iterable

from app.tools.core_tools import ALL_TOOLS, TOOL_REGISTRY


def get_tool_registry():
    return TOOL_REGISTRY


def get_openai_tool_schemas(tool_names: list[str] | None) -> list[dict]:
    schemas = []
    seen: set[str] = set()
    for tool_name in tool_names or []:
        if tool_name in seen:
            continue
        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            continue
        seen.add(tool_name)
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool_name,
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
