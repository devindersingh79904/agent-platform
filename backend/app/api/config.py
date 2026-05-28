import os

from fastapi import APIRouter, Request

from app.channels.telegram_worker import is_configured as telegram_is_configured
from app.core.messages import ResponseMessage
from app.utils.response_builder import success_response

router = APIRouter()


@router.get("")
def get_config(request: Request):
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/ai_agent_studio.db")
    return success_response(request, ResponseMessage.CONFIG_FETCHED, {
        "app_name": os.getenv("APP_NAME", "Devinder AI Agent Studio"),
        "llm_mode": "mock" if use_mock else "openai",
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "search_provider": os.getenv("SEARCH_PROVIDER", "duckduckgo"),
        "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "default_telegram_workflow_id_configured": bool(os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")),
        "database": "sqlite" if database_url.startswith("sqlite") else "external",
    })
