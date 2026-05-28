from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.messages import ResponseMessage
from app.models.models import ScheduledJob
from app.schemas.schemas import ScheduledJobCreate, ScheduledJobRead, ScheduledJobUpdate
from app.utils.response_builder import paginated_response, success_response
from app.core.exceptions import NotFoundException
import uuid

router = APIRouter()

@router.get("")
def get_scheduled_jobs(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(ScheduledJob).order_by(ScheduledJob.created_at.desc())
    total = query.count()
    jobs = query.offset((page - 1) * size).limit(size).all()
    return paginated_response(request, ResponseMessage.SCHEDULES_FETCHED, jobs, page, size, total)

@router.post("")
def create_scheduled_job(job: ScheduledJobCreate, request: Request, db: Session = Depends(get_db)):
    job_id = str(uuid.uuid4())
    new_job = ScheduledJob(id=job_id, **job.model_dump())
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    from app.scheduler.scheduler_worker import sync_jobs
    sync_jobs()
    
    return success_response(request, ResponseMessage.SCHEDULE_CREATED, new_job)

@router.get("/{job_id}")
def get_scheduled_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise NotFoundException("Scheduled job not found")
    return success_response(request, ResponseMessage.SCHEDULE_FETCHED, job)

@router.put("/{job_id}")
def update_scheduled_job(job_id: str, job_update: ScheduledJobUpdate, request: Request, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise NotFoundException("Scheduled job not found")
        
    for key, value in job_update.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
        
    db.commit()
    db.refresh(job)
    
    from app.scheduler.scheduler_worker import sync_jobs
    sync_jobs()
    
    return success_response(request, ResponseMessage.SCHEDULE_UPDATED, job)

@router.delete("/{job_id}")
def delete_scheduled_job(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise NotFoundException("Scheduled job not found")
        
    db.delete(job)
    db.commit()
    
    from app.scheduler.scheduler_worker import sync_jobs
    sync_jobs()
    
    return success_response(request, ResponseMessage.SCHEDULE_DELETED, {"id": job_id})

@router.post("/{job_id}/trigger")
def trigger_scheduled_job(job_id: str, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
    if not job:
        raise NotFoundException("Scheduled job not found")
        
    import uuid
    import json
    from datetime import datetime
    from app.models.models import WorkflowRun
    from app.core.constants import RunStatus
    from app.api.runs import execute_run_task
    
    run_id = str(uuid.uuid4())
    input_data = {"source": "schedule_trigger", "job_id": job_id, "correlation_id": f"SCHED-{job_id}-{int(datetime.utcnow().timestamp())}"}
    
    new_run = WorkflowRun(
        id=run_id, 
        workflow_id=job.workflow_id, 
        input_json=json.dumps(input_data), 
        status=RunStatus.QUEUED.value, 
        started_at=datetime.utcnow(),
        source="SCHEDULE"
    )
    db.add(new_run)
    
    job.last_run_id = run_id
    job.last_run_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_run)
    db.refresh(job)
    
    background_tasks.add_task(execute_run_task, run_id, job.workflow_id, input_data)
    
    return success_response(request, ResponseMessage.SCHEDULE_TRIGGERED, {"run_id": run_id})
