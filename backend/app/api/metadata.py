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
    
    # Add Groq models
    groq_models = [
        {"model": "llama-3.1-8b-instant", "label": "Groq: Llama 3.1 8B"},
        {"model": "llama-3.3-70b-versatile", "label": "Groq: Llama 3.3 70B"},
        {"model": "mixtral-8x7b-32768", "label": "Groq: Mixtral 8x7B"}
    ]
    for gm in groq_models:
        models.append({
            "provider": "groq",
            "model": gm["model"],
            "label": gm["label"],
            "default": False
        })
        
    # Add Google Gemini models
    google_models = [
        {"model": "gemini-1.5-pro", "label": "Google: Gemini 1.5 Pro"},
        {"model": "gemini-1.5-flash", "label": "Google: Gemini 1.5 Flash"},
        {"model": "gemini-2.0-flash", "label": "Google: Gemini 2.0 Flash"}
    ]
    for gm in google_models:
        models.append({
            "provider": "google",
            "model": gm["model"],
            "label": gm["label"],
            "default": False
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
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    raw_username = os.getenv("TELEGRAM_BOT_USERNAME")
    
    bot_token_configured = bool(token)
    default_workflow_configured = bool(workflow_id)
    telegram_active = bot_token_configured and default_workflow_configured
    
    bot_username = raw_username.strip().lstrip('@') if raw_username else None
    bot_url = f"https://t.me/{bot_username}" if bot_username else None

    return success_response(request, ResponseMessage.FETCHED_SUCCESS, {
        "telegram": {
            "active": telegram_active,
            "bot_token_configured": bot_token_configured,
            "default_workflow_configured": default_workflow_configured,
            "bot_username": bot_username,
            "bot_url": bot_url,
            "connection_mode": "Polling (Long Poll)"
        },
        "web_ui": {
            "active": True,
            "websocket_endpoint": "/ws"
        }
    })
