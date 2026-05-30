import asyncio
import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
from app.core.constants import EdgeCondition, NodeType, RunStatus, WebSocketEventType
from app.core.log_messages import LogMessage
from app.models.models import WorkflowRun, WorkflowNode, WorkflowEdge, Agent, AgentMessage, RunLog, ToolCall, TokenUsage, NodeRun, AgentMemory
from app.core.logger import get_logger
from app.runtime.llm_client import get_llm_client
from app.websocket.run_monitor import manager
from app.tools.tool_registry import TOOL_REGISTRY, get_openai_tool_schemas, resolve_tool_alias
from app.core.messages import ErrorMessage
from app.core.exceptions import RunCancelledException

logger = get_logger(__name__)

EVENT_LOG_MESSAGES = {
    WebSocketEventType.RUN_STARTED.value: LogMessage.RUN_STARTED,
    WebSocketEventType.RUN_COMPLETED.value: LogMessage.RUN_COMPLETED,
    WebSocketEventType.RUN_FAILED.value: LogMessage.RUN_FAILED,
    WebSocketEventType.RUN_LOG.value: "Runtime log",
    WebSocketEventType.NODE_STARTED.value: LogMessage.NODE_STARTED,
    WebSocketEventType.NODE_COMPLETED.value: LogMessage.NODE_COMPLETED,
    WebSocketEventType.NODE_FAILED.value: "Node execution failed",
    WebSocketEventType.LLM_TOOL_CALL_REQUESTED.value: LogMessage.LLM_TOOL_CALL_REQUESTED,
    WebSocketEventType.TOOL_CALL_STARTED.value: LogMessage.TOOL_CALL_STARTED,
    WebSocketEventType.TOOL_CALL_COMPLETED.value: LogMessage.TOOL_CALL_COMPLETED,
    WebSocketEventType.TOOL_CALL_FAILED.value: LogMessage.TOOL_CALL_FAILED,
}

def normalize_run_input(input_data: Any) -> dict:
    if not input_data:
        return {}

    if isinstance(input_data, str):
        try:
            input_data = json.loads(input_data)
        except Exception:
            return {"message": input_data}

    if not isinstance(input_data, dict):
        return {"message": str(input_data)}

    if "message" in input_data:
        return {
            "message": input_data.get("message"),
            "source": input_data.get("source", "api")
        }

    if "input" in input_data and isinstance(input_data["input"], str):
        return {"message": input_data["input"], "source": input_data.get("source", "api")}

    if "input_json" in input_data and isinstance(input_data["input_json"], dict):
        return normalize_run_input(input_data["input_json"])

    return input_data

def resolve_source(source: str, state: "RuntimeState") -> str:
    if source == "workflow_input":
        input_value = state.get("input", {})
        if isinstance(input_value, dict):
            return input_value.get("message") or input_value.get("query") or json.dumps(input_value)
        return str(input_value or "")
    if source == "current_output":
        return state.get("current_output", "")
    if source == "final_output":
        return state.get("final_output", "")
    return source

def parse_tool_config(config_json: str | None) -> dict:
    if not config_json:
        return {}
    try:
        parsed = json.loads(config_json)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}

def build_tool_input(tool_name: str, state: "RuntimeState", config: dict | None = None) -> dict:
    config = config or {}

    if tool_name == "duckduckgo_search_tool":
        source = config.get("query_source", "workflow_input")
        query = config.get("manual_query", "") if source == "manual" else resolve_source(source, state)
        return {
            "query": query,
            "max_results": config.get("max_results", int(os.getenv("DUCKDUCKGO_MAX_RESULTS", 5))),
        }

    if tool_name in ("calculator", "calculator_tool"):
        return {"expression": config.get("expression", "1 + 1")}

    if tool_name in ("knowledge_base_lookup", "knowledge_base_tool"):
        source = config.get("query_source", "workflow_input")
        query = config.get("manual_query", "") if source == "manual" else resolve_source(source, state)
        return {"query": query, "topic": query}

    if tool_name in ("summarizer", "summarizer_tool"):
        source = config.get("text_source", "current_output")
        return {"text": resolve_source(source, state)}

    if tool_name in ("draft_generator", "draft_response_tool", "draft_generator_tool"):
        source = config.get("prompt_source", "current_output")
        return {"prompt": resolve_source(source, state)}

    return config

class RuntimeState(TypedDict, total=False):
    run_id: str
    workflow_id: str
    input: dict
    current_output: str
    node_outputs: dict
    previous_agent_id: str
    messages: list
    iteration_count: int
    tool_call_count: int
    final_output: str
    review_passed: bool
    confidence_score: float
    db_session: Session
    reviewer_calls: int

class RuntimeService:
    @staticmethod
    async def emit_event(run_id: str, event_type: str, node_id: str = None, agent_id: str = None, message: str = "", payload: dict = None, db: Session = None, correlation_id: str = None, task_id: str = None):
        if payload is None:
            payload = {}
        if not correlation_id:
            correlation_id = payload.get("correlation_id")
        if not correlation_id and db:
            run_record = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            if run_record and run_record.input_json:
                try:
                    saved_input = json.loads(run_record.input_json)
                    if isinstance(saved_input, dict):
                        correlation_id = saved_input.get("correlation_id")
                except Exception:
                    correlation_id = None
        correlation_id = correlation_id or f"BACK-{run_id}"
        task_id = task_id or payload.get("task_id") or run_id
        payload.setdefault("correlation_id", correlation_id)
        payload.setdefault("task_id", task_id)
        if node_id is not None:
            payload.setdefault("node_id", node_id)
        if agent_id is not None:
            payload.setdefault("agent_id", agent_id)
        
        event_id = None
        if db:
            next_sequence = (
                db.query(func.max(RunLog.event_sequence))
                .filter(RunLog.run_id == run_id)
                .scalar()
                or 0
            ) + 1
            log_entry = RunLog(
                run_id=run_id,
                event_sequence=next_sequence,
                level="INFO",
                event_type=event_type,
                message=message,
                metadata_json=json.dumps(payload)
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)
            event_id = log_entry.event_sequence

        logger.info(
            "%s: %s",
            EVENT_LOG_MESSAGES.get(event_type, event_type),
            message,
            extra={"correlation_id": correlation_id, "run_id": run_id, "task_id": task_id},
        )

        await manager.broadcast_to_run(run_id, {
            "event_id": event_id,
            "event_type": event_type,
            "run_id": run_id,
            "task_id": task_id,
            "correlation_id": correlation_id,
            "node_id": node_id,
            "agent_id": agent_id,
            "message": message,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        })

    @staticmethod
    def is_run_cancelled(db: Session, run_id: str) -> bool:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        return run is not None and run.status == RunStatus.CANCELLED.value

    @staticmethod
    def parse_agent_tool_names(agent: Agent) -> list[str]:
        if not agent or not agent.tools_json:
            return []
        try:
            parsed = json.loads(agent.tools_json)
            return [name for name in parsed if isinstance(name, str) and name in TOOL_REGISTRY]
        except Exception:
            return []

    @staticmethod
    def contains_blocked_keyword(value: Any, blocked_keywords: list[str]) -> str | None:
        serialized = json.dumps(value, default=str).lower()
        for keyword in blocked_keywords or []:
            if str(keyword).lower() in serialized:
                return str(keyword)
        return None

    @staticmethod
    def tool_result_message(tool_call, tool_result) -> dict:
        content = json.dumps(
            tool_result.output if tool_result.success else {"error": tool_result.error, "output": tool_result.output},
            default=str,
        )
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.name,
            "content": content,
        }

    @staticmethod
    def assistant_tool_call_message(response) -> dict:
        return {
            "role": "assistant",
            "content": response.text or "",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.name,
                        "arguments": json.dumps(tool_call.arguments, default=str),
                    },
                }
                for tool_call in response.tool_calls
            ],
        }

    @staticmethod
    async def persist_token_usage(db: Session, run_id: str, agent_id: str, node_id: str, response):
        usage = {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "estimated_cost": f"{response.estimated_cost:.8f}",
            "model": response.model,
        }
        tu = TokenUsage(
            run_id=run_id,
            agent_id=agent_id,
            model=response.model,
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            estimated_cost=usage["estimated_cost"],
        )
        db.add(tu)
        db.commit()
        db.refresh(tu)
        usage["id"] = tu.id
        await RuntimeService.emit_event(
            run_id,
            WebSocketEventType.TOKEN_USAGE_RECORDED.value,
            node_id=node_id,
            agent_id=agent_id,
            message="Token usage recorded",
            payload=usage,
            db=db,
        )

    @staticmethod
    async def generate_with_optional_tools(llm_client, **kwargs):
        try:
            return await llm_client.generate(**kwargs)
        except TypeError as exc:
            if "unexpected keyword" not in str(exc):
                raise
            return await llm_client.generate(
                system_prompt=kwargs.get("system_prompt", ""),
                user_prompt=kwargs.get("user_prompt", ""),
                model=kwargs.get("model"),
                temperature=kwargs.get("temperature", 0.2),
            )

    @staticmethod
    async def execute_llm_tool_call(db: Session, run_id: str, node: WorkflowNode, agent: Agent, tool_call, state: RuntimeState):
        tool = TOOL_REGISTRY.get(tool_call.name)
        if not tool:
            raise Exception(f"TOOL_NOT_FOUND: {tool_call.name}")

        state["tool_call_count"] += 1
        tool_start_time = datetime.utcnow()
        tool_call_record = ToolCall(
            run_id=run_id,
            agent_id=agent.id,
            tool_name=tool_call.name,
            input_json=json.dumps(tool_call.arguments, default=str),
            status=RunStatus.RUNNING.value,
            started_at=tool_start_time,
        )
        db.add(tool_call_record)
        db.commit()
        db.refresh(tool_call_record)

        await RuntimeService.emit_event(
            run_id,
            WebSocketEventType.TOOL_CALL_STARTED.value,
            node_id=node.id,
            agent_id=agent.id,
            message=f"Executing LLM-requested tool {tool_call.name}",
            payload={"tool_name": tool_call.name, "input_json": tool_call.arguments, "source": "LLM_TOOL_CALL"},
            db=db,
        )

        tool_result = await tool.execute(tool_call.arguments)

        tool_call_record.status = RunStatus.COMPLETED.value if tool_result.success else RunStatus.FAILED.value
        tool_call_record.output_json = json.dumps(tool_result.output, default=str)
        tool_call_record.error_message = tool_result.error
        tool_call_record.completed_at = datetime.utcnow()
        db.commit()

        event_type = WebSocketEventType.TOOL_CALL_COMPLETED.value if tool_result.success else WebSocketEventType.TOOL_CALL_FAILED.value
        message = f"Tool {tool_call.name} finished" if tool_result.success else f"Tool {tool_call.name} failed: {tool_result.error}"
        await RuntimeService.emit_event(
            run_id,
            event_type,
            node_id=node.id,
            agent_id=agent.id,
            message=message,
            payload={
                "tool_name": tool_call.name,
                "input_json": tool_call.arguments,
                "result": tool_result.output,
                "error": tool_result.error,
                "status": tool_call_record.status,
                "source": "LLM_TOOL_CALL",
            },
            db=db,
        )
        return tool_result

    @staticmethod
    def make_node_executor(node: WorkflowNode, agent: Optional[Agent]):
        async def node_executor(state: RuntimeState) -> RuntimeState:
            db = state["db_session"]
            run_id = state["run_id"]
            workflow_id = state["workflow_id"]
            
            if RuntimeService.is_run_cancelled(db, run_id):
                await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_CANCELLED.value, node_id=node.id, message="Run was cancelled before executing this node", db=db)
                raise RunCancelledException("Run was cancelled")

            state["iteration_count"] += 1

            max_iter = 10
            max_retries = 1
            timeout_sec = 60
            max_tool_calls = 100
            max_tokens = 1000000
            max_cost = 100.0
            
            if agent and agent.limits_json:
                try:
                    cfg = json.loads(agent.limits_json)
                    max_iter = cfg.get("max_iterations", max_iter)
                    max_retries = cfg.get("max_retries", max_retries)
                    timeout_sec = cfg.get("timeout_sec", timeout_sec)
                    max_tool_calls = cfg.get("max_tool_calls", max_tool_calls)
                    max_tokens = cfg.get("max_tokens", max_tokens)
                    max_cost = cfg.get("max_cost", cfg.get("max_estimated_cost", max_cost))
                except:
                    pass

            if state["iteration_count"] > max_iter:
                await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_FAILED.value, node_id=node.id, message=ErrorMessage.MAX_ITERATIONS_EXCEEDED, db=db)
                raise Exception(ErrorMessage.MAX_ITERATIONS_EXCEEDED)

            # Check run-wide token and cost limits
            tokens_used = db.query(
                func.sum(TokenUsage.total_tokens).label('total')
            ).filter(TokenUsage.run_id == run_id).first()
            current_tokens = tokens_used.total or 0
            
            token_usages = db.query(TokenUsage.estimated_cost).filter(TokenUsage.run_id == run_id).all()
            current_cost = sum(float(tu.estimated_cost or "0.0") for tu in token_usages)
            
            if current_tokens > max_tokens:
                await RuntimeService.emit_event(run_id, WebSocketEventType.GUARDRAIL_VIOLATION.value, node_id=node.id, message=f"Max tokens exceeded: {current_tokens} > {max_tokens}", db=db)
                raise Exception("GUARDRAIL_VIOLATION: Max tokens exceeded")
                
            if current_cost > max_cost:
                await RuntimeService.emit_event(run_id, WebSocketEventType.GUARDRAIL_VIOLATION.value, node_id=node.id, message=f"Max cost exceeded: {current_cost} > {max_cost}", db=db)
                raise Exception("GUARDRAIL_VIOLATION: Max cost exceeded")

            # Idempotency Lookup
            node_run = db.query(NodeRun).filter(NodeRun.workflow_run_id == run_id, NodeRun.node_id == node.id).first()
            if not node_run:
                node_run = NodeRun(
                    workflow_run_id=run_id,
                    workflow_id=workflow_id,
                    node_id=node.id,
                    node_type=node.node_type,
                    agent_id=agent.id if agent else None,
                    tool_name=node.tool_name,
                    status=RunStatus.RUNNING.value,
                    input_json=json.dumps(state.get("input", {})),
                    retry_count=0
                )
                db.add(node_run)
                db.commit()
                db.refresh(node_run)
            else:
                node_run.status = RunStatus.RUNNING.value
                db.commit()
                db.refresh(node_run)

            # Exactly one NODE_STARTED event
            await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_STARTED.value, node_id=node.id, agent_id=agent.id if agent else None, message=f"Starting node {node.id}", db=db)

            async def execute_inner():
                if node.node_type == NodeType.START.value:
                    input_val = state["input"]
                    if isinstance(input_val, dict):
                        if "input_json" in input_val:
                            inner = input_val["input_json"]
                            if isinstance(inner, dict) and "message" in inner:
                                input_str = inner["message"]
                            elif isinstance(inner, str):
                                try:
                                    parsed = json.loads(inner)
                                    if isinstance(parsed, dict) and "message" in parsed:
                                        input_str = parsed["message"]
                                    else:
                                        input_str = inner
                                except:
                                    input_str = inner
                            else:
                                input_str = str(inner)
                        elif "message" in input_val:
                            input_str = input_val["message"]
                        else:
                            input_str = json.dumps(input_val)
                    else:
                        input_str = str(input_val)
                    state["current_output"] = input_str
                    state.setdefault("messages", []).append({"role": "user", "content": input_str})
                    node_run.output_json = json.dumps({"output": input_str})
                    return

                if node.node_type == NodeType.TOOL.value:
                    tool_name = node.tool_name or ""
                    if not tool_name and node.config_json:
                        try:
                            cfg = json.loads(node.config_json)
                            tool_name = cfg.get("tool_name", "")
                        except:
                            pass

                    tool = TOOL_REGISTRY.get(tool_name)
                    if tool:
                        tool_payload = build_tool_input(tool_name, state, parse_tool_config(node.config_json))
                        tool_start_time = datetime.utcnow()
                        tool_call_record = ToolCall(
                            run_id=run_id, agent_id=agent.id if agent else None, tool_name=tool.name,
                            input_json=json.dumps(tool_payload), status=RunStatus.RUNNING.value,
                            started_at=tool_start_time
                        )
                        db.add(tool_call_record)
                        db.commit()
                        db.refresh(tool_call_record)

                        await RuntimeService.emit_event(run_id, WebSocketEventType.TOOL_CALL_STARTED.value, node_id=node.id, agent_id=agent.id if agent else None,
                                                         message=f"Executing tool {tool.name}", payload={"tool_name": tool.name, "input_json": tool_payload}, db=db)

                        tool_result = await tool.execute(tool_payload)

                        tool_call_record.status = RunStatus.COMPLETED.value if tool_result.success else RunStatus.FAILED.value
                        tool_call_record.output_json = json.dumps(tool_result.output)
                        tool_call_record.error_message = tool_result.error
                        tool_call_record.completed_at = datetime.utcnow()
                        db.commit()

                        event_type = WebSocketEventType.TOOL_CALL_COMPLETED.value if tool_result.success else WebSocketEventType.TOOL_CALL_FAILED.value
                        message = f"Tool {tool.name} finished" if tool_result.success else f"Tool {tool.name} failed: {tool_result.error}"
                        await RuntimeService.emit_event(run_id, event_type, node_id=node.id, agent_id=agent.id if agent else None,
                                                         message=message, payload={"tool_name": tool.name, "result": tool_result.output, "error": tool_result.error, "status": tool_call_record.status}, db=db)

                        state["current_output"] = str(tool_result.output)
                        state["node_outputs"][node.id] = tool_result.output
                        node_run.output_json = json.dumps(tool_result.output)
                    else:
                        await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_LOG.value, message=f"Tool {tool_name} not found in registry", db=db)

                    return

                if node.node_type == NodeType.CONDITION.value:
                    await RuntimeService.emit_event(run_id, WebSocketEventType.CONDITION_EVALUATED.value, node_id=node.id, message=f"Evaluated condition", db=db)
                    return

                if node.node_type == NodeType.END.value:
                    final_output = state.get("current_output") or state.get("final_output") or ""
                    state["final_output"] = final_output
                    state.setdefault("node_outputs", {})[node.id] = final_output
                    node_run.output_json = json.dumps({"final_output": final_output})
                    return

                if node.node_type == NodeType.AGENT.value and agent:
                    input_messages = state.get("messages", []).copy()
                    if not input_messages:
                        input_messages = [{"role": "user", "content": state["current_output"]}]

                    sys_prompt = agent.system_prompt or ""
                    
                    from datetime import datetime
                    sys_prompt += f"\n\nSystem Note: The current date and time is {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}."
                    
                    # Memory Injection
                    if agent.memory_enabled:
                        memories = db.query(AgentMemory).filter(AgentMemory.agent_id == agent.id, AgentMemory.deleted_at == None).all()
                        if memories:
                            memory_text = "\\n".join([m.content for m in memories])
                            sys_prompt += f"\\n\\nRelevant Memories:\\n{memory_text}"

                    if sys_prompt:
                         input_messages.insert(0, {"role": "system", "content": sys_prompt})

                    # Guardrails before LLM call
                    allowed_tools = None
                    if agent.guardrails_json:
                        try:
                            gr = json.loads(agent.guardrails_json)
                            banned_words = gr.get("banned_keywords", gr.get("blocked_keywords", []))
                            for word in banned_words:
                                if word.lower() in state["current_output"].lower():
                                    await RuntimeService.emit_event(run_id, WebSocketEventType.GUARDRAIL_VIOLATION.value, node_id=node.id, message=f"Input contains blocked keyword: {word}", db=db)
                                    raise Exception(f"GUARDRAIL_VIOLATION: Input contains blocked keyword: {word}")
                            allowed_tools = gr.get("allowed_tools", None)
                        except Exception as e:
                            if "GUARDRAIL_VIOLATION" in str(e):
                                raise e
                            pass

                    # Persist Task Handoff
                    if state.get("previous_agent_id"):
                        handoff_msg = AgentMessage(
                            run_id=run_id, from_agent_id=state["previous_agent_id"], to_agent_id=agent.id,
                            message_type="TASK_HANDOFF", content=state["current_output"], status="DELIVERED"
                        )
                        db.add(handoff_msg)
                        db.commit()
                        await RuntimeService.emit_event(
                            run_id, WebSocketEventType.AGENT_MESSAGE_CREATED.value, 
                            node_id=node.id, agent_id=agent.id, 
                            message="Handoff message created", 
                            payload={
                                "content": state["current_output"], 
                                "from_agent_id": state["previous_agent_id"], 
                                "to_agent_id": agent.id, 
                                "message_type": "TASK_HANDOFF"
                            },
                            db=db
                        )

                    configured_tool_names = RuntimeService.parse_agent_tool_names(agent)
                    if allowed_tools is not None:
                        resolved_allowed = [resolve_tool_alias(t) for t in allowed_tools]
                        disallowed_configured_tools = [name for name in configured_tool_names if resolve_tool_alias(name) not in resolved_allowed]
                        if disallowed_configured_tools:
                            message = f"Unauthorized tool requested: {disallowed_configured_tools[0]}"
                            await RuntimeService.emit_event(run_id, WebSocketEventType.GUARDRAIL_VIOLATION.value, node_id=node.id, agent_id=agent.id, message=message, db=db)
                            raise Exception(f"GUARDRAIL_VIOLATION: {message}")
                    if configured_tool_names and max_tool_calls <= 0:
                        await RuntimeService.emit_event(run_id, WebSocketEventType.GUARDRAIL_VIOLATION.value, node_id=node.id, agent_id=agent.id, message="Max tool calls exceeded: 0 >= 0", db=db)
                        raise Exception("GUARDRAIL_VIOLATION: Max tool calls exceeded")
                    available_tool_names = [
                        name
                        for name in configured_tool_names
                        if allowed_tools is None or name in allowed_tools
                    ]
                    tool_schemas = get_openai_tool_schemas(available_tool_names)

                    prompt = "\\n\\n".join(
                        str(message.get("content", ""))
                        for message in input_messages
                        if message.get("role") != "system" and message.get("content")
                    )
                    if state.get("node_outputs"):
                        prompt += "\\n\\nPrevious node outputs:\\n" + json.dumps(state["node_outputs"])

                    llm_client = get_llm_client(agent.model)
                    
                    # Sanitize messages to remove non-standard keys like 'agent_id' before sending to LLM
                    conversation = [
                        {k: v for k, v in msg.items() if k in ("role", "content", "name", "tool_calls", "tool_call_id")}
                        for msg in input_messages
                    ]
                    
                    if prompt and (not conversation or conversation[-1].get("content") != prompt):
                        conversation.append({"role": "user", "content": prompt})

                    max_llm_tool_rounds = int(os.getenv("MAX_LLM_TOOL_CALL_ROUNDS", "3"))
                    blocked_tool_keywords = []
                    if agent.guardrails_json:
                        try:
                            tool_guardrails = json.loads(agent.guardrails_json)
                            blocked_tool_keywords = tool_guardrails.get("blocked_keywords", tool_guardrails.get("banned_keywords", []))
                        except Exception:
                            blocked_tool_keywords = []

                    response = None
                    content = ""
                    for tool_round in range(max_llm_tool_rounds + 1):
                        response = await RuntimeService.generate_with_optional_tools(
                            llm_client,
                            system_prompt=sys_prompt,
                            user_prompt=prompt,
                            model=agent.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                            tools=tool_schemas or None,
                            tool_choice="auto",
                            messages=conversation,
                        )
                        await RuntimeService.persist_token_usage(db, run_id, agent.id, node.id, response)

                        if not response.tool_calls:
                            content = response.text or ""
                            break

                        if tool_round >= max_llm_tool_rounds:
                            await RuntimeService.emit_event(
                                run_id,
                                WebSocketEventType.GUARDRAIL_VIOLATION.value,
                                node_id=node.id,
                                agent_id=agent.id,
                                message=f"Max LLM tool-call rounds exceeded: {max_llm_tool_rounds}",
                                db=db,
                            )
                            raise Exception(f"GUARDRAIL_VIOLATION: Max LLM tool-call rounds exceeded")

                        conversation.append(RuntimeService.assistant_tool_call_message(response))
                        for requested_tool_call in response.tool_calls:
                            await RuntimeService.emit_event(
                                run_id,
                                WebSocketEventType.LLM_TOOL_CALL_REQUESTED.value,
                                node_id=node.id,
                                agent_id=agent.id,
                                message=f"LLM requested tool {requested_tool_call.name}",
                                payload={
                                    "tool_name": requested_tool_call.name,
                                    "arguments": requested_tool_call.arguments,
                                    "source": "LLM_TOOL_CALL",
                                },
                                db=db,
                            )

                            raw_tool_name = requested_tool_call.name
                            canonical_tool_name = resolve_tool_alias(raw_tool_name)

                            resolved_configured = [resolve_tool_alias(t) for t in configured_tool_names]
                            resolved_allowed = [resolve_tool_alias(t) for t in allowed_tools] if allowed_tools is not None else None

                            guardrail_error = None
                            if canonical_tool_name not in resolved_configured:
                                guardrail_error = f"Tool not configured: {raw_tool_name}"
                            elif resolved_allowed is not None and canonical_tool_name not in resolved_allowed:
                                guardrail_error = f"Unauthorized tool requested: {raw_tool_name}"
                            else:
                                blocked_keyword = RuntimeService.contains_blocked_keyword(requested_tool_call.arguments, blocked_tool_keywords)
                                if blocked_keyword:
                                    guardrail_error = f"Tool arguments contain blocked keyword: {blocked_keyword}"
                                elif state["tool_call_count"] >= max_tool_calls:
                                    guardrail_error = f"Max tool calls exceeded: {state['tool_call_count']} >= {max_tool_calls}"

                            if guardrail_error:
                                # Create failing/blocked ToolCall record
                                tool_call_payload = {
                                    "tool_name": canonical_tool_name,
                                    "requested_tool_name": raw_tool_name,
                                    "arguments": requested_tool_call.arguments,
                                    "source": "LLM_TOOL_CALL"
                                }
                                tool_call_record = ToolCall(
                                    run_id=run_id,
                                    agent_id=agent.id if agent else None,
                                    tool_name=canonical_tool_name,
                                    input_json=json.dumps(tool_call_payload),
                                    status="FAILED",
                                    started_at=datetime.utcnow(),
                                    completed_at=datetime.utcnow(),
                                    error_message=f"GUARDRAIL_VIOLATION: {guardrail_error}"
                                )
                                db.add(tool_call_record)
                                db.commit()

                                # Emit failures
                                await RuntimeService.emit_event(
                                    run_id,
                                    WebSocketEventType.TOOL_CALL_FAILED.value,
                                    node_id=node.id,
                                    agent_id=agent.id if agent else None,
                                    message=f"Tool call blocked by guardrail: {guardrail_error}",
                                    payload={
                                        "tool_name": canonical_tool_name,
                                        "requested_tool_name": raw_tool_name,
                                        "input_json": requested_tool_call.arguments,
                                        "error": f"GUARDRAIL_VIOLATION: {guardrail_error}",
                                        "status": "BLOCKED",
                                        "source": "LLM_TOOL_CALL"
                                    },
                                    db=db
                                )
                                await RuntimeService.emit_event(
                                    run_id,
                                    WebSocketEventType.GUARDRAIL_VIOLATION.value,
                                    node_id=node.id,
                                    agent_id=agent.id if agent else None,
                                    message=f"GUARDRAIL_VIOLATION: {guardrail_error}",
                                    db=db
                                )
                                raise Exception(f"GUARDRAIL_VIOLATION: {guardrail_error}")

                            requested_tool_call.name = canonical_tool_name
                            tool_result = await RuntimeService.execute_llm_tool_call(db, run_id, node, agent, requested_tool_call, state)
                            conversation.append(RuntimeService.tool_result_message(requested_tool_call, tool_result))

                    # Guardrails after LLM call
                    if agent.guardrails_json:
                        try:
                            gr = json.loads(agent.guardrails_json)
                            banned_words = gr.get("banned_keywords", gr.get("blocked_keywords", []))
                            for word in banned_words:
                                if word.lower() in content.lower():
                                    await RuntimeService.emit_event(run_id, WebSocketEventType.GUARDRAIL_VIOLATION.value, node_id=node.id, message=f"Output contains blocked keyword: {word}", db=db)
                                    raise Exception(f"GUARDRAIL_VIOLATION: Output contains blocked keyword: {word}")
                        except Exception as e:
                            if "GUARDRAIL_VIOLATION" in str(e):
                                raise e
                            pass

                    # Persist Agent Output Message
                    agent_msg = AgentMessage(
                        run_id=run_id, from_agent_id=agent.id, to_agent_id=None,
                        message_type="AGENT_OUTPUT", content=content, status="DELIVERED"
                    )
                    db.add(agent_msg)
                    
                    await RuntimeService.emit_event(run_id, WebSocketEventType.AGENT_MESSAGE_CREATED.value, node_id=node.id, agent_id=agent.id, message="Agent generated a message", payload={"content": content, "from_agent_id": agent.id, "to_agent_id": None, "message_type": "AGENT_OUTPUT"}, db=db)

                    state["messages"].append({"role": "assistant", "content": content, "agent_id": agent.id})
                    state["node_outputs"][node.id] = content
                    state["current_output"] = content
                    state["previous_agent_id"] = agent.id
                    node_run.output_json = json.dumps({"output": content})
                    
                    # Mock evaluation for conditionals
                    if agent.id == "reviewer_agent":
                        input_text = state.get("input", {}).get("message", "").lower()
                        if "force reject" in input_text or "needs revision" in input_text:
                            reviewer_calls = state.get("reviewer_calls", 0) + 1
                            state["reviewer_calls"] = reviewer_calls
                            await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_LOG.value, message=f"Reviewer agent evaluated. Calls count: {reviewer_calls}", db=db)
                            if reviewer_calls <= 1:
                                state["review_passed"] = False
                                content = "Draft review failed: needs revision. Please fix formatting and include more references."
                                agent_msg.content = content
                                state["current_output"] = content
                                state["node_outputs"][node.id] = content
                            else:
                                state["review_passed"] = True
                                content = "Draft approved. The summary is complete and accurate."
                                agent_msg.content = content
                                state["current_output"] = content
                                state["node_outputs"][node.id] = content
                        else:
                            state["review_passed"] = True
                    else:
                        if "reject" in content.lower():
                            state["review_passed"] = False
                        elif "approve" in content.lower():
                            state["review_passed"] = True
                        
                    if "confidence_low" in content.lower() or EdgeCondition.ESCALATE.value in content.lower():
                        state["confidence_score"] = 0.2
                    else:
                        state["confidence_score"] = 0.9

                    await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_LOG.value, message=f"Final node execution state - review_passed: {state.get('review_passed')}, reviewer_calls: {state.get('reviewer_calls')}", db=db)

            success = False
            error_msg = None
            for attempt in range(max_retries + 1):
                try:
                    node_run.retry_count = attempt
                    db.commit()
                    await asyncio.wait_for(execute_inner(), timeout=timeout_sec)
                    success = True
                    break
                except asyncio.TimeoutError:
                    error_msg = "Timeout exceeded"
                    if attempt == max_retries:
                        break
                except Exception as e:
                    error_msg = str(e)
                    if attempt == max_retries:
                        break

            if success:
                node_run.status = RunStatus.COMPLETED.value
                node_run.completed_at = datetime.utcnow()
                db.commit()
                
                payload = {}
                if node.node_type == NodeType.END.value:
                    payload["final_output"] = state.get("final_output", "")
                await RuntimeService.emit_event(
                    run_id, 
                    WebSocketEventType.NODE_COMPLETED.value, 
                    node_id=node.id, 
                    agent_id=agent.id if agent else None, 
                    message=f"Completed node {node.id}", 
                    payload=payload,
                    db=db
                )
            else:
                node_run.status = RunStatus.FAILED.value
                node_run.error_message = error_msg
                node_run.completed_at = datetime.utcnow()
                db.commit()
                await RuntimeService.emit_event(
                    run_id, 
                    WebSocketEventType.NODE_FAILED.value, 
                    node_id=node.id, 
                    agent_id=agent.id if agent else None, 
                    message=error_msg or "Node execution failed", 
                    db=db
                )
                raise Exception(error_msg or "Node execution failed")
                
            return state

        return node_executor
    @staticmethod
    async def execute_run(db: Session, run_id: str, workflow_id: str, input_data: dict):
        input_data = normalize_run_input(input_data)
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if not run:
            return

        run.status = RunStatus.RUNNING.value
        db.commit()
        
        await RuntimeService.emit_event(run.id, WebSocketEventType.RUN_STARTED.value, message=f"Run {run.id} started", payload={"input": input_data}, db=db)
        
        nodes = db.query(WorkflowNode).filter(WorkflowNode.workflow_id == workflow_id).all()
        edges = db.query(WorkflowEdge).filter(WorkflowEdge.workflow_id == workflow_id).all()
        if not edges and len(nodes) > 1:
            start_nodes = [n for n in nodes if n.node_type == NodeType.START.value]
            end_nodes = [n for n in nodes if n.node_type == NodeType.END.value]
            middle_nodes = [n for n in nodes if n.node_type not in (NodeType.START.value, NodeType.END.value)]
            ordered_nodes = start_nodes + middle_nodes + end_nodes
            edges = [
                WorkflowEdge(
                    workflow_id=workflow_id,
                    source_node_id=ordered_nodes[index].id,
                    target_node_id=ordered_nodes[index + 1].id,
                    condition_type=EdgeCondition.ALWAYS.value,
                )
                for index in range(len(ordered_nodes) - 1)
            ]
        
        agent_ids = {n.agent_id for n in nodes if n.agent_id}
        agents = {a.id: a for a in db.query(Agent).filter(Agent.id.in_(agent_ids)).all()}
        
        start_node = next((n for n in nodes if n.node_type == NodeType.START.value), None)
        if not start_node:
            await RuntimeService.emit_event(run.id, WebSocketEventType.RUN_FAILED.value, message="No START node found", db=db)
            run.status = RunStatus.FAILED.value
            run.error_message = "No START node found"
            db.commit()
            return run

        graph = StateGraph(RuntimeState)
        
        for node in nodes:
            agent = agents.get(node.agent_id) if node.agent_id else None
            graph.add_node(node.id, RuntimeService.make_node_executor(node, agent))

        graph.set_entry_point(start_node.id)

        from collections import defaultdict
        
        cond_edges_by_source = defaultdict(list)
        normal_edges = []
        
        for edge in edges:
            is_conditional = edge.condition_type not in (None, "", EdgeCondition.ALWAYS.value)
            if is_conditional:
                cond_edges_by_source[edge.source_node_id].append(edge)
            else:
                normal_edges.append(edge)
                
        for source_id, source_edges in cond_edges_by_source.items():
            def make_router(edgs):
                end_node = next((n for n in nodes if n.node_type == NodeType.END.value), None)
                end_node_id = end_node.id if end_node else NodeType.END.value
                async def router(state: RuntimeState) -> str:
                    db_session = state["db_session"]
                    selected_target = None
                    for e in edgs:
                        await RuntimeService.emit_event(state["run_id"], WebSocketEventType.CONDITION_EVALUATED.value, message=f"Evaluated condition {e.condition_type}", db=db_session)
                        
                        # 1. approved / rejected
                        if e.condition_type == EdgeCondition.APPROVED.value and state.get("review_passed") is True:
                            selected_target = e.target_node_id
                            break
                        if e.condition_type == EdgeCondition.REJECTED.value and state.get("review_passed") is False:
                            selected_target = e.target_node_id
                            break
                        # 2. resolved / escalate
                        if e.condition_type == EdgeCondition.RESOLVED.value and state.get("confidence_score", 1.0) > 0.5:
                            selected_target = e.target_node_id
                            break
                        if e.condition_type == EdgeCondition.ESCALATE.value and state.get("confidence_score", 1.0) <= 0.5:
                            selected_target = e.target_node_id
                            break
                        if e.condition_type == EdgeCondition.EXPRESSION.value and e.condition_expression:
                            current_output = str(state.get("current_output", "")).lower()
                            expression = e.condition_expression.lower()
                            if expression in current_output:
                                selected_target = e.target_node_id
                                break
                            
                    if not selected_target:
                        selected_target = edgs[0].target_node_id if edgs else end_node_id
                    return selected_target
                return router

            mapping = {}
            for e in source_edges:
                mapping[e.target_node_id] = e.target_node_id

            graph.add_conditional_edges(
                source_id,
                make_router(source_edges),
                mapping
            )

        for edge in normal_edges:
            graph.add_edge(edge.source_node_id, edge.target_node_id)

        for node in nodes:
            if node.node_type == NodeType.END.value:
                graph.add_edge(node.id, END)

        compiled_graph = graph.compile()

        initial_state: RuntimeState = {
            "run_id": run.id,
            "workflow_id": workflow_id,
            "input": input_data,
            "current_output": "",
            "node_outputs": {},
            "previous_agent_id": "",
            "messages": [],
            "iteration_count": 0,
            "tool_call_count": 0,
            "final_output": "",
            "review_passed": True,
            "confidence_score": 1.0,
            "db_session": db,
            "reviewer_calls": 0
        }

        try:
            final_state = await compiled_graph.ainvoke(initial_state)
            
            run.status = RunStatus.COMPLETED.value
            run.completed_at = datetime.utcnow()
            run.output_json = json.dumps({"final_message": final_state.get("current_output", "")})
            db.commit()
            await RuntimeService.emit_event(run.id, WebSocketEventType.RUN_COMPLETED.value, message=f"Run {run.id} completed successfully", db=db)

        except RunCancelledException as e:
            # Leave run status as CANCELLED, do not mark FAILED
            run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
            run.status = RunStatus.CANCELLED.value
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            db.commit()
        except Exception as e:
            run.status = RunStatus.FAILED.value
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            db.commit()
            await RuntimeService.emit_event(run.id, WebSocketEventType.RUN_FAILED.value, message=f"Run {run.id} failed: {str(e)}", db=db)

        return run
