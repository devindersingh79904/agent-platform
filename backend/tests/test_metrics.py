import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import WorkflowRun, TokenUsage, ToolCall, NodeRun
from app.core.constants import RunStatus

def test_run_metrics_calculated_from_real_run_data(client: TestClient, db):
    run_id = str(uuid.uuid4())
    wf_run = WorkflowRun(
        id=run_id, 
        workflow_id="wf1", 
        status="COMPLETED", 
        input_json="{}"
    )
    db.add(wf_run)
    
    # 2 TokenUsage rows
    db.add(TokenUsage(run_id=run_id, model="test", prompt_tokens=10, completion_tokens=20, total_tokens=30, estimated_cost="0.001"))
    db.add(TokenUsage(run_id=run_id, model="test", prompt_tokens=5, completion_tokens=5, total_tokens=10, estimated_cost="0.0005"))

    # 3 ToolCalls: 2 completed, 1 failed
    db.add(ToolCall(run_id=run_id, tool_name="tool1", status=RunStatus.COMPLETED.value))
    db.add(ToolCall(run_id=run_id, tool_name="tool2", status=RunStatus.COMPLETED.value))
    db.add(ToolCall(run_id=run_id, tool_name="tool3", status=RunStatus.FAILED.value))

    # 4 NodeRuns: 3 completed, 1 failed
    db.add(NodeRun(workflow_run_id=run_id, workflow_id="wf1", node_id="n1", node_type="AGENT", status=RunStatus.COMPLETED.value))
    db.add(NodeRun(workflow_run_id=run_id, workflow_id="wf1", node_id="n2", node_type="AGENT", status=RunStatus.COMPLETED.value))
    db.add(NodeRun(workflow_run_id=run_id, workflow_id="wf1", node_id="n3", node_type="AGENT", status=RunStatus.COMPLETED.value))
    db.add(NodeRun(workflow_run_id=run_id, workflow_id="wf1", node_id="n4", node_type="AGENT", status=RunStatus.FAILED.value))
    
    db.commit()

    res = client.get(f"/api/runs/{run_id}/metrics")
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert data["node_count"] == 4
    assert data["failed_node_count"] == 1
    assert data["tool_call_count"] == 3
    assert data["tool_success_rate"] == (2/3)
    assert data["total_tokens"] == 40
    assert data["estimated_cost"] == 0.0015
