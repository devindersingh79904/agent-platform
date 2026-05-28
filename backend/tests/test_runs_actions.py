import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import WorkflowRun, WorkflowNode, WorkflowEdge, NodeRun, RunLog
from app.core.constants import RunStatus, NodeType, WebSocketEventType
from app.runtime.engine import RuntimeService

def test_cancel_run(client: TestClient, db):
    run_id = str(uuid.uuid4())
    wf_run = WorkflowRun(
        id=run_id, 
        workflow_id="wf1", 
        status=RunStatus.RUNNING.value, 
        input_json="{}"
    )
    db.add(wf_run)
    db.commit()

    res = client.post(f"/api/runs/{run_id}/cancel")
    assert res.status_code == 200

    updated = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    assert updated.status == RunStatus.CANCELLED.value

def test_resume_run_creates_new_resumed_run(client: TestClient, db):
    run_id = str(uuid.uuid4())
    wf_run = WorkflowRun(
        id=run_id, 
        workflow_id="wf2", 
        status=RunStatus.FAILED.value, 
        input_json='{"message": "retry me"}'
    )
    db.add(wf_run)
    db.commit()

    res = client.post(f"/api/runs/{run_id}/resume")
    assert res.status_code == 200
    
    new_run_id = res.json()["data"]["run_id"]
    assert new_run_id != run_id

    new_run = db.query(WorkflowRun).filter(WorkflowRun.id == new_run_id).first()
    assert new_run.resumed_from_run_id == run_id
    assert new_run.input_json == '{"message": "retry me"}'

@pytest.mark.asyncio
async def test_runtime_cancelled_run_stops_before_next_node(db, monkeypatch):
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    start_node = WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.START.value)
    end_node = WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.END.value)
    db.add(start_node)
    db.add(end_node)
    
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, status=RunStatus.QUEUED.value, input_json='{"message": "hi"}'))
    db.commit()

    original_is_cancelled = RuntimeService.is_run_cancelled
    call_count = 0
    
    def fake_is_cancelled(db_session, r_id):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            return True
        return False
        
    monkeypatch.setattr(RuntimeService, "is_run_cancelled", fake_is_cancelled)

    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})
    
    assert run.status == RunStatus.CANCELLED.value
    
    node_runs = db.query(NodeRun).filter(NodeRun.workflow_run_id == run_id).all()
    assert len(node_runs) == 1
    assert node_runs[0].node_id == start_node.id
    
    cancel_logs = db.query(RunLog).filter(RunLog.run_id == run_id, RunLog.event_type == WebSocketEventType.RUN_CANCELLED.value).all()
    assert len(cancel_logs) > 0
