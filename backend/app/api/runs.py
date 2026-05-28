from fastapi import APIRouter, Depends, BackgroundTasks, Query, Request
from sqlalchemy.orm import Session
from app.core.constants import RunStatus
from app.core.exceptions import NotFoundException
from app.core.logger import get_logger
from app.core.messages import ResponseMessage
from app.db.session import get_db, SessionLocal
from app.schemas.schemas import WorkflowRunCreate
from app.models.models import WorkflowRun, AgentMessage, RunLog, ToolCall, TokenUsage, NodeRun, ChannelMessage
from app.schemas.base_response import ApiResponse
from sqlalchemy import func, case
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

@router.get("/{run_id}/channel-messages")
def get_run_channel_messages(run_id: str, request: Request, db: Session = Depends(get_db)):
    messages = db.query(ChannelMessage).filter(ChannelMessage.run_id == run_id).order_by(ChannelMessage.created_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_CHANNEL_MESSAGES_FETCHED, messages)

@router.get("/{run_id}/tool-calls")
def get_run_tool_calls(run_id: str, request: Request, db: Session = Depends(get_db)):
    tool_calls = db.query(ToolCall).filter(ToolCall.run_id == run_id).order_by(ToolCall.started_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_TOOL_CALLS_FETCHED, tool_calls)

@router.get("/{run_id}/token-usage")
def get_run_token_usage(run_id: str, request: Request, db: Session = Depends(get_db)):
    token_usage = db.query(TokenUsage).filter(TokenUsage.run_id == run_id).order_by(TokenUsage.created_at.asc()).all()
    return success_response(request, ResponseMessage.RUN_TOKEN_USAGE_FETCHED, token_usage)

@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, request: Request, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise NotFoundException("Run not found")
    
    if run.status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value):
        return success_response(request, "Run already in terminal state", run)
        
    run.status = RunStatus.CANCELLED.value
    db.commit()
    db.refresh(run)
    return success_response(request, ResponseMessage.RUN_CANCELLED, run)

@router.post("/{run_id}/resume")
def resume_run(run_id: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise NotFoundException("Run not found")
        
    if run.status != RunStatus.FAILED.value:
        return success_response(request, "Only failed runs can be resumed", run)
        
    import uuid
    import json
    new_run_id = str(uuid.uuid4())
    
    new_run = WorkflowRun(
        id=new_run_id, 
        workflow_id=run.workflow_id, 
        input_json=run.input_json, 
        status=RunStatus.QUEUED.value,
        resumed_from_run_id=run.id,
        source="resume_api"
    )
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    
    background_tasks.add_task(execute_run_task, new_run_id, new_run.workflow_id, json.loads(new_run.input_json))
    
    return success_response(request, ResponseMessage.RUN_RESUMED, {"run_id": new_run_id})

@router.get("/{run_id}/node-runs", response_model=ApiResponse)
def get_run_node_runs(run_id: str, request: Request, db: Session = Depends(get_db)):
    node_runs = db.query(NodeRun).filter(NodeRun.workflow_run_id == run_id).order_by(NodeRun.created_at.asc()).all()
    from app.schemas.schemas import NodeRunRead
    return success_response(request, ResponseMessage.FETCHED_SUCCESS, [NodeRunRead.model_validate(n).model_dump(mode="json") for n in node_runs])

@router.get("/{run_id}/metrics", response_model=ApiResponse)
def get_run_metrics(run_id: str, request: Request, db: Session = Depends(get_db)):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run:
        raise NotFoundException("Run not found")
        
    node_stats = db.query(
        func.count(NodeRun.id).label('total_nodes'),
        func.sum(case((NodeRun.status == 'FAILED', 1), else_=0)).label('failed_nodes')
    ).filter(NodeRun.workflow_run_id == run_id).first()
    
    tool_stats = db.query(
        func.count(ToolCall.id).label('total_tools'),
        func.sum(case((ToolCall.status == 'COMPLETED', 1), else_=0)).label('successful_tools')
    ).filter(ToolCall.run_id == run_id).first()

    tokens = db.query(
        func.sum(TokenUsage.total_tokens).label('total')
    ).filter(TokenUsage.run_id == run_id).first()

    # Summing cost which is a string in the DB requires some manual python work if we don't want to cast
    token_usages = db.query(TokenUsage.estimated_cost).filter(TokenUsage.run_id == run_id).all()
    total_cost = sum(float(tu.estimated_cost or "0.0") for tu in token_usages)
    
    duration_ms = 0
    if run.started_at and run.completed_at:
        duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        
    tool_count = tool_stats.total_tools or 0
    tool_success = tool_stats.successful_tools or 0
    tool_success_rate = (tool_success / tool_count) if tool_count > 0 else 1.0

    return success_response(request, ResponseMessage.METRICS_FETCHED, {
        "run_id": run.id,
        "duration_ms": duration_ms,
        "node_count": node_stats.total_nodes or 0,
        "tool_call_count": tool_count,
        "failed_node_count": node_stats.failed_nodes or 0,
        "total_tokens": tokens.total or 0,
        "estimated_cost": total_cost,
        "tool_success_rate": tool_success_rate
    })
