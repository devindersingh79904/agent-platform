import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import AgentMemory, Agent, WorkflowNode, WorkflowRun, RunLog
from app.core.constants import RunStatus, NodeType
from app.runtime.engine import RuntimeService
from app.services.llm.base import LLMResponse

def test_memory_crud(client: TestClient):
    # Create agent first
    agent_res = client.post("/api/agents", json={"name": "MemAgent", "role": "r", "system_prompt": "s", "model": "m"})
    assert agent_res.status_code == 200
    agent_id = agent_res.json()["data"]["id"]

    # Create memory
    res = client.post(f"/api/agents/{agent_id}/memories", json={
        "memory_type": "SHORT_TERM",
        "content": "Test content",
        "metadata_json": "{}"
    })
    assert res.status_code == 200
    mem_id = res.json()["data"]["id"]

    # Read memories
    get_res = client.get(f"/api/agents/{agent_id}/memories")
    assert get_res.status_code == 200
    assert len(get_res.json()["data"]) == 1

    # Update memory
    put_res = client.put(f"/api/agents/{agent_id}/memories/{mem_id}", json={
        "memory_type": "LONG_TERM",
        "content": "Updated content"
    })
    assert put_res.status_code == 200

    # Delete memory
    del_res = client.delete(f"/api/agents/{agent_id}/memories/{mem_id}")
    assert del_res.status_code == 200

    # Verify empty
    get_empty = client.get(f"/api/agents/{agent_id}/memories")
    assert len(get_empty.json()["data"]) == 0

@pytest.mark.asyncio
async def test_memory_injected_into_llm_prompt(db, monkeypatch):
    captured_prompts = []

    class FakeLLM:
        async def generate(self, system_prompt, user_prompt, model=None, temperature=0.2):
            captured_prompts.append({
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            })
            return LLMResponse(
                text="memory-aware response",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                model="fake"
            )

    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLM())
    
    agent_id = str(uuid.uuid4())
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    
    db.add(Agent(id=agent_id, name="Test Agent", role="test", goal="test", memory_enabled=True, system_prompt="Base prompt"))
    db.add(AgentMemory(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        memory_type="LONG_TERM",
        content="User prefers concise summaries"
    ))
    
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.START.value))
    db.add(WorkflowNode(id=str(uuid.uuid4()), workflow_id=workflow_id, node_type=NodeType.AGENT.value, agent_id=agent_id))
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, status=RunStatus.QUEUED.value, input_json='{"message": "hi"}'))
    db.commit()

    await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "hi"})
    
    assert len(captured_prompts) > 0
    assert "User prefers concise summaries" in captured_prompts[0]["system_prompt"]
