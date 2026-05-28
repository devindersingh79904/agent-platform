from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.constants import EdgeCondition, NodeType
from app.core.exceptions import NotFoundException
from app.core.messages import ResponseMessage
from app.db.session import get_db
from app.utils.response_builder import success_response
import uuid

router = APIRouter()

TEMPLATES = {
    "tpl_research_write_review": {
        "name": "Research → Write → Review",
        "description": "Coordinator routes to Research, Writer, then Reviewer with feedback loops.",
        "nodes": [
            {"id": "n_start", "type": NodeType.START.value, "agent_id": None, "x": 100, "y": 150},
            {"id": "n_coord", "type": NodeType.AGENT.value, "agent_id": "coord_agent", "x": 300, "y": 150},
            {"id": "n_res", "type": NodeType.AGENT.value, "agent_id": "research_agent", "x": 500, "y": 150},
            {"id": "n_writer", "type": NodeType.AGENT.value, "agent_id": "writer_agent", "x": 700, "y": 150},
            {"id": "n_reviewer", "type": NodeType.AGENT.value, "agent_id": "reviewer_agent", "x": 900, "y": 150},
            {"id": "n_cond", "type": NodeType.CONDITION.value, "agent_id": None, "x": 1100, "y": 150},
            {"id": "n_end", "type": NodeType.END.value, "agent_id": None, "x": 1300, "y": 150}
        ],
        "edges": [
            {"source": "n_start", "target": "n_coord", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_coord", "target": "n_res", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_res", "target": "n_writer", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_writer", "target": "n_reviewer", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_reviewer", "target": "n_cond", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_cond", "target": "n_end", "type": EdgeCondition.APPROVED.value},
            {"source": "n_cond", "target": "n_writer", "type": EdgeCondition.REJECTED.value}
        ]
    },
    "tpl_customer_support_triage": {
        "name": "Customer Support Triage",
        "description": "Support Agent -> Knowledge Agent -> Resolution -> Escalation.",
        "nodes": [
            {"id": "n_start", "type": NodeType.START.value, "agent_id": None, "x": 100, "y": 150},
            {"id": "n_support", "type": NodeType.AGENT.value, "agent_id": "support_agent", "x": 300, "y": 150},
            {"id": "n_knowledge", "type": NodeType.AGENT.value, "agent_id": "knowledge_agent", "x": 500, "y": 150},
            {"id": "n_resolution", "type": NodeType.AGENT.value, "agent_id": "resolution_agent", "x": 700, "y": 150},
            {"id": "n_escalation", "type": NodeType.AGENT.value, "agent_id": "escalation_agent", "x": 900, "y": 150},
            {"id": "n_cond", "type": NodeType.CONDITION.value, "agent_id": None, "x": 1100, "y": 150},
            {"id": "n_end", "type": NodeType.END.value, "agent_id": None, "x": 1300, "y": 150}
        ],
        "edges": [
            {"source": "n_start", "target": "n_support", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_support", "target": "n_knowledge", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_knowledge", "target": "n_resolution", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_resolution", "target": "n_escalation", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_escalation", "target": "n_cond", "type": EdgeCondition.ALWAYS.value},
            {"source": "n_cond", "target": "n_end", "type": EdgeCondition.RESOLVED.value},
            {"source": "n_cond", "target": "n_end", "type": EdgeCondition.ESCALATE.value}
        ]
    }
}

@router.get("")
def get_templates(request: Request):
    templates = [
        {
            "id": k, 
            "name": v["name"], 
            "description": v["description"],
            "nodes_count": len(v["nodes"]),
            "edges_count": len(v["edges"])
        } for k, v in TEMPLATES.items()
    ]
    return success_response(request, ResponseMessage.TEMPLATES_FETCHED, templates)

@router.post("/{template_id}/create-workflow")
def create_workflow_from_template(template_id: str, request: Request, db: Session = Depends(get_db)):
    from app.models.models import Workflow, WorkflowNode, WorkflowEdge
    
    template = TEMPLATES.get(template_id)
    if not template:
        raise NotFoundException("Template not found")
        
    new_wf_id = str(uuid.uuid4())
    new_wf = Workflow(id=new_wf_id, name=template["name"], description=template["description"])
    db.add(new_wf)
    
    old_to_new_nodes = {}
    for n in template["nodes"]:
        new_node_id = str(uuid.uuid4())
        old_to_new_nodes[n["id"]] = new_node_id
        db.add(WorkflowNode(
            id=new_node_id, workflow_id=new_wf_id, node_type=n["type"],
            agent_id=n["agent_id"], position_x=n["x"], position_y=n["y"]
        ))
        
    for e in template["edges"]:
        db.add(WorkflowEdge(
            id=str(uuid.uuid4()), workflow_id=new_wf_id,
            source_node_id=old_to_new_nodes[e["source"]],
            target_node_id=old_to_new_nodes[e["target"]],
            condition_type=e["type"]
        ))
        
    db.commit()
    return success_response(request, ResponseMessage.WORKFLOW_CREATED, {"workflow_id": new_wf_id, "name": new_wf.name})
