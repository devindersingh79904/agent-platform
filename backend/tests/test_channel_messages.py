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
