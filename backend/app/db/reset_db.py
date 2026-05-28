from app.db.session import SessionLocal, Base, engine
from app.db.seed import reset_and_seed
from app.models.models import Agent, Workflow
from app.api.templates import TEMPLATES

def main():
    # Recreate tables to ensure clean DB schemas
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        reset_and_seed(db)
        
        agent_count = db.query(Agent).count()
        workflow_count = db.query(Workflow).count()
        
        print("Database reset complete.")
        print(f"Seeded agents: {agent_count}")
        print(f"Templates available: {len(TEMPLATES)}")
        print(f"Seeded demo workflows: {workflow_count}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
