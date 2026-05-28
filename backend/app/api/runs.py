from fastapi import APIRouter, Depends, BackgroundTasks, Query, Request
from sqlalchemy.orm import Session
from app.core.constants import RunStatus
from app.core.exceptions import NotFoundException
from app.core.logger import get_logger
from app.core.messages import ResponseMessage
from app.db.session import get_db, SessionLocal
from app.schemas.schemas import WorkflowRunCreate
from app.models.models import WorkflowRun, AgentMessage, RunLog, ToolCall, TokenUsage
from app.runtime.engine import RuntimeService
from app.utils.response_builder import paginated_response, success_response
import asyncio

router = APIRouter()
logger = get_logger(__name__)

def execute_run_task(run_id: str, workflow_id: str, input_json: dict):
    db = SessionLocal()
    try:
        logger.info(
            "Executing run task",
            extra={"correlation_id": input_json.get("correlation_id", "-") if isinstance(input_json, dict) else "-", "run_id": run_id, "task_id": run_id},
        )
        asyncio.run(RuntimeService.execute_run(db, run_id, workflow_id, input_json))
    finally:
        db.close()

@router.post("")
@router.post("/{workflow_id}/runs")
def create_workflow_run(workflow_id: str, run: WorkflowRunCreate, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Immediately trigger run in background
    import json
    from app.runtime.engine import normalize_run_input
    
    raw_input = json.loads(run.input_json) if isinstance(run.input_json, str) else run.input_json
    input_data = normalize_run_input(raw_input)
    
    # We must create the initial DB record so we can return its ID immediately
    from datetime import datetime
    import uuid
    run_id = str(uuid.uuid4())
    new_run = WorkflowRun(id=run_id, workflow_id=workflow_id, input_json=json.dumps(input_data), status=RunStatus.QUEUED.value, started_at=datetime.utcnow())
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    background_tasks.add_task(execute_run_task, run_id, workflow_id, input_data)
    
    return success_response(request, ResponseMessage.RUN_QUEUED, new_run)

@router.get("")
def get_runs(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(WorkflowRun).order_by(WorkflowRun.started_at.desc())
    total = db.query(WorkflowRun).count()
    runs = query.offset((page - 1) * size).limit(size).all()
    return paginated_response(request, ResponseMessage.RUNS_FETCHED, runs, page, size, total)

@router.get("/{run_id}")
def get_run(run_id: str, request: Request, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise NotFoundException("Run not found")
    return success_response(request, ResponseMessage.RUN_FETCHED, run)

@router.get("/{run_id}/messages")
def get_run_messages(run_id: str, request: Request, db: Session = Depends(get_db)):
    messages = db.query(AgentMessage).filter(AgentMessage.run_id == run_id).order_by(AgentMessage.created_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_MESSAGES_FETCHED, messages)

@router.get("/{run_id}/logs")
def get_run_logs(run_id: str, request: Request, db: Session = Depends(get_db)):
    logs = db.query(RunLog).filter(RunLog.run_id == run_id).order_by(RunLog.created_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_LOGS_FETCHED, logs)

@router.get("/{run_id}/tool-calls")
def get_run_tool_calls(run_id: str, request: Request, db: Session = Depends(get_db)):
    tool_calls = db.query(ToolCall).filter(ToolCall.run_id == run_id).order_by(ToolCall.started_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_TOOL_CALLS_FETCHED, tool_calls)

@router.get("/{run_id}/token-usage")
def get_run_token_usage(run_id: str, request: Request, db: Session = Depends(get_db)):
    token_usage = db.query(TokenUsage).filter(TokenUsage.run_id == run_id).order_by(TokenUsage.created_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_TOKEN_USAGE_FETCHED, token_usage)
