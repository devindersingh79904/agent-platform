from app.core.constants import EdgeCondition, NodeType
from app.db.session import SessionLocal, Base, engine
from app.models.models import Agent, Workflow, WorkflowNode, WorkflowEdge, WorkflowRun, AgentMessage, RunLog, ToolCall, TokenUsage
from sqlalchemy.orm import Session
import json

Base.metadata.create_all(bind=engine)

# Definitions of default 8 agents
DEFAULT_AGENTS = [
    {
        "id": "coord_agent",
        "name": "Coordinator Agent",
        "description": "Orchestrates user inputs and routes tasks to specialized agents.",
        "role": "coordinator",
        "system_prompt": "You are the Coordinator Agent. Route tasks to the correct agent.",
        "model": "gpt-4o-mini",
        "tools_json": "[]",
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["duckduckgo_search_tool", "summarizer", "draft_generator", "knowledge_base_lookup"],
            "blocked_keywords": [],
            "require_review_before_final": True
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "research_agent",
        "name": "Research Agent",
        "description": "Performs web searches and summarizes research material.",
        "role": "researcher",
        "system_prompt": "You are the Research Agent. Use your search and summarizer tools to compile information.",
        "model": "gpt-4o-mini",
        "tools_json": '["duckduckgo_search_tool", "summarizer"]',
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["duckduckgo_search_tool", "summarizer"],
            "blocked_keywords": [],
            "require_review_before_final": False
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "writer_agent",
        "name": "Writer Agent",
        "description": "Drafts clear summaries, reports, and messages.",
        "role": "writer",
        "system_prompt": "You are the Writer Agent. Write a clear summary. If review failed, revise your draft.",
        "model": "gpt-4o-mini",
        "tools_json": '["draft_generator", "summarizer"]',
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["draft_response_tool", "summarizer"],
            "blocked_keywords": [],
            "require_review_before_final": False
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "reviewer_agent",
        "name": "Reviewer Agent",
        "description": "Evaluates draft quality and outputs either approve or reject.",
        "role": "reviewer",
        "system_prompt": "You are the Reviewer Agent. Review the summary. If it covers the requirements, output 'approve'. If it is incomplete or incorrect, output 'reject' with reasons.",
        "model": "gpt-4o-mini",
        "tools_json": '["summarizer"]',
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["summarizer"],
            "blocked_keywords": [],
            "require_review_before_final": False
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "support_agent",
        "name": "Support Agent",
        "description": "Frontline customer support triage agent.",
        "role": "support",
        "system_prompt": "You are the Support Agent. Answer customer queries and look up documentation if needed.",
        "model": "gpt-4o-mini",
        "tools_json": "[]",
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": [],
            "blocked_keywords": [],
            "require_review_before_final": True
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "knowledge_agent",
        "name": "Knowledge Agent",
        "description": "Queries internal knowledge bases for accurate data.",
        "role": "knowledge",
        "system_prompt": "You are the Knowledge Agent. Query internal databases using your lookup tool.",
        "model": "gpt-4o-mini",
        "tools_json": '["knowledge_base_lookup"]',
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["knowledge_base_lookup"],
            "blocked_keywords": [],
            "require_review_before_final": False
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "resolution_agent",
        "name": "Resolution Agent",
        "description": "Drafts the final resolution proposals for support issues.",
        "role": "resolution",
        "system_prompt": "You are the Resolution Agent. Draft the final resolution for customer support.",
        "model": "gpt-4o-mini",
        "tools_json": '["draft_generator"]',
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["draft_response_tool"],
            "blocked_keywords": [],
            "require_review_before_final": False
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    },
    {
        "id": "escalation_agent",
        "name": "Escalation Agent",
        "description": "Prepares and validates escalation notes for human support agent.",
        "role": "escalation",
        "system_prompt": "You are the Escalation Agent. Prepare the escalation notes.",
        "model": "gpt-4o-mini",
        "tools_json": '["draft_generator"]',
        "memory_enabled": True,
        "guardrails_json": json.dumps({
            "allowed_tools": ["draft_response_tool"],
            "blocked_keywords": [],
            "require_review_before_final": False
        }),
        "limits_json": json.dumps({
            "max_iterations": 10,
            "max_tool_calls": 5
        }),
        "schedule_config_json": "{}",
        "channel_config_json": "{}"
    }
]

def seed_missing_defaults(db: Session) -> None:
    # 1. Seed missing agents
    seeded_agents_count = 0
    for a_data in DEFAULT_AGENTS:
        existing = db.query(Agent).filter(Agent.id == a_data["id"]).first()
        if not existing:
            db.add(Agent(**a_data))
            seeded_agents_count += 1
    db.commit()
    
    # 2. Seed default workflows if they do not exist
    # Research -> Write -> Review
    existing_wf1 = db.query(Workflow).filter(Workflow.id == "wf_research_review").first()
    if not existing_wf1:
        wf1 = Workflow(
            id="wf_research_review", 
            name="Research → Write → Review", 
            description="Coordinator routes user input to Research, Writer, and then Reviewer with feedback loops."
        )
        db.add(wf1)
        db.commit()
        
        # Nodes
        n_start = WorkflowNode(id="n1_start", workflow_id=wf1.id, node_type=NodeType.START.value, position_x=100, position_y=150)
        n_coord = WorkflowNode(id="n1_coord", workflow_id=wf1.id, node_type=NodeType.AGENT.value, agent_id="coord_agent", position_x=300, position_y=150)
        n_research = WorkflowNode(id="n1_res", workflow_id=wf1.id, node_type=NodeType.AGENT.value, agent_id="research_agent", position_x=500, position_y=150)
        n_write = WorkflowNode(id="n1_write", workflow_id=wf1.id, node_type=NodeType.AGENT.value, agent_id="writer_agent", position_x=700, position_y=150)
        n_review = WorkflowNode(id="n1_review", workflow_id=wf1.id, node_type=NodeType.AGENT.value, agent_id="reviewer_agent", position_x=900, position_y=150)
        n_cond = WorkflowNode(id="n1_cond", workflow_id=wf1.id, node_type=NodeType.CONDITION.value, position_x=1100, position_y=150)
        n_end = WorkflowNode(id="n1_end", workflow_id=wf1.id, node_type=NodeType.END.value, position_x=1300, position_y=150)
        
        db.add_all([n_start, n_coord, n_research, n_write, n_review, n_cond, n_end])
        db.commit()
        
        # Edges
        edges1 = [
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_start.id, target_node_id=n_coord.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_coord.id, target_node_id=n_research.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_research.id, target_node_id=n_write.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_write.id, target_node_id=n_review.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_review.id, target_node_id=n_cond.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_cond.id, target_node_id=n_end.id, condition_type=EdgeCondition.APPROVED.value),
            WorkflowEdge(workflow_id=wf1.id, source_node_id=n_cond.id, target_node_id=n_write.id, condition_type=EdgeCondition.REJECTED.value)
        ]
        db.add_all(edges1)
        db.commit()

    # Customer Support Triage
    existing_wf2 = db.query(Workflow).filter(Workflow.id == "wf_support_triage").first()
    if not existing_wf2:
        wf2 = Workflow(
            id="wf_support_triage",
            name="Customer Support Triage",
            description="Support Agent -> Knowledge Agent -> Resolution -> Escalation."
        )
        db.add(wf2)
        db.commit()
        
        # Nodes
        n2_start = WorkflowNode(id="n2_start", workflow_id=wf2.id, node_type=NodeType.START.value, position_x=100, position_y=150)
        n2_support = WorkflowNode(id="n2_support", workflow_id=wf2.id, node_type=NodeType.AGENT.value, agent_id="support_agent", position_x=300, position_y=150)
        n2_knowledge = WorkflowNode(id="n2_knowledge", workflow_id=wf2.id, node_type=NodeType.AGENT.value, agent_id="knowledge_agent", position_x=500, position_y=150)
        n2_resolution = WorkflowNode(id="n2_resolution", workflow_id=wf2.id, node_type=NodeType.AGENT.value, agent_id="resolution_agent", position_x=700, position_y=150)
        n2_escalation = WorkflowNode(id="n2_escalation", workflow_id=wf2.id, node_type=NodeType.AGENT.value, agent_id="escalation_agent", position_x=900, position_y=150)
        n2_cond = WorkflowNode(id="n2_cond", workflow_id=wf2.id, node_type=NodeType.CONDITION.value, position_x=1100, position_y=150)
        n2_end = WorkflowNode(id="n2_end", workflow_id=wf2.id, node_type=NodeType.END.value, position_x=1300, position_y=150)
        
        db.add_all([n2_start, n2_support, n2_knowledge, n2_resolution, n2_escalation, n2_cond, n2_end])
        db.commit()
        
        # Edges
        edges2 = [
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_start.id, target_node_id=n2_support.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_support.id, target_node_id=n2_knowledge.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_knowledge.id, target_node_id=n2_resolution.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_resolution.id, target_node_id=n2_escalation.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_escalation.id, target_node_id=n2_cond.id, condition_type=EdgeCondition.ALWAYS.value),
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_cond.id, target_node_id=n2_end.id, condition_type=EdgeCondition.RESOLVED.value),
            WorkflowEdge(workflow_id=wf2.id, source_node_id=n2_cond.id, target_node_id=n2_end.id, condition_type=EdgeCondition.ESCALATE.value)
        ]
        db.add_all(edges2)
        db.commit()

def reset_and_seed(db: Session) -> None:
    # Destructive wipe
    db.query(WorkflowEdge).delete()
    db.query(WorkflowNode).delete()
    db.query(WorkflowRun).delete()
    db.query(AgentMessage).delete()
    db.query(RunLog).delete()
    db.query(ToolCall).delete()
    db.query(TokenUsage).delete()
    db.query(Workflow).delete()
    db.query(Agent).delete()
    db.commit()
    
    # Run the idempotent seed to populate
    seed_missing_defaults(db)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_missing_defaults(db)
        print("Database seeded successfully.")
    finally:
        db.close()
