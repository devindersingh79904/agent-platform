from sqlalchemy.orm import Session
from app.models.models import Agent
from app.schemas.schemas import AgentCreate, AgentUpdate
import json

class AgentService:
    @staticmethod
    def get_agent(db: Session, agent_id: str):
        return db.query(Agent).filter(Agent.id == agent_id).first()

    @staticmethod
    def list_agents(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Agent).offset(skip).limit(limit).all()

    @staticmethod
    def create_agent(db: Session, agent: AgentCreate):
        db_agent = Agent(**agent.model_dump())
        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)
        return db_agent

    @staticmethod
    def update_agent(db: Session, agent_id: str, agent: AgentUpdate):
        db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not db_agent:
            return None
        
        update_data = agent.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_agent, key, value)
            
        db.commit()
        db.refresh(db_agent)
        return db_agent

    @staticmethod
    def delete_agent(db: Session, agent_id: str):
        db_agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if db_agent:
            db.delete(db_agent)
            db.commit()
            return True
        return False
