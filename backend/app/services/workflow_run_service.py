from datetime import datetime
import json
import uuid
from sqlalchemy.orm import Session
from app.models.models import WorkflowRun, Workflow
from app.core.constants import RunStatus
from app.runtime.engine import normalize_run_input
from app.core.logger import get_logger

logger = get_logger(__name__)

class WorkflowRunService:
    @staticmethod
    def create_run(
        db: Session,
        workflow_id: str,
        input_data: dict,
        trigger_source: str = "api",
        commit: bool = True
    ) -> WorkflowRun:
        # Validate that the workflow exists
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow with ID {workflow_id} does not exist")
            
        normalized = normalize_run_input(input_data)
        run_id = str(uuid.uuid4())
        
        new_run = WorkflowRun(
            id=run_id,
            workflow_id=workflow.id,
            input_json=json.dumps(normalized),
            status=RunStatus.QUEUED.value,
            started_at=datetime.utcnow(),
            source=trigger_source
        )
        db.add(new_run)
        if commit:
            db.commit()
            db.refresh(new_run)
        return new_run
