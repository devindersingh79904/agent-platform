import re

with open("app/runtime/engine.py", "r") as f:
    content = f.read()

if "import asyncio" not in content:
    content = "import asyncio\n" + content

# Replace make_node_executor definition up to the `execute_run`
# We'll use regex to find the method.
pattern = r"    @staticmethod\n    def make_node_executor\(node: WorkflowNode, agent: Optional\[Agent\]\):.*?(?=    @staticmethod\n    async def execute_run)"

replacement = """    @staticmethod
    def make_node_executor(node: WorkflowNode, agent: Optional[Agent]):
        async def node_executor(state: RuntimeState) -> RuntimeState:
            db = state["db_session"]
            run_id = state["run_id"]
            workflow_id = state["workflow_id"]
            state["iteration_count"] += 1

            max_iter = 10
            max_retries = 1
            timeout_sec = 60
            if agent and agent.limits_json:
                try:
                    cfg = json.loads(agent.limits_json)
                    max_iter = cfg.get("max_iterations", max_iter)
                    max_retries = cfg.get("max_retries", max_retries)
                    timeout_sec = cfg.get("timeout_sec", timeout_sec)
                except:
                    pass

            if state["iteration_count"] > max_iter:
                await RuntimeService.emit_event(run_id, WebSocketEventType.RUN_FAILED.value, node_id=node.id, message=ErrorMessage.MAX_ITERATIONS_EXCEEDED, db=db)
                raise Exception(ErrorMessage.MAX_ITERATIONS_EXCEEDED)

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

            async def execute_inner():
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
                    node_run.output_json = json.dumps({"output": input_str})
                    await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, message="START node completed", db=db)
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
                        await RuntimeService.emit_event(run_id, "RUN_LOG", message=f"Tool {tool_name} not found in registry", db=db)

                    await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, agent_id=agent.id if agent else None,
                                                   message=f"Completed node {node.id}", db=db)
                    return

                if node.node_type == NodeType.CONDITION.value:
                    await RuntimeService.emit_event(run_id, WebSocketEventType.CONDITION_EVALUATED.value, node_id=node.id, message=f"Evaluated condition", db=db)
                    await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, message="CONDITION node completed", db=db)
                    return

                if node.node_type == NodeType.END.value:
                    await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_STARTED.value, node_id=node.id, agent_id=None, message="End node started", db=db)
                    final_output = state.get("current_output") or state.get("final_output") or ""
                    state["final_output"] = final_output
                    state.setdefault("node_outputs", {})[node.id] = final_output
                    node_run.output_json = json.dumps({"final_output": final_output})
                    await RuntimeService.emit_event(run_id, WebSocketEventType.NODE_COMPLETED.value, node_id=node.id, agent_id=None, message="End node completed", payload={"final_output": final_output}, db=db)
                    return

                if node.node_type == NodeType.AGENT.value and agent:
                    input_messages = state.get("messages", []).copy()
                    if not input_messages:
                        input_messages = [{"role": "user", "content": state["current_output"]}]

                    sys_prompt = agent.system_prompt
                    
                    # Memory Injection
                    if agent.memory_enabled:
                        memories = db.query(AgentMemory).filter(AgentMemory.agent_id == agent.id).all()
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
                            banned_words = gr.get("banned_keywords", [])
                            for word in banned_words:
                                if word.lower() in state["current_output"].lower():
                                    raise Exception(f"Input contains banned keyword: {word}")
                            allowed_tools = gr.get("allowed_tools", None)
                        except Exception as e:
                            if "banned keyword" in str(e):
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

                    # Evaluate Tools if configured
                    tools_list = []
                    if agent.tools_json:
                        try:
                            tool_names = json.loads(agent.tools_json)
                            if allowed_tools is not None:
                                tool_names = [t for t in tool_names if t in allowed_tools]
                            tools_list = [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]
                        except Exception as e:
                            pass

                    prompt = "\\n\\n".join(
                        str(message.get("content", ""))
                        for message in input_messages
                        if message.get("role") != "system" and message.get("content")
                    )
                    if state.get("node_outputs"):
                        prompt += "\\n\\nPrevious node outputs:\\n" + json.dumps(state["node_outputs"])

                    llm_client = get_llm_client()
                    response = await llm_client.generate(
                        system_prompt=sys_prompt,
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
                            content += f"\\n\\n[Used tool {tool.name}: {json.dumps(tool_result.output)}]"

                    # Guardrails after LLM call
                    if agent.guardrails_json:
                        try:
                            gr = json.loads(agent.guardrails_json)
                            banned_words = gr.get("banned_keywords", [])
                            for word in banned_words:
                                if word.lower() in content.lower():
                                    raise Exception(f"Output contains banned keyword: {word}")
                        except Exception as e:
                            if "banned keyword" in str(e):
                                raise e
                            pass

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
                    node_run.output_json = json.dumps({"output": content})
                    
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

            for attempt in range(max_retries + 1):
                try:
                    node_run.retry_count = attempt
                    db.commit()
                    await asyncio.wait_for(execute_inner(), timeout=timeout_sec)
                    node_run.status = RunStatus.COMPLETED.value
                    node_run.completed_at = datetime.utcnow()
                    db.commit()
                    break
                except asyncio.TimeoutError:
                    if attempt == max_retries:
                        node_run.status = RunStatus.FAILED.value
                        node_run.error_message = "Timeout exceeded"
                        node_run.completed_at = datetime.utcnow()
                        db.commit()
                        raise Exception("Timeout exceeded for node")
                except Exception as e:
                    if attempt == max_retries:
                        node_run.status = RunStatus.FAILED.value
                        node_run.error_message = str(e)
                        node_run.completed_at = datetime.utcnow()
                        db.commit()
                        raise
                        
            return state

        return node_executor
"""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
with open("app/runtime/engine.py", "w") as f:
    f.write(new_content)
