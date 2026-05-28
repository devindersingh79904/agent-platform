from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.core.messages import ResponseMessage, ErrorMessage
from app.db.session import get_db
from app.schemas.schemas import AgentCreate, AgentUpdate
from app.services.agent_service import AgentService
from app.models.models import Agent
from app.utils.response_builder import paginated_response, success_response

router = APIRouter()

@router.post("")
def create_agent(agent: AgentCreate, request: Request, db: Session = Depends(get_db)):
    return success_response(request, ResponseMessage.AGENT_CREATED, AgentService.create_agent(db, agent))

@router.get("")
def get_agents(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Agent)
    total = query.count()
    agents = query.offset((page - 1) * size).limit(size).all()
    return paginated_response(request, ResponseMessage.AGENTS_FETCHED, agents, page, size, total)

@router.get("/{agent_id}")
def get_agent(agent_id: str, request: Request, db: Session = Depends(get_db)):
    db_agent = AgentService.get_agent(db, agent_id)
    if db_agent is None:
        raise NotFoundException(ErrorMessage.AGENT_NOT_FOUND)
    return success_response(request, ResponseMessage.AGENT_FETCHED, db_agent)

@router.put("/{agent_id}")
def update_agent(agent_id: str, agent: AgentUpdate, request: Request, db: Session = Depends(get_db)):
    db_agent = AgentService.update_agent(db, agent_id, agent)
    if db_agent is None:
        raise NotFoundException(ErrorMessage.AGENT_NOT_FOUND)
    return success_response(request, ResponseMessage.AGENT_UPDATED, db_agent)

@router.delete("/{agent_id}")
def delete_agent(agent_id: str, request: Request, db: Session = Depends(get_db)):
    success = AgentService.delete_agent(db, agent_id)
    if not success:
        raise NotFoundException(ErrorMessage.AGENT_NOT_FOUND)
    return success_response(request, ResponseMessage.AGENT_DELETED, {"status": "ok"})
