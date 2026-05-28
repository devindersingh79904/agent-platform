import pytest
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import WorkflowRun, ScheduledJob

def test_schedule_crud(client: TestClient):
    # Workflow
    wf_res = client.post("/api/workflows", json={"name": "Sch_WF", "description": "d"})
    assert wf_res.status_code == 200
    wf_id = wf_res.json()["data"]["id"]

    # Create schedule
    res = client.post("/api/schedules", json={
        "name": "Test Schedule",
        "workflow_id": wf_id,
        "cron_expression": "* * * * *",
        "enabled": True
    })
    assert res.status_code == 200
    sch_id = res.json()["data"]["id"]

    # Read
    get_res = client.get("/api/schedules")
    assert get_res.status_code == 200
    assert len(get_res.json()["data"]["content"]) >= 1

    # Delete
    del_res = client.delete(f"/api/schedules/{sch_id}")
    assert del_res.status_code == 200

def test_schedule_manual_trigger_creates_real_run(client: TestClient, db):
    wf_res = client.post("/api/workflows", json={"name": "Sch_WF_2", "description": "d"})
    wf_id = wf_res.json()["data"]["id"]

    res = client.post("/api/schedules", json={
        "name": "Test Trigger Schedule",
        "workflow_id": wf_id,
        "cron_expression": "* * * * *",
        "enabled": True
    })
    sch_id = res.json()["data"]["id"]

    # Trigger
    trig_res = client.post(f"/api/schedules/{sch_id}/trigger")
    assert trig_res.status_code == 200
    run_id = trig_res.json()["data"]["run_id"]
    assert run_id is not None
    
    # Assert WorkflowRun exists with source=SCHEDULE
    wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    assert wf_run is not None
    assert wf_run.source == "SCHEDULE"
    
    # Assert ScheduledJob updated
    job = db.query(ScheduledJob).filter(ScheduledJob.id == sch_id).first()
    assert job.last_run_id == run_id
    assert job.last_run_at is not None
