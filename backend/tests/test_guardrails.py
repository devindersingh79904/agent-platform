import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import Agent, WorkflowNode, WorkflowRun, RunLog, NodeRun
from app.core.constants import RunStatus, NodeType, WebSocketEventType
from app.runtime.engine import RuntimeService
from app.services.llm.base import LLMResponse

class FakeLLMClient:
    def __init__(self, output_text="default response", tokens=10):
        self.output_text = output_text
        self.tokens = tokens
        
    async def generate(self, system_prompt: str, user_prompt: str, model: str = "test", temperature: float = 0.2, max_tokens: int = 1000):
        return LLMResponse(
            text=self.output_text,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=self.tokens,
            model=model,
            estimated_cost=0.0001
        )

async def setup_guardrail_test_run(db, guardrails_json=None, limits_json=None, tools_json='[]', llm_output="response"):
    agent_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    db.add(Agent(
        id=agent_id, name="Test Agent", role="test", goal="test",
        guardrails_json=guardrails_json,
        limits_json=limits_json,
        tools_json=tools_json
    ))
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.START.value))
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.AGENT.value, agent_id=agent_id))
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, status=RunStatus.QUEUED.value, input_json='{"message": "hi secret"}'))
    db.commit()

    return run_id, workflow_id

@pytest.mark.asyncio
async def test_guardrail_blocks_unauthorized_tool_during_runtime(db, monkeypatch):
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLMClient())
    guardrails = json.dumps({"allowed_tools": ["calculator_tool"]})
    tools = json.dumps(["duckduckgo_search_tool"]) # Tool not in allowed_tools
    
    run_id, workflow_id = await setup_guardrail_test_run(db, guardrails_json=guardrails, tools_json=tools)
    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})
    
    assert run.status == RunStatus.FAILED.value
    logs = db.query(RunLog).filter(RunLog.run_id == run_id, RunLog.event_type == WebSocketEventType.GUARDRAIL_VIOLATION.value).all()
    assert len(logs) > 0
    assert "Unauthorized tool requested" in logs[0].message

@pytest.mark.asyncio
async def test_guardrail_blocks_blocked_keyword_during_runtime(db, monkeypatch):
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLMClient())
    guardrails = json.dumps({"blocked_keywords": ["secret"]})
    
    run_id, workflow_id = await setup_guardrail_test_run(db, guardrails_json=guardrails)
    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi secret"})
    
    assert run.status == RunStatus.FAILED.value
    logs = db.query(RunLog).filter(RunLog.run_id == run_id, RunLog.event_type == WebSocketEventType.GUARDRAIL_VIOLATION.value).all()
    assert len(logs) > 0
    assert "blocked keyword" in logs[0].message

@pytest.mark.asyncio
async def test_guardrail_max_tool_calls_during_runtime(db, monkeypatch):
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLMClient())
    limits = json.dumps({"max_tool_calls": 0})
    tools = json.dumps(["calculator_tool"]) # Will try to call it but max is 0
    
    run_id, workflow_id = await setup_guardrail_test_run(db, limits_json=limits, tools_json=tools)
    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})
    
    assert run.status == RunStatus.FAILED.value
    logs = db.query(RunLog).filter(RunLog.run_id == run_id, RunLog.event_type == WebSocketEventType.GUARDRAIL_VIOLATION.value).all()
    assert len(logs) > 0
    assert "Max tool calls exceeded" in logs[0].message

@pytest.mark.asyncio
async def test_guardrail_token_budget_during_runtime(db, monkeypatch):
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLMClient(tokens=5000))
    limits = json.dumps({"max_tokens": 100})
    
    run_id, workflow_id = await setup_guardrail_test_run(db, limits_json=limits)
    # The first LLM response works but then total tokens check will fail on the NEXT iteration
    # Wait, the engine checks token usage at the beginning of the node.
    # To trigger token failure, we execute normally and then if it loops, it'll fail. 
    # Or we can artificially inject token usage prior to running
    from app.models.models import TokenUsage
    db.add(TokenUsage(run_id=run_id, agent_id="agent", total_tokens=200, estimated_cost=0.1))
    db.commit()
    
    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})
    assert run.status == RunStatus.FAILED.value
    logs = db.query(RunLog).filter(RunLog.run_id == run_id, RunLog.event_type == WebSocketEventType.GUARDRAIL_VIOLATION.value).all()
    assert len(logs) > 0
    assert "Max tokens exceeded" in logs[0].message
