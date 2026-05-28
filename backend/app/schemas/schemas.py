from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.core.constants import EdgeCondition

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    role: str
    system_prompt: str
    model: str
    tools_json: str = "[]"
    memory_enabled: bool = False
    guardrails_json: str = "{}"
    schedule_config_json: str = "{}"
    channel_config_json: str = "{}"
    limits_json: str = "{}"

class AgentCreate(AgentBase):
    pass

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools_json: Optional[str] = None
    memory_enabled: Optional[bool] = None
    guardrails_json: Optional[str] = None
    schedule_config_json: Optional[str] = None
    channel_config_json: Optional[str] = None
    limits_json: Optional[str] = None

class AgentRead(AgentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowRead(WorkflowBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowNodeBase(BaseModel):
    workflow_id: str
    node_type: str
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    config_json: str = "{}"
    position_x: int = 0
    position_y: int = 0

class WorkflowNodeCreate(WorkflowNodeBase):
    id: Optional[str] = None

class WorkflowNodeRead(WorkflowNodeBase):
    id: str

    class Config:
        from_attributes = True

class WorkflowEdgeBase(BaseModel):
    workflow_id: str
    source_node_id: str
    target_node_id: str
    condition_type: str = EdgeCondition.ALWAYS.value
    condition_expression: Optional[str] = None

class WorkflowEdgeCreate(WorkflowEdgeBase):
    id: Optional[str] = None

class WorkflowEdgeRead(WorkflowEdgeBase):
    id: str

    class Config:
        from_attributes = True

class WorkflowGraphSave(BaseModel):
    nodes: List[WorkflowNodeCreate]
    edges: List[WorkflowEdgeCreate]

class WorkflowRunBase(BaseModel):
    workflow_id: str
    input_json: str = "{}"
    idempotency_key: Optional[str] = None
    source: Optional[str] = None
    resumed_from_run_id: Optional[str] = None

class WorkflowRunCreate(WorkflowRunBase):
    pass

class WorkflowRunRead(WorkflowRunBase):
    id: str
    status: str
    output_json: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class NodeRunRead(BaseModel):
    id: str
    workflow_run_id: str
    workflow_id: str
    node_id: str
    node_type: str
    agent_id: Optional[str] = None
    tool_name: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int
    input_json: str
    output_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChannelMessageRead(BaseModel):
    id: str
    channel_type: str
    external_message_id: str
    external_user_id: str
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    direction: str
    status: str
    payload_json: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AgentMessageRead(BaseModel):
    id: str
    run_id: str
    from_agent_id: Optional[str] = None
    to_agent_id: Optional[str] = None
    message_type: str
    content: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class RunLogRead(BaseModel):
    id: str
    run_id: str
    level: str
    event_type: str
    message: str
    metadata_json: str
    created_at: datetime

    class Config:
        from_attributes = True

class ToolCallRead(BaseModel):
    id: str
    run_id: str
    agent_id: Optional[str] = None
    tool_name: str
    input_json: str
    output_json: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class TokenUsageRead(BaseModel):
    id: str
    run_id: str
    agent_id: Optional[str] = None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: str
    created_at: datetime

    class Config:
        from_attributes = True

class AgentMemoryBase(BaseModel):
    memory_type: str
    content: str
    metadata_json: str = "{}"
    source: Optional[str] = None

class AgentMemoryCreate(AgentMemoryBase):
    pass

class AgentMemoryUpdate(BaseModel):
    memory_type: Optional[str] = None
    content: Optional[str] = None
    metadata_json: Optional[str] = None
    source: Optional[str] = None

class AgentMemoryRead(AgentMemoryBase):
    id: str
    agent_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ScheduledJobBase(BaseModel):
    name: str
    agent_id: Optional[str] = None
    workflow_id: str
    cron_expression: str
    enabled: bool = True
    misfire_policy: str = "SKIP"

class ScheduledJobCreate(ScheduledJobBase):
    pass

class ScheduledJobUpdate(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[str] = None
    workflow_id: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    misfire_policy: Optional[str] = None

class ScheduledJobRead(ScheduledJobBase):
    id: str
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
