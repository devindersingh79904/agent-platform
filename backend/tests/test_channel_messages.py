import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.db.session import SessionLocal
from app.models.models import ChannelMessage, WorkflowRun
from app.channels.telegram_worker import process_telegram_update

def test_channel_messages_list(client: TestClient, db):
    msg = ChannelMessage(
        id=str(uuid.uuid4()),
        channel_type="TELEGRAM",
        external_message_id="123",
        external_user_id="user1",
        direction="INBOUND",
        status="RECEIVED",
        payload_json="{}"
    )
    db.add(msg)
    db.commit()

    res = client.get("/api/channel-messages")
    assert res.status_code == 200
    assert len(res.json()["data"]["content"]) >= 1

def test_run_channel_messages_list(client: TestClient, db):
    run_id = str(uuid.uuid4())
    wf_run = WorkflowRun(
        id=run_id, 
        workflow_id="test", 
        status="RUNNING", 
        input_json="{}"
    )
    db.add(wf_run)
    
    msg = ChannelMessage(
        id=str(uuid.uuid4()),
        channel_type="TELEGRAM",
        external_message_id="456",
        external_user_id="user2",
        run_id=run_id,
        direction="OUTBOUND",
        status="SENT",
        payload_json="{}"
    )
    db.add(msg)
    db.commit()

    res = client.get(f"/api/runs/{run_id}/channel-messages")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["external_message_id"] == "456"

@pytest.mark.asyncio
async def test_telegram_duplicate_update_ignored_by_handler(db, monkeypatch):
    monkeypatch.setenv("DEFAULT_TELEGRAM_WORKFLOW_ID", "dummy_wf")
    
    # Create the workflow in DB so validation passes
    from app.models.models import Workflow
    db.add(Workflow(id="dummy_wf", name="Dummy Workflow"))
    db.commit()
    
    # Track execute_run calls
    execute_calls = []
    
    class DummyRun:
        status = "COMPLETED"
        output_json = '{"final_message": "done"}'
        
    async def fake_execute_run(*args, **kwargs):
        execute_calls.append(True)
        return DummyRun()
        
    monkeypatch.setattr("app.channels.telegram_worker.RuntimeService.execute_run", fake_execute_run)

    update_payload = {
        "update_id": 999,
        "message": {
            "message_id": 888,
            "from": {"id": 777}
        }
    }
    
    # Act
    res1 = await process_telegram_update(update_payload, db, "chat1", "hello")
    res2 = await process_telegram_update(update_payload, db, "chat1", "hello")

    # Assert
    assert res1 == "done"
    assert res2 == "DUPLICATE"
    
    assert len(execute_calls) == 1
    
    inbound = db.query(ChannelMessage).filter(
        ChannelMessage.external_message_id == "TG-999",
        ChannelMessage.direction == "INBOUND"
    ).all()

    assert len(inbound) == 1


@pytest.mark.asyncio
async def test_telegram_valid_message_creates_run_correctly(db, monkeypatch):
    monkeypatch.setenv("DEFAULT_TELEGRAM_WORKFLOW_ID", "valid_wf")
    
    from app.models.models import Workflow
    db.add(Workflow(id="valid_wf", name="Valid Workflow"))
    db.commit()
    
    class DummyRun:
        status = "COMPLETED"
        output_json = '{"final_message": "workflow response output"}'
        
    async def fake_execute_run(*args, **kwargs):
        return DummyRun()
        
    monkeypatch.setattr("app.channels.telegram_worker.RuntimeService.execute_run", fake_execute_run)

    update_payload = {
        "update_id": 1001,
        "message": {
            "message_id": 2001,
            "from": {"id": 3001}
        }
    }
    
    # Act
    res = await process_telegram_update(update_payload, db, "chat1001", "hello valid")
    
    # Assert
    assert res == "workflow response output"
    
    # Verify channel message exists
    msg = db.query(ChannelMessage).filter(ChannelMessage.external_message_id == "TG-1001").first()
    assert msg is not None
    assert msg.run_id is not None
    
    # Verify workflow run exists and links to message
    run = db.query(WorkflowRun).filter(WorkflowRun.id == msg.run_id).first()
    assert run is not None
    assert run.workflow_id == "valid_wf"
    assert run.source == "telegram"


@pytest.mark.asyncio
async def test_telegram_invalid_workflow_does_not_create_run(db, monkeypatch):
    monkeypatch.setenv("DEFAULT_TELEGRAM_WORKFLOW_ID", "nonexistent_wf")
    
    update_payload = {
        "update_id": 1002,
        "message": {
            "message_id": 2002,
            "from": {"id": 3002}
        }
    }
    
    # Act
    res = await process_telegram_update(update_payload, db, "chat1002", "hello invalid")
    
    # Assert
    assert "Telegram workflow is not configured correctly" in res
    
    # Verify channel message exists but has run_id = None
    msg = db.query(ChannelMessage).filter(ChannelMessage.external_message_id == "TG-1002").first()
    assert msg is not None
    assert msg.run_id is None
    
    # Verify no runs exist for nonexistent_wf
    runs_count = db.query(WorkflowRun).filter(WorkflowRun.workflow_id == "nonexistent_wf").count()
    assert runs_count == 0


@pytest.mark.asyncio
async def test_telegram_run_execution_failure_marks_run_failed(db, monkeypatch):
    monkeypatch.setenv("DEFAULT_TELEGRAM_WORKFLOW_ID", "error_wf")
    
    from app.models.models import Workflow
    db.add(Workflow(id="error_wf", name="Error Workflow"))
    db.commit()
    
    async def fake_execute_run(*args, **kwargs):
        raise RuntimeError("Something failed catastrophically in runtime engine")
        
    monkeypatch.setattr("app.channels.telegram_worker.RuntimeService.execute_run", fake_execute_run)

    update_payload = {
        "update_id": 1003,
        "message": {
            "message_id": 2003,
            "from": {"id": 3003}
        }
    }
    
    # Act
    res = await process_telegram_update(update_payload, db, "chat1003", "trigger error")
    
    # Assert
    assert "An error occurred during workflow execution." in res
    
    # Verify channel message has a run_id linked
    msg = db.query(ChannelMessage).filter(ChannelMessage.external_message_id == "TG-1003").first()
    assert msg is not None
    assert msg.run_id is not None
    
    # Verify workflow run exists and is marked as FAILED with error message
    run = db.query(WorkflowRun).filter(WorkflowRun.id == msg.run_id).first()
    assert run is not None
    assert run.status == "FAILED"
    assert "Something failed catastrophically" in run.error_message
