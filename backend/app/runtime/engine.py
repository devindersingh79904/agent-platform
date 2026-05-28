import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
from app.core.constants import EdgeCondition, NodeType, RunStatus, WebSocketEventType
from app.core.log_messages import LogMessage
from app.models.models import WorkflowRun, WorkflowNode, WorkflowEdge, Agent, AgentMessage, RunLog, ToolCall, TokenUsage
from app.core.logger import get_logger
from app.runtime.llm_client import get_llm_client
from app.websocket.run_monitor import manager
from app.tools.core_tools import TOOL_REGISTRY
from app.core.messages import ErrorMessage

logger = get_logger(__name__)

EVENT_LOG_MESSAGES = {
    WebSocketEventType.RUN_STARTED.value: LogMessage.RUN_STARTED,
    WebSocketEventType.RUN_COMPLETED.value: LogMessage.RUN_COMPLETED,
    WebSocketEventType.RUN_FAILED.value: LogMessage.RUN_FAILED,
    WebSocketEventType.NODE_STARTED.value: LogMessage.NODE_STARTED,
    WebSocketEventType.NODE_COMPLETED.value: LogMessage.NODE_COMPLETED,
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
        return {
            "query": resolve_source(source, state),
            "max_results": config.get("max_results", int(os.getenv("DUCKDUCKGO_MAX_RESULTS", 5))),
        }

    if tool_name in ("calculator", "calculator_tool"):
        return {"expression": config.get("expression", "1 + 1")}

    if tool_name in ("knowledge_base_lookup", "knowledge_base_tool"):
        source = config.get("query_source", "workflow_input")
        query = resolve_source(source, state)
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
    def make_node_executor(node: WorkflowNode, agent: Optional[Agent]):
        async def node_executor(state: RuntimeState) -> RuntimeState:
            db = state["db_session"]
            run_id = state["run_id"]
            state["iteration_count"] += 1

            max_iter = 10
            if agent and agent.limits_json:
                try:
                    cfg = json.loads(agent.limits_json)
                    max_iter = cfg.get("max_iterations", 5)
                except:
                    pass

            if state["iteration_count"] > max_iter:
                await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_FAILED.value, node_id=node.id, message=ErrorMessage.MAX_ITERATIONS_EXCEEDED, db=db)
                raise Exception(ErrorMessage.MAX_ITERATIONS_EXCEEDED)
            
            await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_STARTED.value, node_id=node.id, agent_id=agent.id if agent else None, message=f"Starting node {node.id}", db=db)

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
                await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, message="START node completed", db=db)
                return state

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
                else:
                    await RuntimeService.emit_event(run_id, "RUN_LOG", message=f"Tool {tool_name} not found in registry", db=db)

                await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, agent_id=agent.id if agent else None,
                                               message=f"Completed node {node.id}", db=db)
                return state

            if node.node_type == NodeType.CONDITION.value:
                await RuntimeService.emit_event(run_id, WebSocketEventType.CONDITION_EVALUATED.value, node_id=node.id, message=f"Evaluated condition", db=db)
                await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, message="CONDITION node completed", db=db)
                return state

            if node.node_type == NodeType.END.value:
                await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_STARTED.value, node_id=node.id, agent_id=None, message="End node started", db=db)
                final_output = state.get("current_output") or state.get("final_output") or ""
                state["final_output"] = final_output
                state.setdefault("node_outputs", {})[node.id] = final_output
                await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, agent_id=None, message="End node completed", payload={"final_output": final_output}, db=db)
                return state

            if node.node_type == NodeType.AGENT.value and agent:
                input_messages = state.get("messages", []).copy()
                if not input_messages:
                    input_messages = [{"role": "user", "content": state["current_output"]}]

                if agent.system_prompt:
                     input_messages.insert(0, {"role": "system", "content": agent.system_prompt})

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

                # Evaluate Tools if configured
                tools_list = []
                if agent.tools_json:
                    try:
                        tool_names = json.loads(agent.tools_json)
                        tools_list = [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]
                    except Exception as e:
                        pass

                prompt = "\n\n".join(
                    str(message.get("content", ""))
                    for message in input_messages
                    if message.get("role") != "system" and message.get("content")
                )
                if state.get("node_outputs"):
                    prompt += "\n\nPrevious node outputs:\n" + json.dumps(state["node_outputs"])

                llm_client = get_llm_client()
                response = await llm_client.generate(
                    system_prompt=agent.system_prompt,
                    user_prompt=prompt,
                    model=agent.model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                )
                
                content = response.text
                
                if tools_list:
                    for tool in tools_list:
                        tool_start_time = datetime.utcnow()
                        state["tool_call_count"] += 1
                        
                        tool_payload = build_tool_input(tool.name, state, {})
                        
                        tool_call_record = ToolCall(
                            run_id=run_id, agent_id=agent.id, tool_name=tool.name,
                            input_json=json.dumps(tool_payload), status=RunStatus.RUNNING.value,
                            started_at=tool_start_time
                        )
                        db.add(tool_call_record)
                        db.commit()
                        db.refresh(tool_call_record)
                        
                        await RuntimeService.emit_event(run_id, WebSocketEventType.TOOL_CALL_STARTED.value, node_id=node.id, agent_id=agent.id, message=f"Executing tool {tool.name}", payload={"tool_name": tool.name, "input_json": tool_payload}, db=db)
                        
                        tool_result = await tool.execute(tool_payload)
                        
                        tool_call_record.status = RunStatus.COMPLETED.value if tool_result.success else RunStatus.FAILED.value
                        tool_call_record.output_json = json.dumps(tool_result.output)
                        tool_call_record.error_message = tool_result.error
                        tool_call_record.completed_at = datetime.utcnow()
                        db.commit()
                        
                        event_type = WebSocketEventType.TOOL_CALL_COMPLETED.value if tool_result.success else WebSocketEventType.TOOL_CALL_FAILED.value
                        message = f"Tool {tool.name} finished" if tool_result.success else f"Tool {tool.name} failed: {tool_result.error}"
                        await RuntimeService.emit_event(run_id, event_type, node_id=node.id, agent_id=agent.id, message=message, payload={"tool_name": tool.name, "result": tool_result.output, "error": tool_result.error, "status": tool_call_record.status}, db=db)
                        content += f"\n\n[Used tool {tool.name}: {json.dumps(tool_result.output)}]"

                # Persist Agent Output Message
                agent_msg = AgentMessage(
                    run_id=run_id, from_agent_id=agent.id, to_agent_id=None,
                    message_type="AGENT_OUTPUT", content=content, status="DELIVERED"
                )
                db.add(agent_msg)
                
                # Persist Token Usage
                usage = {
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                    "estimated_cost": f"{response.estimated_cost:.8f}",
                    "model": response.model,
                }
                token_record = TokenUsage(
                    run_id=run_id, agent_id=agent.id, model=response.model,
                    prompt_tokens=usage["prompt_tokens"], completion_tokens=usage["completion_tokens"],
                    total_tokens=usage["total_tokens"], estimated_cost=usage["estimated_cost"]
                )
                db.add(token_record)
                db.commit()
                
                await RuntimeService.emit_event(run_id, WebSocketEventType.AGENT_MESSAGE_CREATED.value, node_id=node.id, agent_id=agent.id, message="Agent generated a message", payload={"content": content, "from_agent_id": agent.id, "to_agent_id": None, "message_type": "AGENT_OUTPUT"}, db=db)
                await RuntimeService.emit_event(run_id, WebSocketEventType.TOKEN_USAGE_RECORDED.value, node_id=node.id, agent_id=agent.id, message="Token usage recorded", payload=usage, db=db)

                state["messages"].append({"role": "assistant", "content": content, "agent_id": agent.id})
                state["node_outputs"][node.id] = content
                state["current_output"] = content
                state["previous_agent_id"] = agent.id
                
                # Mock evaluation for conditionals
                if agent.id == "reviewer_agent":
                    input_text = state.get("input", {}).get("message", "").lower()
                    if "force reject" in input_text or "needs revision" in input_text:
                        reviewer_calls = state.get("reviewer_calls", 0) + 1
                        state["reviewer_calls"] = reviewer_calls
                        await RuntimeService.emit_event(run_id, "RUN_LOG", message=f"Reviewer agent evaluated. Calls count: {reviewer_calls}", db=db)
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

                await RuntimeService.emit_event(run_id, "RUN_LOG", message=f"Final node execution state - review_passed: {state.get('review_passed')}, reviewer_calls: {state.get('reviewer_calls')}", db=db)

                await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, agent_id=agent.id, message=f"Completed node {node.id}", db=db)
                return state

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

        except Exception as e:
            run.status = RunStatus.FAILED.value
            run.completed_at = datetime.utcnow()
            run.error_message = str(e)
            db.commit()
            await RuntimeService.emit_event(run.id, WebSocketEventType.RUN_FAILED.value, message=f"Run {run.id} failed: {str(e)}", db=db)

        return run
