import json
import uuid

import pytest

from app.core.constants import EdgeCondition, NodeType, RunStatus, WebSocketEventType
from app.models.models import NodeRun, RunLog, Workflow, WorkflowEdge, WorkflowNode, WorkflowRun
from app.runtime.engine import RuntimeService


@pytest.mark.asyncio
async def test_runtime_emits_single_node_started_per_node(db):
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    db.add(Workflow(id=workflow_id, name="Runtime event uniqueness"))
    db.add(WorkflowNode(id="start", workflow_id=workflow_id, node_type=NodeType.START.value))
    db.add(WorkflowNode(id="end", workflow_id=workflow_id, node_type=NodeType.END.value))
    db.add(WorkflowEdge(
        workflow_id=workflow_id,
        source_node_id="start",
        target_node_id="end",
        condition_type=EdgeCondition.ALWAYS.value,
    ))
    db.add(WorkflowRun(
        id=run_id,
        workflow_id=workflow_id,
        status=RunStatus.QUEUED.value,
        input_json=json.dumps({"message": "hello"}),
    ))
    db.commit()

    await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hello"})

    node_runs = db.query(NodeRun).filter(NodeRun.workflow_run_id == run_id).all()
    started_logs = db.query(RunLog).filter(
        RunLog.run_id == run_id,
        RunLog.event_type == WebSocketEventType.NODE_STARTED.value,
    ).all()

    started_node_ids = [
        json.loads(log.metadata_json).get("node_id")
        for log in started_logs
    ]

    assert len(node_runs) == 2
    assert len(started_logs) == len(node_runs)
    assert sorted(started_node_ids) == sorted(node_run.node_id for node_run in node_runs)
    assert len(started_node_ids) == len(set(started_node_ids))
