from fastapi import APIRouter, Depends, BackgroundTasks, Query, Request
from sqlalchemy.orm import Session
from app.core.constants import EdgeCondition, NodeType, RunStatus
from app.core.exceptions import NotFoundException
from app.core.messages import ResponseMessage
from app.db.session import get_db
from app.schemas.schemas import WorkflowCreate
from app.models.models import Workflow, WorkflowNode, WorkflowEdge
from app.utils.response_builder import paginated_response, success_response

router = APIRouter()

@router.post("")
def create_workflow(workflow: WorkflowCreate, request: Request, db: Session = Depends(get_db)):
    db_workflow = Workflow(**workflow.model_dump())
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return success_response(request, ResponseMessage.WORKFLOW_CREATED, db_workflow)

@router.get("")
def get_workflows(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Workflow)
    total = query.count()
    workflows = query.offset((page - 1) * size).limit(size).all()
    return paginated_response(request, ResponseMessage.WORKFLOWS_FETCHED, workflows, page, size, total)

@router.post("/{workflow_id}/runs")
def create_workflow_run(workflow_id: str, payload: dict, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from app.models.models import WorkflowRun
    import uuid
    import json
    from datetime import datetime
    from app.api.runs import execute_run_task
    from app.runtime.engine import normalize_run_input
    
    normalized = normalize_run_input(payload)
    normalized["correlation_id"] = getattr(request.state, "correlation_id", None)
    run_id = str(uuid.uuid4())
    new_run = WorkflowRun(id=run_id, workflow_id=workflow_id, input_json=json.dumps(normalized), status=RunStatus.QUEUED.value, started_at=datetime.utcnow())
    db.add(new_run)
    db.commit()
    db.refresh(new_run)

    background_tasks.add_task(execute_run_task, run_id, workflow_id, normalized)
    
    return success_response(request, ResponseMessage.RUN_QUEUED, {"run_id": run_id, "workflow_id": workflow_id, "status": RunStatus.QUEUED.value})

@router.get("/{workflow_id}")
def get_workflow(workflow_id: str, request: Request, db: Session = Depends(get_db)):
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise NotFoundException("Workflow not found")
    return success_response(request, ResponseMessage.WORKFLOW_FETCHED, db_workflow)

@router.put("/{workflow_id}")
def update_workflow(workflow_id: str, workflow: WorkflowCreate, request: Request, db: Session = Depends(get_db)):
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise NotFoundException("Workflow not found")
    
    update_data = workflow.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_workflow, key, value)
        
    db.commit()
    db.refresh(db_workflow)
    return success_response(request, ResponseMessage.WORKFLOW_UPDATED, db_workflow)

@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str, request: Request, db: Session = Depends(get_db)):
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if db_workflow:
        db.delete(db_workflow)
        db.commit()
        return success_response(request, ResponseMessage.WORKFLOW_DELETED, {"status": "ok"})
    raise NotFoundException("Workflow not found")

@router.get("/{workflow_id}/graph")
def get_workflow_graph(workflow_id: str, request: Request, db: Session = Depends(get_db)):
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise NotFoundException("Workflow not found")
        
    nodes = db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).all()
    edges = db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow_id).all()
    
    return success_response(request, ResponseMessage.WORKFLOW_GRAPH_FETCHED, {
        "workflow": db_workflow,
        "nodes": [
            {
                "id": n.id, "node_type": n.node_type, "agent_id": n.agent_id, 
                "tool_name": n.tool_name, "config_json": n.config_json, "config": n.config_json,
                "position": {"x": n.position_x, "y": n.position_y}
            } for n in nodes
        ],
        "edges": [
            {
                "id": e.id, "source_node_id": e.source_node_id, "target_node_id": e.target_node_id,
                "condition_type": e.condition_type, "condition_expression": e.condition_expression
            } for e in edges
        ]
    })

@router.put("/{workflow_id}/graph")
def update_workflow_graph(workflow_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    import uuid
    import json
    from app.core.logger import get_logger
    from fastapi import HTTPException
    
    logger = get_logger(__name__)
    
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise NotFoundException("Workflow not found")

    nodes_data = payload.get("nodes", [])
    edges_data = payload.get("edges", [])
    
    logger.info("Updating workflow graph", extra={
        "workflow_id": workflow_id,
        "node_count": len(nodes_data),
        "edge_count": len(edges_data),
    })
    
    # Ensure all nodes have IDs
    for n in nodes_data:
        if not n.get("id"):
            n["id"] = str(uuid.uuid4())

    node_ids = {n.get("id") for n in nodes_data}
    
    if not node_ids:
        raise HTTPException(status_code=400, detail="Workflow graph must contain at least one node")

    missing_refs = []
    for e in edges_data:
        source_id = e.get("source_node_id") or e.get("source")
        target_id = e.get("target_node_id") or e.get("target")
        if source_id not in node_ids:
            missing_refs.append({"edge_id": e.get("id"), "field": "source_node_id", "node_id": source_id})
        if target_id not in node_ids:
            missing_refs.append({"edge_id": e.get("id"), "field": "target_node_id", "node_id": target_id})
            
    if missing_refs:
        logger.warning("Workflow graph validation failed: missing edge node references", extra={
            "workflow_id": workflow_id,
            "missing_refs": missing_refs,
        })
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Workflow graph contains edges referencing missing nodes",
                "missing_refs": missing_refs,
            },
        )

    try:
        # Delete existing edges first to prevent foreign key violations, then nodes
        db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow_id).delete(synchronize_session=False)
        db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).delete(synchronize_session=False)
        
        for n in nodes_data:
            node_type = n.get("node_type") or n.get("type") or n.get("data", {}).get("node_type")
            if node_type == "input":
                node_type = NodeType.START.value
            elif node_type == "output":
                node_type = NodeType.END.value
            elif not node_type:
                node_type = NodeType.AGENT.value
                
            agent_id = n.get("agent_id") or n.get("data", {}).get("agent_id")
            tool_name = n.get("tool_name") or n.get("data", {}).get("tool_name")
            config_json = n.get("config_json") or n.get("config") or n.get("data", {}).get("config_json")
            if isinstance(config_json, dict):
                config_json = json.dumps(config_json)
            elif not config_json:
                config_json = "{}"
                
            position_x = n.get("position", {}).get("x", n.get("position_x", 0))
            position_y = n.get("position", {}).get("y", n.get("position_y", 0))

            db.add(WorkflowNode(
                id=n["id"], 
                workflow_id=workflow_id,
                node_type=node_type, 
                agent_id=agent_id,
                tool_name=tool_name,
                config_json=config_json,
                position_x=int(position_x), 
                position_y=int(position_y)
            ))
            
        db.flush() # flush nodes so edges can reference them safely
        
        for e in edges_data:
            source_node_id = e.get("source_node_id") or e.get("source")
            target_node_id = e.get("target_node_id") or e.get("target")
            condition_type = e.get("condition_type") or e.get("label") or e.get("data", {}).get("condition_type") or EdgeCondition.ALWAYS.value
            condition_expression = e.get("condition_expression") or e.get("data", {}).get("condition_expression")

            db.add(WorkflowEdge(
                id=e.get("id") or str(uuid.uuid4()), 
                workflow_id=workflow_id,
                source_node_id=source_node_id, 
                target_node_id=target_node_id,
                condition_type=condition_type,
                condition_expression=condition_expression
            ))
            
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to update workflow graph", extra={"workflow_id": workflow_id})
        raise HTTPException(status_code=500, detail="Failed to update workflow graph")

    return success_response(request, ResponseMessage.WORKFLOW_GRAPH_UPDATED, {"status": "ok"})
