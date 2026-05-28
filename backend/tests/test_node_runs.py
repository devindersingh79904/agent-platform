import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import WorkflowRun, NodeRun, Agent, WorkflowNode, WorkflowEdge
from app.core.constants import RunStatus, NodeType
from app.runtime.engine import RuntimeService
from app.services.llm.base import LLMResponse

class FakeLLMClient:
    async def generate(self, system_prompt: str, user_prompt: str, model: str = "test", temperature: float = 0.2, max_tokens: int = 1000):
        return LLMResponse(
            text="Mocked output from fake LLM.",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            model=model,
            estimated_cost=0.0001
        )

@pytest.mark.asyncio
async def test_runtime_creates_node_runs_during_execution(db, monkeypatch):
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLMClient())
    
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())

    db.add(Agent(id=agent_id, name="Test Agent", role="test", goal="test"))
    
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.START.value))
    agent_node = WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.AGENT.value, agent_id=agent_id)
    db.add(agent_node)
    end_node = WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.END.value)
    db.add(end_node)
    
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, status=RunStatus.QUEUED.value, input_json='{"message": "hi"}'))
    db.commit()

    # Act
    await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})

    # Assert
    node_runs = db.query(NodeRun).filter(NodeRun.workflow_run_id == run_id).all()
    assert len(node_runs) >= 3 # start, agent, end
    assert any(n.node_type == NodeType.AGENT.value and n.status == RunStatus.COMPLETED.value for n in node_runs)

@pytest.mark.asyncio
async def test_runtime_marks_node_run_failed_on_tool_error(db, monkeypatch):
    class FailingFakeLLMClient:
        async def generate(self, *args, **kwargs):
            raise Exception("Fatal LLM generation error")
            
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FailingFakeLLMClient())
    
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())

    db.add(Agent(id=agent_id, name="Test Agent", role="test", goal="test"))
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.START.value))
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.AGENT.value, agent_id=agent_id))
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, status=RunStatus.QUEUED.value, input_json='{"message": "hi"}'))
    db.commit()

    # Act
    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})

    # Assert
    assert run.status == RunStatus.FAILED.value
    node_runs = db.query(NodeRun).filter(NodeRun.workflow_run_id == run_id).all()
    failed_node = next((n for n in node_runs if n.node_type == NodeType.AGENT.value), None)
    assert failed_node is not None
    assert failed_node.status == RunStatus.FAILED.value
    assert "Fatal LLM generation error" in failed_node.error_message
