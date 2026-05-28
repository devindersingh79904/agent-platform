from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.constants import EdgeCondition, RunStatus
from app.db.session import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    role = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    model = Column(String, nullable=False)
    tools_json = Column(Text, nullable=False, default="[]")
    memory_enabled = Column(Boolean, default=False)
    guardrails_json = Column(Text, nullable=False, default="{}")
    schedule_config_json = Column(Text, nullable=False, default="{}")
    channel_config_json = Column(Text, nullable=False, default="{}")
    limits_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    node_type = Column(String, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    tool_name = Column(String, nullable=True)
    config_json = Column(Text, nullable=False, default="{}")
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    source_node_id = Column(String, ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False)
    target_node_id = Column(String, ForeignKey("workflow_nodes.id", ondelete="CASCADE"), nullable=False)
    condition_type = Column(String, nullable=False, default=EdgeCondition.ALWAYS.value)
    condition_expression = Column(Text, nullable=True)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    status = Column(String, nullable=False, default=RunStatus.QUEUED.value)
    input_json = Column(Text, nullable=False, default="{}")
    output_json = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    from_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    to_agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="DELIVERED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    event_sequence = Column(Integer, nullable=True)
    level = Column(String, nullable=False, default="INFO")
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    tool_name = Column(String, nullable=False)
    input_json = Column(Text, nullable=False, default="{}")
    output_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="STARTED")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)


class TokenUsage(Base):
    __tablename__ = "token_usages"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(String, default="0.0")  # Stored as string to avoid floating point issues easily
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Memory(Base):
    __tablename__ = "memories"

    id = Column(String, primary_key=True, default=generate_uuid)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, nullable=True)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
