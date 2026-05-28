import json
import uuid

import pytest

from app.core.constants import EdgeCondition, NodeType, RunStatus, WebSocketEventType
from app.models.models import Agent, AgentMessage, RunLog, ToolCall, Workflow, WorkflowEdge, WorkflowNode, WorkflowRun
from app.runtime.engine import RuntimeService
from app.services.llm.base import LLMResponse, LLMToolCall
from app.services.llm.mock_provider import MockProvider
from app.services.llm.openai_provider import OpenAIProvider
import app.services.llm.openai_provider as openai_provider_module
from app.tools.tool_registry import get_openai_tool_schemas


def create_agent_workflow(db, tools_json=None, guardrails_json=None):
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    agent_id = str(uuid.uuid4())

    db.add(Workflow(id=workflow_id, name="Tool calling workflow"))
    db.add(
        Agent(
            id=agent_id,
            name="Tool Agent",
            role="assistant",
            system_prompt="Use tools when useful.",
            model="gpt-4o-mini",
            tools_json=json.dumps(tools_json or []),
            guardrails_json=json.dumps(guardrails_json or {}),
        )
    )
    db.add(WorkflowNode(id="start-" + workflow_id, workflow_id=workflow_id, node_type=NodeType.START.value))
    db.add(
        WorkflowNode(
            id="agent-" + workflow_id,
            workflow_id=workflow_id,
            node_type=NodeType.AGENT.value,
            agent_id=agent_id,
        )
    )
    db.add(WorkflowNode(id="end-" + workflow_id, workflow_id=workflow_id, node_type=NodeType.END.value))
    db.add(
        WorkflowEdge(
            workflow_id=workflow_id,
            source_node_id="start-" + workflow_id,
            target_node_id="agent-" + workflow_id,
            condition_type=EdgeCondition.ALWAYS.value,
        )
    )
    db.add(
        WorkflowEdge(
            workflow_id=workflow_id,
            source_node_id="agent-" + workflow_id,
            target_node_id="end-" + workflow_id,
            condition_type=EdgeCondition.ALWAYS.value,
        )
    )
    db.add(
        WorkflowRun(
            id=run_id,
            workflow_id=workflow_id,
            status=RunStatus.QUEUED.value,
            input_json=json.dumps({"message": "calculate 10 + 20"}),
        )
    )
    db.commit()
    return workflow_id, run_id, agent_id


def test_tool_registry_returns_openai_schemas():
    schemas = get_openai_tool_schemas([
        "duckduckgo_search_tool",
        "calculator_tool",
        "knowledge_base_tool",
        "summarizer_tool",
        "draft_response_tool",
    ])

    names = {schema["function"]["name"] for schema in schemas}
    assert "duckduckgo_search_tool" in names
    assert "calculator_tool" in names
    assert all(schema["type"] == "function" for schema in schemas)
    assert all(schema["function"]["parameters"]["type"] == "object" for schema in schemas)


@pytest.mark.asyncio
async def test_openai_provider_parses_tool_calls(monkeypatch):
    class FakeUsage:
        prompt_tokens = 10
        completion_tokens = 20
        total_tokens = 30

    class FakeFunction:
        name = "calculator_tool"
        arguments = '{"expression": "10 + 20"}'

    class FakeToolCall:
        id = "call-1"
        function = FakeFunction()

    class FakeMessage:
        content = None
        tool_calls = [FakeToolCall()]

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]
        usage = FakeUsage()

    class FakeCompletions:
        async def create(self, **kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeAsyncOpenAI:
        def __init__(self, api_key):
            self.chat = FakeChat()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_provider_module, "AsyncOpenAI", FakeAsyncOpenAI)

    response = await OpenAIProvider().generate(
        system_prompt="system",
        user_prompt="calculate",
        tools=get_openai_tool_schemas(["calculator_tool"]),
    )

    assert response.tool_calls[0].name == "calculator_tool"
    assert response.tool_calls[0].arguments == {"expression": "10 + 20"}
    assert response.prompt_tokens == 10


@pytest.mark.asyncio
async def test_mock_provider_returns_tool_call_for_search(monkeypatch):
    monkeypatch.setenv("MOCK_LLM_DELAY_MS", "0")
    response = await MockProvider().generate(
        system_prompt="system",
        user_prompt="please search AI agents",
        tools=get_openai_tool_schemas(["duckduckgo_search_tool"]),
    )
    assert response.tool_calls[0].name == "duckduckgo_search_tool"


@pytest.mark.asyncio
async def test_agent_node_executes_llm_requested_tool(db, monkeypatch):
    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def generate(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return LLMResponse(
                    text=None,
                    tool_calls=[LLMToolCall(id="call-1", name="calculator_tool", arguments={"expression": "10 + 20"})],
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    model="fake-model",
                )
            return LLMResponse(text="The result is 30", prompt_tokens=10, completion_tokens=5, total_tokens=15, model="fake-model")

    fake_llm = FakeLLM()
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: fake_llm)
    workflow_id, run_id, _ = create_agent_workflow(db, tools_json=["calculator_tool"])

    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "calculate 10 + 20"})

    assert run.status == RunStatus.COMPLETED.value
    tool_call = db.query(ToolCall).filter(ToolCall.run_id == run_id).first()
    assert tool_call is not None
    assert json.loads(tool_call.input_json)["expression"] == "10 + 20"
    message = db.query(AgentMessage).filter(AgentMessage.run_id == run_id).first()
    assert message is not None
    assert "30" in message.content


@pytest.mark.asyncio
async def test_agent_node_sends_tool_result_back_to_llm(db, monkeypatch):
    captured_messages = []

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        async def generate(self, **kwargs):
            self.calls += 1
            captured_messages.append(kwargs.get("messages", []))
            if self.calls == 1:
                return LLMResponse(
                    text=None,
                    tool_calls=[LLMToolCall(id="call-1", name="calculator_tool", arguments={"expression": "10 + 20"})],
                    prompt_tokens=10,
                    completion_tokens=5,
                    total_tokens=15,
                    model="fake-model",
                )
            return LLMResponse(text="The result is 30", prompt_tokens=10, completion_tokens=5, total_tokens=15, model="fake-model")

    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLM())
    workflow_id, run_id, _ = create_agent_workflow(db, tools_json=["calculator_tool"])

    await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "calculate 10 + 20"})

    assert any(message.get("role") == "tool" and "30" in message.get("content", "") for message in captured_messages[-1])


@pytest.mark.asyncio
async def test_llm_cannot_call_unconfigured_tool(db, monkeypatch):
    class FakeLLM:
        async def generate(self, **kwargs):
            return LLMResponse(
                text=None,
                tool_calls=[LLMToolCall(id="call-1", name="calculator_tool", arguments={"expression": "10 + 20"})],
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                model="fake-model",
            )

    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLM())
    workflow_id, run_id, _ = create_agent_workflow(db, tools_json=[])

    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "calculate 10 + 20"})

    assert run.status == RunStatus.FAILED.value
    assert db.query(ToolCall).filter(ToolCall.run_id == run_id, ToolCall.status == RunStatus.COMPLETED.value).count() == 0
    assert db.query(RunLog).filter(RunLog.run_id == run_id, RunLog.event_type == WebSocketEventType.GUARDRAIL_VIOLATION.value).count() > 0


@pytest.mark.asyncio
async def test_llm_tool_call_loop_limit(db, monkeypatch):
    class FakeLLM:
        async def generate(self, **kwargs):
            return LLMResponse(
                text=None,
                tool_calls=[LLMToolCall(id=str(uuid.uuid4()), name="calculator_tool", arguments={"expression": "10 + 20"})],
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                model="fake-model",
            )

    monkeypatch.setenv("MAX_LLM_TOOL_CALL_ROUNDS", "1")
    monkeypatch.setattr("app.runtime.engine.get_llm_client", lambda: FakeLLM())
    workflow_id, run_id, _ = create_agent_workflow(db, tools_json=["calculator_tool"])

    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "calculate 10 + 20"})

    assert run.status == RunStatus.FAILED.value
    assert "Max LLM tool-call rounds" in run.error_message


@pytest.mark.asyncio
async def test_explicit_tool_node_still_works(db):
    workflow_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    db.add(Workflow(id=workflow_id, name="Explicit tool workflow"))
    db.add(WorkflowNode(id="start-" + workflow_id, workflow_id=workflow_id, node_type=NodeType.START.value))
    db.add(
        WorkflowNode(
            id="tool-" + workflow_id,
            workflow_id=workflow_id,
            node_type=NodeType.TOOL.value,
            tool_name="calculator_tool",
            config_json=json.dumps({"expression": "10 + 20"}),
        )
    )
    db.add(WorkflowNode(id="end-" + workflow_id, workflow_id=workflow_id, node_type=NodeType.END.value))
    db.add(WorkflowEdge(workflow_id=workflow_id, source_node_id="start-" + workflow_id, target_node_id="tool-" + workflow_id, condition_type=EdgeCondition.ALWAYS.value))
    db.add(WorkflowEdge(workflow_id=workflow_id, source_node_id="tool-" + workflow_id, target_node_id="end-" + workflow_id, condition_type=EdgeCondition.ALWAYS.value))
    db.add(WorkflowRun(id=run_id, workflow_id=workflow_id, status=RunStatus.QUEUED.value, input_json='{"message": "calculate"}'))
    db.commit()

    run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": "calculate"})

    assert run.status == RunStatus.COMPLETED.value
    tool_call = db.query(ToolCall).filter(ToolCall.run_id == run_id).first()
    assert tool_call is not None
    assert json.loads(tool_call.output_json)["result"] == 30
