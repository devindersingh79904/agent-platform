from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundException
from app.core.messages import ResponseMessage, ErrorMessage
from app.db.session import get_db
from app.schemas.schemas import AgentCreate, AgentUpdate, AgentMemoryCreate, AgentMemoryUpdate
from app.services.agent_service import AgentService
from app.models.models import Agent, AgentMemory
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


@router.get("/{agent_id}/memories")
def get_agent_memories(agent_id: str, request: Request, db: Session = Depends(get_db)):
    if not AgentService.get_agent(db, agent_id):
        raise NotFoundException(ErrorMessage.AGENT_NOT_FOUND)
        
    memories = db.query(AgentMemory).filter(
        AgentMemory.agent_id == agent_id,
        AgentMemory.deleted_at == None
    ).order_by(AgentMemory.created_at.desc()).all()
    
    return success_response(request, ResponseMessage.MEMORIES_FETCHED, memories)

@router.post("/{agent_id}/memories")
def create_agent_memory(agent_id: str, memory: AgentMemoryCreate, request: Request, db: Session = Depends(get_db)):
    if not AgentService.get_agent(db, agent_id):
        raise NotFoundException(ErrorMessage.AGENT_NOT_FOUND)
        
    import uuid
    new_memory = AgentMemory(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        memory_type=memory.memory_type,
        content=memory.content,
        metadata_json=memory.metadata_json,
        source=memory.source
    )
    db.add(new_memory)
    db.commit()
    db.refresh(new_memory)
    return success_response(request, ResponseMessage.MEMORY_CREATED, new_memory)

@router.put("/{agent_id}/memories/{memory_id}")
def update_agent_memory(agent_id: str, memory_id: str, memory: AgentMemoryUpdate, request: Request, db: Session = Depends(get_db)):
    db_memory = db.query(AgentMemory).filter(
        AgentMemory.id == memory_id,
        AgentMemory.agent_id == agent_id,
        AgentMemory.deleted_at == None
    ).first()
    
    if not db_memory:
        raise NotFoundException("Memory not found")
        
    update_data = memory.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_memory, key, value)
        
    db.commit()
    db.refresh(db_memory)
    return success_response(request, ResponseMessage.MEMORY_UPDATED, db_memory)

@router.delete("/{agent_id}/memories/{memory_id}")
def delete_agent_memory(agent_id: str, memory_id: str, request: Request, db: Session = Depends(get_db)):
    db_memory = db.query(AgentMemory).filter(
        AgentMemory.id == memory_id,
        AgentMemory.agent_id == agent_id,
        AgentMemory.deleted_at == None
    ).first()
    
    if not db_memory:
        raise NotFoundException("Memory not found")
        
    from datetime import datetime
    db_memory.deleted_at = datetime.utcnow()
    db.commit()
    return success_response(request, ResponseMessage.MEMORY_DELETED, {"status": "ok"})
