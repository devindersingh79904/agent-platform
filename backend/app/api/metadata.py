import os
from fastapi import APIRouter, Request
from app.utils.response_builder import success_response
from app.core.messages import ResponseMessage
from app.tools.tool_registry import TOOL_REGISTRY, TOOL_ALIASES

router = APIRouter()


@router.get("/models")
def get_models_metadata(request: Request):
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    
    models = []
    # Add gpt-4o-mini
    models.append({
        "provider": "openai",
        "model": "gpt-4o-mini",
        "label": "GPT-4o mini",
        "default": (not use_mock) and (openai_model == "gpt-4o-mini")
    })
    
    # Add custom openai model if set
    if openai_model != "gpt-4o-mini":
        models.append({
            "provider": "openai",
            "model": openai_model,
            "label": f"OpenAI {openai_model}",
            "default": not use_mock
        })
        
    # Add mock model
    models.append({
        "provider": "mock",
        "model": "mock-llm",
        "label": "Mock LLM",
        "default": use_mock
    })
    
    return success_response(request, ResponseMessage.FETCHED_SUCCESS, {"models": models})


@router.get("/tools")
def get_tools_metadata(request: Request):
    tools_list = []
    seen = set()
    
    # Filter out known aliases to present only canonical names in metadata
    alias_names = set(TOOL_ALIASES.keys())
    
    for name, tool in TOOL_REGISTRY.items():
        if name in seen or name in alias_names:
            continue
        label = name.replace("_", " ").title()
        tools_list.append({
            "name": name,
            "label": label,
            "description": getattr(tool, "description", ""),
            "input_schema": getattr(tool, "input_schema", {})
        })
        seen.add(name)
        
    return success_response(request, ResponseMessage.FETCHED_SUCCESS, {"tools": tools_list})


@router.get("/channels")
def get_channels_metadata(request: Request):
    telegram_configured = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID"))
    channels = [
        {
            "name": "telegram",
            "label": "Telegram",
            "configured": telegram_configured
        },
        {
            "name": "web",
            "label": "Web UI",
            "configured": True
        }
    ]
    return success_response(request, ResponseMessage.FETCHED_SUCCESS, {"channels": channels})
