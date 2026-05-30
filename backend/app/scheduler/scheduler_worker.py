import os
import asyncio
import logging
import threading
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import ScheduledJob, WorkflowRun
from app.runtime.engine import RuntimeService
from app.core.constants import RunStatus
from datetime import datetime
import uuid
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_scheduler_started = False
_scheduler_lock = threading.Lock()

async def execute_scheduled_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        if not job or not job.enabled:
            return

        run_id = str(uuid.uuid4())
        correlation_id = f"SCHED-{job_id}-{int(datetime.utcnow().timestamp())}"
        input_data = {"source": "schedule", "job_id": job_id, "correlation_id": correlation_id}
        
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
        
        logger.info(f"Executing scheduled job {job_id} (run {run_id})")
        await RuntimeService.execute_run(db, run_id, job.workflow_id, input_data)
        
    except Exception as e:
        logger.error(f"Error executing scheduled job {job_id}: {e}")
    finally:
        db.close()

def sync_jobs():
    if not scheduler.running:
        return
        
    db = SessionLocal()
    try:
        # Remove all existing jobs from the scheduler
        scheduler.remove_all_jobs()
        
        # Add enabled jobs
        jobs = db.query(ScheduledJob).filter(ScheduledJob.enabled == True).all()
        for job in jobs:
            scheduler.add_job(
                execute_scheduled_job,
                CronTrigger.from_crontab(job.cron_expression),
                id=job.id,
                args=[job.id],
                replace_existing=True,
                misfire_grace_time=3600 if job.misfire_policy == "RUN_ONCE" else None
            )
            
            # Update next_run_at in DB based on newly added job trigger
            aps_job = scheduler.get_job(job.id)
            if aps_job and aps_job.next_run_time:
                job.next_run_at = aps_job.next_run_time
        
        db.commit()
    except Exception as e:
        logger.error(f"Error syncing jobs: {e}")
    finally:
        db.close()

def start_scheduler():
    global _scheduler_started
    
    with _scheduler_lock:
        if _scheduler_started and scheduler.running:
            logger.info("Scheduler already running, skipping startup")
            return
            
        scheduler.start()
        sync_jobs()
        _scheduler_started = True
        logger.info("Scheduler started")

if __name__ == "__main__":
    logger.info("Starting scheduler worker...")
    start_scheduler()
    
    # Run forever
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
