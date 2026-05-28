from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.db.session import engine, Base
from app.api import agents, templates, workflows, runs, config, enums, schedules, channel_messages
from app.core.api_paths import API_PREFIX, ApiPath
from enum import Enum

class ExtraApiPath(str, Enum):
    SCHEDULES = "/schedules"
from app.core.correlation import CorrelationIdMiddleware
from app.core.exceptions import AppException
from app.core.logger import RequestLoggingMiddleware, get_logger, setup_logging
from app.core.security import APIAuthMiddleware
from app.schemas.base_response import ErrorDetail
from app.utils.response_builder import error_response, success_response
import os
from app.websocket import run_monitor
from app.core.messages import ErrorMessage, ResponseMessage

setup_logging()
logger = get_logger(__name__)

# Create database tables and seed missing defaults
Base.metadata.create_all(bind=engine)
from app.db.session import SessionLocal
from app.db.seed import seed_missing_defaults
db = SessionLocal()
try:
    seed_missing_defaults(db)
finally:
    db.close()

app = FastAPI(title="Yuno Agent Studio API")

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(APIAuthMiddleware)

cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(agents.router, prefix=f"{API_PREFIX}{ApiPath.AGENTS}", tags=["Agents"])
app.include_router(workflows.router, prefix=f"{API_PREFIX}{ApiPath.WORKFLOWS}", tags=["Workflows"])
app.include_router(templates.router, prefix=f"{API_PREFIX}{ApiPath.TEMPLATES}", tags=["Templates"])
app.include_router(runs.router, prefix=f"{API_PREFIX}{ApiPath.RUNS}", tags=["Runs"])
app.include_router(config.router, prefix=f"{API_PREFIX}{ApiPath.CONFIG}", tags=["Config"])
app.include_router(enums.router, prefix=f"{API_PREFIX}{ApiPath.ENUMS}", tags=["Enums"])
app.include_router(schedules.router, prefix=f"{API_PREFIX}{ExtraApiPath.SCHEDULES.value}", tags=["Schedules"])
app.include_router(channel_messages.router, prefix=f"{API_PREFIX}/channel-messages", tags=["Channel Messages"])
app.include_router(run_monitor.router, tags=["Websocket"])

# Start scheduler is handled by a separate worker process now

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    errors = getattr(exc, "errors", None) or [
        ErrorDetail(field=getattr(exc, "field", None), code=exc.code, message=exc.message)
    ]
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(request, exc.message, errors).model_dump(mode="json"),
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "BACK-UNKNOWN")},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        errors.append(
            ErrorDetail(
                field=field or None,
                code="VALIDATION_ERROR",
                message=err.get("msg", "Invalid value"),
            )
        )

    return JSONResponse(
        status_code=422,
        content=error_response(request, ErrorMessage.VALIDATION_FAILED, errors).model_dump(mode="json"),
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "BACK-UNKNOWN")},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            request,
            str(exc.detail),
            [ErrorDetail(field=None, code=f"HTTP_{exc.status_code}", message=str(exc.detail))],
        ).model_dump(mode="json"),
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "BACK-UNKNOWN")},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception",
        extra={
            "correlation_id": getattr(request.state, "correlation_id", "-"),
            "run_id": "-",
            "task_id": "-",
        },
    )
    return JSONResponse(
        status_code=500,
        content=error_response(
            request,
            ErrorMessage.INTERNAL_SERVER_ERROR,
            [ErrorDetail(field=None, code="INTERNAL_SERVER_ERROR", message=ErrorMessage.UNEXPECTED_ERROR)],
        ).model_dump(mode="json"),
        headers={"X-Correlation-ID": getattr(request.state, "correlation_id", "BACK-UNKNOWN")},
    )


@app.get("/")
def root_check(request: Request):
    return success_response(request, ResponseMessage.HEALTH_CHECK_SUCCESS, {"status": "ok", "app": "Yuno Agent Studio"})

@app.get("/health")
def health_check(request: Request):
    return success_response(request, ResponseMessage.HEALTH_CHECK_SUCCESS, {"status": "ok"})

@app.get("/ready")
def ready_check(request: Request):
    try:
        # Check DB by getting a session and executing a simple query
        from app.db.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "ok"
    except Exception:
        db_status = "error"
        
    use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    return success_response(request, ResponseMessage.READINESS_CHECK_SUCCESS, {
        "status": "ready",
        "database": db_status,
        "llm_provider": "mock" if use_mock else "openai",
        "scheduler": "enabled" if os.getenv("SCHEDULER_ENABLED", "false").lower() == "true" else "disabled"
    })
