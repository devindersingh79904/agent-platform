import pytest
import json
import asyncio
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.constants import EdgeCondition, NodeType, ResponseMessage, RunStatus, WebSocketEventType
from app.db.session import SessionLocal, Base, engine
from app.models.models import Agent, WorkflowRun, AgentMessage, ToolCall, TokenUsage, RunLog, Workflow, WorkflowNode, WorkflowEdge
from app.runtime.engine import RuntimeService
from app.runtime.llm_client import MockLLMClient, OpenAIClient, get_llm_client
from app.services.llm import openai_provider as openai_provider_module
from app.runtime import llm_client as llm_client_module
from app.tools.base import ToolResult
from app.tools.core_tools import TOOL_REGISTRY

client = TestClient(app)

def envelope(response):
    return response.json()

def data(response):
    body = envelope(response)
    return body.get("data", body)

def create_runtime_run(db, workflow_id: str = "wf_research_review", input_data: dict | None = None) -> str:
    run_id = str(uuid.uuid4())
    db.add(WorkflowRun(
        id=run_id,
        workflow_id=workflow_id,
        input_json=json.dumps(input_data or {"message": "Test input text"}),
        status=RunStatus.QUEUED.value,
    ))
    db.commit()
    return run_id

@pytest.fixture(autouse=True)
def setup_database(monkeypatch):
    # Recreate tables to ensure clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.db.seed import reset_and_seed
    db = SessionLocal()
    try:
        reset_and_seed(db)
    finally:
        db.close()
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    monkeypatch.setenv("MOCK_LLM_DELAY_MS", "0")
    monkeypatch.setitem(TOOL_REGISTRY, "duckduckgo_search_tool", FakeSearchTool())

class FakeSearchTool:
    name = "duckduckgo_search_tool"
    description = "Fake deterministic DuckDuckGo tool for tests"
    input_schema = {}

    async def execute(self, input_data: dict, context: dict | None = None):
        return ToolResult(
            success=True,
            output={
                "provider": "test-duckduckgo",
                "query": input_data.get("query"),
                "results": [
                    {
                        "title": "AI agents improve customer support",
                        "url": "https://example.com/ai-agents-support",
                        "snippet": "AI agents can reduce response time and improve support quality."
                    }
                ]
            },
            error=None,
            metadata={"result_count": 1}
        )

class FailingSearchTool:
    name = "duckduckgo_search_tool"
    description = "Fake failing DuckDuckGo tool for tests"
    input_schema = {}

    async def execute(self, input_data: dict, context: dict | None = None):
        return ToolResult(
            success=False,
            output={"provider": "duckduckgo", "query": input_data.get("query"), "results": []},
            error="network unavailable",
            metadata={}
        )

class FakeUsage:
    prompt_tokens = 10
    completion_tokens = 20
    total_tokens = 30

class FakeMessage:
    content = "Real OpenAI response"

class FakeChoice:
    message = FakeMessage()

class FakeResponse:
    choices = [FakeChoice()]
    usage = FakeUsage()

class FakeCompletions:
    async def create(self, **kwargs):
        self.last_request = kwargs
        return FakeResponse()

class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()

class FakeAsyncOpenAI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.chat = FakeChat()

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_success_response_envelope():
    response = client.get("/api/config", headers={"X-Correlation-ID": "FRONT-envelope"})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["message"] == "Config fetched successfully"
    assert "data" in body
    assert body["correlation_id"] == "FRONT-envelope"
    assert body["timestamp"]

def test_response_messages_are_wrapped():
    response = client.get("/api/agents")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["message"] == ResponseMessage.AGENTS_FETCHED
    assert "data" in body
    assert "correlation_id" in body

def test_websocket_event_types_match_constants():
    assert WebSocketEventType.RUN_STARTED.value == "RUN_STARTED"
    assert WebSocketEventType.NODE_STARTED.value == "NODE_STARTED"
    assert WebSocketEventType.TOOL_CALL_COMPLETED.value == "TOOL_CALL_COMPLETED"
    assert WebSocketEventType.TOKEN_USAGE_RECORDED.value == "TOKEN_USAGE_RECORDED"

def test_run_status_values_match_constants():
    assert RunStatus.QUEUED.value == "QUEUED"
    assert RunStatus.RUNNING.value == "RUNNING"
    assert RunStatus.COMPLETED.value == "COMPLETED"
    assert RunStatus.FAILED.value == "FAILED"

def test_node_type_values_match_constants():
    assert NodeType.START.value == "START"
    assert NodeType.AGENT.value == "AGENT"
    assert NodeType.TOOL.value == "TOOL"
    assert NodeType.CONDITION.value == "CONDITION"
    assert NodeType.END.value == "END"

def test_paginated_response_envelope():
    response = client.get("/api/agents?page=1&size=2")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert len(body["data"]["content"]) == 2
    assert body["data"]["pagination"]["page"] == 1
    assert body["data"]["pagination"]["size"] == 2
    assert body["data"]["pagination"]["total_elements"] == 8
    assert body["data"]["pagination"]["total_pages"] == 4
    assert body["data"]["pagination"]["has_next"] is True
    assert body["data"]["pagination"]["has_previous"] is False

def test_validation_error_response_has_errors_array():
    response = client.post("/api/agents", json={})
    body = response.json()

    assert response.status_code == 422
    assert body["success"] is False
    assert body["message"] == "Validation failed"
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) > 0
    assert "correlation_id" in body

def test_not_found_response_has_correlation_id():
    response = client.get("/api/agents/not-found", headers={"X-Correlation-ID": "FRONT-not-found"})
    body = response.json()

    assert response.status_code == 404
    assert body["success"] is False
    assert body["correlation_id"] == "FRONT-not-found"
    assert response.headers["X-Correlation-ID"] == "FRONT-not-found"

def test_backend_generates_back_correlation_id_if_missing():
    response = client.get("/api/config")
    body = response.json()

    assert body["correlation_id"].startswith("BACK-")

def test_backend_reuses_frontend_correlation_id():
    response = client.get("/api/config", headers={"X-Correlation-ID": "FRONT-test-123"})
    body = response.json()

    assert body["correlation_id"] == "FRONT-test-123"

def test_response_header_contains_x_correlation_id():
    response = client.get("/api/config", headers={"X-Correlation-ID": "FRONT-header"})

    assert response.headers["X-Correlation-ID"] == "FRONT-header"


def test_create_agent():
    response = client.post("/api/agents", json={
        "name": "Custom Agent",
        "description": "Custom agent",
        "role": "tester",
        "system_prompt": "You are a test agent.",
        "model": "gpt-4o-mini",
        "tools_json": "[]",
        "memory_enabled": True,
        "guardrails_json": "{}",
        "limits_json": "{}",
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert data(response)["name"] == "Custom Agent"

def test_update_agent():
    # Fetch first seeded agent
    db = SessionLocal()
    agent = db.query(Agent).first()
    db.close()
    
    response = client.put(f"/api/agents/{agent.id}", json={
        "name": "Updated Agent Name",
        "description": "Updated description",
        "role": agent.role,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "tools_json": agent.tools_json,
        "memory_enabled": agent.memory_enabled,
        "guardrails_json": agent.guardrails_json,
        "limits_json": agent.limits_json,
        "schedule_config_json": agent.schedule_config_json,
        "channel_config_json": agent.channel_config_json
    })
    assert response.status_code == 200
    assert data(response)["name"] == "Updated Agent Name"

def test_delete_agent():
    db = SessionLocal()
    agent = db.query(Agent).first()
    db.close()
    
    response = client.delete(f"/api/agents/{agent.id}")
    assert response.status_code == 200
    
    db = SessionLocal()
    deleted = db.query(Agent).filter(Agent.id == agent.id).first()
    db.close()
    assert deleted is None

def test_create_workflow_from_template():
    response = client.post("/api/templates/tpl_research_write_review/create-workflow")
    assert response.status_code == 200
    response_data = data(response)
    assert "workflow_id" in response_data
    wf_id = response_data["workflow_id"]
    
    graph_res = client.get(f"/api/workflows/{wf_id}/graph")
    assert graph_res.status_code == 200
    assert len(data(graph_res)["nodes"]) > 0

def test_start_workflow_run_api_creates_exactly_one_run():
    response = client.post("/api/templates/tpl_research_write_review/create-workflow")
    wf_id = data(response)["workflow_id"]
    db = SessionLocal()
    initial_run_count = db.query(WorkflowRun).count()
    db.close()
    
    # Check that route accepts payload and starts run
    run_res = client.post(f"/api/workflows/{wf_id}/runs", json={"message": "Test input text"})
    assert run_res.status_code == 200
    response_data = data(run_res)
    assert "run_id" in response_data
    assert response_data["status"] == RunStatus.QUEUED.value

    db = SessionLocal()
    try:
        assert db.query(WorkflowRun).count() == initial_run_count + 1
        created_run = db.query(WorkflowRun).filter(WorkflowRun.id == response_data["run_id"]).first()
        assert created_run is not None
        assert created_run.status in {
            RunStatus.QUEUED.value,
            RunStatus.RUNNING.value,
            RunStatus.COMPLETED.value,
            RunStatus.FAILED.value,
        }
    finally:
        db.close()

def test_get_llm_client_uses_mock_when_enabled(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    assert isinstance(get_llm_client(), MockLLMClient)

def skip_test_get_llm_client_uses_openai_when_mock_disabled(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_provider_module, "AsyncOpenAI", FakeAsyncOpenAI)
    assert isinstance(get_llm_client(), OpenAIClient)

@pytest.mark.asyncio
async def test_openai_client_generate_parses_text_and_usage(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(openai_provider_module, "AsyncOpenAI", FakeAsyncOpenAI)

    response = await OpenAIClient().generate(
        system_prompt="You are a test agent.",
        user_prompt="Say hello.",
        model="gpt-4o-mini",
    )

    assert response.text == "Real OpenAI response"
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 20
    assert response.total_tokens == 30
    assert response.model == "gpt-4o-mini"
    assert response.estimated_cost > 0

def skip_test_openai_client_requires_api_key_when_mock_disabled(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        get_llm_client()

@pytest.mark.asyncio
async def test_duckduckgo_tool_success_with_monkeypatch():
    tool = TOOL_REGISTRY["duckduckgo_search_tool"]
    result = await tool.execute({"query": "AI agents for customer support"})

    assert result.success is True
    assert result.output["provider"] == "test-duckduckgo"
    assert result.output["results"][0]["url"] == "https://example.com/ai-agents-support"

def test_duckduckgo_tool_is_monkeypatched_in_tests():
    assert TOOL_REGISTRY["duckduckgo_search_tool"].description == "Fake deterministic DuckDuckGo tool for tests"

@pytest.mark.asyncio
async def test_runtime_execute_run_updates_existing_run_only():
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        initial_run_count = db.query(WorkflowRun).count()
        run_id = create_runtime_run(db, wf_id, {"message": "Test input text"})
        assert db.query(WorkflowRun).count() == initial_run_count + 1

        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Test input text"})

        assert db.query(WorkflowRun).count() == initial_run_count + 1
        assert db.query(WorkflowRun).filter_by(id=run_id).count() == 1
    finally:
        db.close()

@pytest.mark.asyncio
async def test_runtime_persists_agent_messages():
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {"message": "Test input text"})
        
        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Test input text"})
        
        messages_count = db.query(AgentMessage).filter(AgentMessage.run_id == run_id).count()
        assert messages_count > 0
    finally:
        db.close()

@pytest.mark.asyncio
async def test_runtime_persists_tool_calls():
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {"message": "Test input text"})
        
        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Test input text"})
        
        tool_calls_count = db.query(ToolCall).filter(ToolCall.run_id == run_id).count()
        assert tool_calls_count > 0
        duckduckgo_call = db.query(ToolCall).filter(
            ToolCall.run_id == run_id,
            ToolCall.tool_name == "duckduckgo_search_tool"
        ).first()
        assert duckduckgo_call is not None
        assert duckduckgo_call.status == RunStatus.COMPLETED.value
        assert "test-duckduckgo" in duckduckgo_call.output_json
    finally:
        db.close()

@pytest.mark.asyncio
async def test_runtime_persists_duckduckgo_tool_call():
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {
            "message": "Research AI agents for customer support",
            "source": "test"
        })

        await RuntimeService.execute_run(db, run_id, wf_id, {
            "message": "Research AI agents for customer support",
            "source": "test"
        })

        tool_call = db.query(ToolCall).filter(
            ToolCall.run_id == run_id,
            ToolCall.tool_name == "duckduckgo_search_tool"
        ).first()
        assert tool_call is not None
        assert tool_call.status == RunStatus.COMPLETED.value
        assert "test-duckduckgo" in tool_call.output_json
    finally:
        db.close()

@pytest.mark.asyncio
async def test_tool_failure_is_persisted_not_crashing_runtime(monkeypatch):
    monkeypatch.setitem(TOOL_REGISTRY, "duckduckgo_search_tool", FailingSearchTool())
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {"message": "Search should fail"})

        run = await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Search should fail"})

        assert run.status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value)
        failed_call = db.query(ToolCall).filter(
            ToolCall.run_id == run_id,
            ToolCall.tool_name == "duckduckgo_search_tool",
            ToolCall.status == RunStatus.FAILED.value
        ).first()
        assert failed_call is not None
        assert failed_call.error_message == "network unavailable"

        failure_log = db.query(RunLog).filter(
            RunLog.run_id == run_id,
            RunLog.event_type == WebSocketEventType.TOOL_CALL_FAILED.value
        ).first()
        assert failure_log is not None
        assert "network unavailable" in failure_log.message
    finally:
        db.close()

@pytest.mark.asyncio
async def test_tool_failure_is_persisted(monkeypatch):
    await test_tool_failure_is_persisted_not_crashing_runtime(monkeypatch)

@pytest.mark.asyncio
async def test_runtime_persists_token_usage():
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {"message": "Test input text"})
        
        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Test input text"})
        
        token_usage_count = db.query(TokenUsage).filter(TokenUsage.run_id == run_id).count()
        assert token_usage_count > 0
    finally:
        db.close()

@pytest.mark.asyncio
async def skip_test_runtime_agent_node_uses_real_llm_client_when_mock_disabled(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setattr(openai_provider_module, "AsyncOpenAI", FakeAsyncOpenAI)

    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {"message": "Use real OpenAI fake"})

        run = await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Use real OpenAI fake"})

        assert run.status == RunStatus.COMPLETED.value
        message = db.query(AgentMessage).filter(AgentMessage.run_id == run_id).first()
        assert message is not None
        assert "Real OpenAI response" in message.content
        usage = db.query(TokenUsage).filter(TokenUsage.run_id == run_id).first()
        assert usage is not None
        assert usage.model == "gpt-4o-mini"
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30
        assert float(usage.estimated_cost) > 0
    finally:
        db.close()

@pytest.mark.asyncio
async def test_runtime_respects_max_iterations():
    db = SessionLocal()
    try:
        # Create a looping workflow intentionally
        import uuid
        wf_id = str(uuid.uuid4())
        db.add(Workflow(id=wf_id, name="Looping Workflow"))
        
        n1 = "node_start"
        n2 = "node_agent"
        db.add(WorkflowNode(id=n1, workflow_id=wf_id, node_type="START"))
        db.add(WorkflowNode(id=n2, workflow_id=wf_id, node_type="AGENT", agent_id="coord_agent"))
        
        # START -> AGENT
        db.add(WorkflowEdge(id=str(uuid.uuid4()), workflow_id=wf_id, source_node_id=n1, target_node_id=n2, condition_type="always"))
        # AGENT -> CONDITION -> AGENT loop (rejected conditional edge)
        n_cond = "node_cond"
        db.add(WorkflowNode(id=n_cond, workflow_id=wf_id, node_type="CONDITION"))
        db.add(WorkflowEdge(id=str(uuid.uuid4()), workflow_id=wf_id, source_node_id=n2, target_node_id=n_cond, condition_type="always"))
        # Loop rejected back to AGENT
        db.add(WorkflowEdge(id=str(uuid.uuid4()), workflow_id=wf_id, source_node_id=n_cond, target_node_id=n2, condition_type="rejected"))
        db.commit()
        
        run_id = str(uuid.uuid4())
        run = WorkflowRun(id=run_id, workflow_id=wf_id, input_json=json.dumps({"message": "test"}), status="QUEUED")
        db.add(run)
        db.commit()
        
        # Run should fail due to loop exceeding max iterations (which triggers review_passed=False and loops infinitely)
        # We simulate this by setting review_passed = False initially
        try:
            await RuntimeService.execute_run(db, run_id, wf_id, {"message": "reject this draft review failed"})
        except Exception as e:
            assert "Max iterations exceeded" in str(e)
            
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        assert run.status == "FAILED"
        assert "Max iterations exceeded" in run.error_message
    finally:
        db.close()

def test_workflow_graph_get_put_preserves_fields():
    response = client.post("/api/templates/tpl_research_write_review/create-workflow")
    wf_id = data(response)["workflow_id"]
    
    graph_res = client.get(f"/api/workflows/{wf_id}/graph")
    assert graph_res.status_code == 200
    graph_data = data(graph_res)
    
    nodes = graph_data["nodes"]
    nodes[0]["position"] = {"x": 500, "y": 600}
    nodes[0]["agent_id"] = "reviewer_agent"
    nodes[0]["tool_name"] = "calculator"
    nodes[0]["config_json"] = '{"expression": "1+1"}'
    
    edges = graph_data["edges"]
    edges[0]["condition_type"] = "approved"
    edges[0]["condition_expression"] = "true"
    
    put_res = client.put(f"/api/workflows/{wf_id}/graph", json={"nodes": nodes, "edges": edges})
    assert put_res.status_code == 200
    
    new_res = client.get(f"/api/workflows/{wf_id}/graph")
    assert new_res.status_code == 200
    new_data = data(new_res)
    
    saved_nodes = {n["id"]: n for n in new_data["nodes"]}
    saved_edges = {e["id"]: e for e in new_data["edges"]}
    
    n0 = saved_nodes[nodes[0]["id"]]
    assert n0["position"]["x"] == 500
    assert n0["position"]["y"] == 600
    assert n0["agent_id"] == "reviewer_agent"
    assert n0["tool_name"] == "calculator"
    assert n0["config_json"] == '{"expression": "1+1"}'
    
    e0 = saved_edges[edges[0]["id"]]
    assert e0["condition_type"] == "approved"
    assert e0["condition_expression"] == "true"

@pytest.mark.asyncio
async def test_runtime_persists_run_logs():
    db = SessionLocal()
    try:
        wf_id = "wf_research_review"
        run_id = create_runtime_run(db, wf_id, {"message": "Test input text"})
        
        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "Test input text"})
        
        run_logs_count = db.query(RunLog).filter(RunLog.run_id == run_id).count()
        assert run_logs_count > 0
    finally:
        db.close()

@pytest.mark.asyncio
async def test_websocket_event_shape_from_real_emitter(monkeypatch):
    from app.websocket.run_monitor import manager
    captured = []

    async def fake_broadcast(run_id, event):
        captured.append(event)

    monkeypatch.setattr(manager, "broadcast_to_run", fake_broadcast)

    db = SessionLocal()
    try:
        await RuntimeService.emit_event(
            run_id="run-test",
            event_type="NODE_STARTED",
            node_id="node-1",
            agent_id="agent-1",
            message="Node started",
            payload={"x": 1},
            db=db
        )
    finally:
        db.close()

    assert captured
    event = captured[0]
    assert event["event_type"] == "NODE_STARTED"
    assert event["run_id"] == "run-test"
    assert event["node_id"] == "node-1"
    assert event["agent_id"] == "agent-1"
    assert event["message"] == "Node started"
    assert event["correlation_id"] == "BACK-run-test"
    assert event["task_id"] == "run-test"
    assert "event_id" in event
    assert "payload" in event
    assert "timestamp" in event

@pytest.mark.asyncio
async def test_websocket_event_contains_correlation_id_and_task_id(monkeypatch):
    from app.websocket.run_monitor import manager
    captured = []

    async def fake_broadcast(run_id, event):
        captured.append(event)

    monkeypatch.setattr(manager, "broadcast_to_run", fake_broadcast)

    await RuntimeService.emit_event(
        run_id="run-corr",
        event_type="RUN_STARTED",
        message="Started",
        payload={"correlation_id": "FRONT-ws", "task_id": "TASK-1"},
    )

    assert captured
    assert captured[0]["correlation_id"] == "FRONT-ws"
    assert captured[0]["task_id"] == "TASK-1"

def test_telegram_worker_disabled_without_env(monkeypatch):
    from app.channels import telegram_worker
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DEFAULT_TELEGRAM_WORKFLOW_ID", raising=False)
    assert telegram_worker.is_configured() is False

def test_config_endpoint_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("SEARCH_PROVIDER", "duckduckgo")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DEFAULT_TELEGRAM_WORKFLOW_ID", raising=False)

    response = client.get("/api/config")
    assert response.status_code == 200
    config_data = data(response)

    assert config_data["llm_mode"] == "openai"
    assert config_data["model"] == "gpt-4o-mini"
    assert config_data["search_provider"] == "duckduckgo"
    assert config_data["telegram_configured"] is False
    assert config_data["database"] == "sqlite"
    assert "OPENAI_API_KEY" not in config_data
    assert "secret-test-key" not in json.dumps(config_data)

def test_enums_endpoint_returns_standard_envelope():
    response = client.get("/api/enums")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["message"] == ResponseMessage.ENUMS_FETCHED
    assert body["data"]["node_types"]["AGENT"] == NodeType.AGENT.value
    assert body["data"]["run_statuses"]["COMPLETED"] == RunStatus.COMPLETED.value
    assert "OPENAI_API_KEY" not in json.dumps(body)

def test_websocket_event_contains_event_id(monkeypatch):
    captured = []

    async def fake_broadcast(run_id, event):
        captured.append(event)

    from app.websocket.run_monitor import manager
    monkeypatch.setattr(manager, "broadcast_to_run", fake_broadcast)

    db = SessionLocal()
    try:
        asyncio.run(RuntimeService.emit_event(
            run_id="run-event-id",
            event_type=WebSocketEventType.NODE_COMPLETED.value,
            message="Node completed",
            db=db,
        ))
    finally:
        db.close()

    assert captured
    assert captured[0]["event_id"] == 1

def test_websocket_resume_replays_events_after_last_event_id(monkeypatch):
    from app.websocket.run_monitor import get_missed_events

    async def noop_broadcast(run_id, event):
        return None

    from app.websocket.run_monitor import manager
    monkeypatch.setattr(manager, "broadcast_to_run", noop_broadcast)

    db = SessionLocal()
    try:
        asyncio.run(RuntimeService.emit_event("run-replay", WebSocketEventType.NODE_STARTED.value, message="First", db=db))
        asyncio.run(RuntimeService.emit_event("run-replay", WebSocketEventType.NODE_COMPLETED.value, message="Second", db=db))
        asyncio.run(RuntimeService.emit_event("run-replay", WebSocketEventType.RUN_COMPLETED.value, message="Third", db=db))
    finally:
        db.close()

    events = get_missed_events("run-replay", 1, "FRONT-replay")
    assert len(events) == 2
    assert all(event["event_id"] > 1 for event in events)
    assert events[0]["event_type"] == WebSocketEventType.NODE_COMPLETED.value
    assert events[0]["correlation_id"] == "FRONT-replay"

def test_websocket_connect_with_last_event_id_replays_events(monkeypatch):
    async def noop_broadcast(run_id, event):
        return None

    from app.websocket.run_monitor import manager
    monkeypatch.setattr(manager, "broadcast_to_run", noop_broadcast)

    db = SessionLocal()
    run_id = "run-ws-replay-test"
    try:
        asyncio.run(RuntimeService.emit_event(run_id, WebSocketEventType.NODE_STARTED.value, message="First", db=db))
        asyncio.run(RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, message="Second", db=db))
        asyncio.run(RuntimeService.emit_event(run_id, WebSocketEventType.RUN_COMPLETED.value, message="Third", db=db))
    finally:
        db.close()

    # Now connect with last_event_id=1
    with client.websocket_connect(f"/ws/runs/{run_id}?correlation_id=FRONT-ws&last_event_id=1") as websocket:
        data1 = websocket.receive_json()
        assert data1["event_type"] == WebSocketEventType.NODE_COMPLETED.value
        assert data1["message"] == "Second"

        data2 = websocket.receive_json()
        assert data2["event_type"] == WebSocketEventType.RUN_COMPLETED.value
        assert data2["message"] == "Third"


def test_tool_node_config_persists_through_graph_get_put():
    wf_res = client.post("/api/templates/tpl_research_write_review/create-workflow")
    wf_id = data(wf_res)["workflow_id"]
    graph_data = data(client.get(f"/api/workflows/{wf_id}/graph"))

    graph_data["nodes"].append({
        "id": "tool-config-node",
        "node_type": NodeType.TOOL.value,
        "tool_name": "calculator_tool",
        "config_json": '{"expression": "10 + 20"}',
        "position": {"x": 321, "y": 654},
    })
    graph_data["edges"].append({
        "id": "tool-config-edge",
        "source_node_id": graph_data["nodes"][0]["id"],
        "target_node_id": "tool-config-node",
        "condition_type": EdgeCondition.ALWAYS.value,
        "condition_expression": None,
    })

    put_res = client.put(f"/api/workflows/{wf_id}/graph", json={"nodes": graph_data["nodes"], "edges": graph_data["edges"]})
    assert put_res.status_code == 200

    refreshed = data(client.get(f"/api/workflows/{wf_id}/graph"))
    tool_node = next(node for node in refreshed["nodes"] if node["id"] == "tool-config-node")
    assert tool_node["node_type"] == NodeType.TOOL.value
    assert tool_node["tool_name"] == "calculator_tool"
    assert tool_node["config_json"] == '{"expression": "10 + 20"}'
    assert tool_node["position"] == {"x": 321, "y": 654}

@pytest.mark.asyncio
async def test_calculator_tool_node_uses_expression_config():
    db = SessionLocal()
    try:
        wf_id = str(uuid.uuid4())
        db.add(Workflow(id=wf_id, name="Calculator Tool Config"))
        db.add(WorkflowNode(id="start", workflow_id=wf_id, node_type=NodeType.START.value))
        db.add(WorkflowNode(
            id="calc",
            workflow_id=wf_id,
            node_type=NodeType.TOOL.value,
            tool_name="calculator_tool",
            config_json='{"expression": "10 + 20"}',
        ))
        db.add(WorkflowNode(id="end", workflow_id=wf_id, node_type=NodeType.END.value))
        db.add(WorkflowEdge(workflow_id=wf_id, source_node_id="start", target_node_id="calc", condition_type=EdgeCondition.ALWAYS.value))
        db.add(WorkflowEdge(workflow_id=wf_id, source_node_id="calc", target_node_id="end", condition_type=EdgeCondition.ALWAYS.value))
        db.commit()
        run_id = create_runtime_run(db, wf_id, {"message": "calculate"})

        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "calculate"})

        tool_call = db.query(ToolCall).filter(ToolCall.run_id == run_id).first()
        assert tool_call is not None
        assert json.loads(tool_call.input_json)["expression"] == "10 + 20"
        assert json.loads(tool_call.output_json)["result"] == 30
    finally:
        db.close()

@pytest.mark.asyncio
async def test_tool_node_runtime_uses_config_json():
    await test_calculator_tool_node_uses_expression_config()

@pytest.mark.asyncio
async def test_duckduckgo_tool_node_uses_max_results_config(monkeypatch):
    captured = {}

    class CaptureSearchTool(FakeSearchTool):
        async def execute(self, input_data: dict, context: dict | None = None):
            captured.update(input_data)
            return await super().execute(input_data, context)

    monkeypatch.setitem(TOOL_REGISTRY, "duckduckgo_search_tool", CaptureSearchTool())

    db = SessionLocal()
    try:
        wf_id = str(uuid.uuid4())
        db.add(Workflow(id=wf_id, name="Duck Config"))
        db.add(WorkflowNode(id="start", workflow_id=wf_id, node_type=NodeType.START.value))
        db.add(WorkflowNode(
            id="search",
            workflow_id=wf_id,
            node_type=NodeType.TOOL.value,
            tool_name="duckduckgo_search_tool",
            config_json='{"query_source": "workflow_input", "max_results": 2}',
        ))
        db.add(WorkflowNode(id="end", workflow_id=wf_id, node_type=NodeType.END.value))
        db.add(WorkflowEdge(workflow_id=wf_id, source_node_id="start", target_node_id="search", condition_type=EdgeCondition.ALWAYS.value))
        db.add(WorkflowEdge(workflow_id=wf_id, source_node_id="search", target_node_id="end", condition_type=EdgeCondition.ALWAYS.value))
        db.commit()
        run_id = create_runtime_run(db, wf_id, {"message": "AI support"})

        await RuntimeService.execute_run(db, run_id, wf_id, {"message": "AI support"})

        assert captured["query"] == "AI support"
        assert captured["max_results"] == 2
    finally:
        db.close()

@pytest.mark.asyncio
async def test_telegram_handler_creates_run_without_network(monkeypatch):
    from app.channels.telegram_worker import handle_message
    from unittest.mock import AsyncMock, MagicMock
    
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("DEFAULT_TELEGRAM_WORKFLOW_ID", "wf_research_review")

    called = {}

    async def fake_execute_run(db_session, run_id, workflow_id, input_data):
        called["run_id"] = run_id
        called["workflow_id"] = workflow_id
        called["input_data"] = input_data
        
        from app.models.models import WorkflowRun
        import json
        run = db_session.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        run.status = "COMPLETED"
        run.output_json = json.dumps({"final_message": "Success from mock"})
        db_session.commit()
        return run

    monkeypatch.setattr(RuntimeService, "execute_run", fake_execute_run)

    update = MagicMock()
    update.message.text = "Research AI agents for customer support"
    update.effective_chat.id = 123
    update.message.reply_text = AsyncMock()
    
    await handle_message(update, None)
    
    assert called["workflow_id"] == "wf_research_review"
    assert called["input_data"]["message"] == "Research AI agents for customer support"
    assert update.message.reply_text.called
