import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from app.db.session import SessionLocal
from app.models.models import RunLog

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, list[tuple[WebSocket, str | None]]] = {}

    async def connect(self, run_id: str, websocket: WebSocket, correlation_id: str | None = None):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append((websocket, correlation_id))

    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.active_connections:
            self.active_connections[run_id] = [
                (conn, corr) for conn, corr in self.active_connections[run_id] if conn is not websocket
            ]
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast_to_run(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            for connection, correlation_id in self.active_connections[run_id]:
                try:
                    event = dict(message)
                    if correlation_id and not event.get("correlation_id"):
                        event["correlation_id"] = correlation_id
                    event.setdefault("task_id", run_id)
                    await connection.send_json(event)
                except Exception:
                    pass

manager = ConnectionManager()

def run_log_to_event(log: RunLog, correlation_id: str | None = None) -> dict:
    payload = {}
    try:
        payload = json.loads(log.metadata_json or "{}")
    except Exception:
        payload = {}

    event_correlation_id = correlation_id or payload.get("correlation_id") or f"BACK-{log.run_id}"
    task_id = payload.get("task_id") or log.run_id

    return {
        "event_id": log.event_sequence,
        "event_type": log.event_type,
        "run_id": log.run_id,
        "task_id": task_id,
        "correlation_id": event_correlation_id,
        "timestamp": log.created_at.isoformat() if log.created_at else None,
        "message": log.message,
        "payload": payload,
    }

def get_missed_events(run_id: str, last_event_id: int, correlation_id: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        logs = (
            db.query(RunLog)
            .filter(RunLog.run_id == run_id, RunLog.event_sequence > last_event_id)
            .order_by(RunLog.event_sequence.asc())
            .all()
        )
        return [run_log_to_event(log, correlation_id) for log in logs]
    finally:
        db.close()

@router.websocket("/ws/runs/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    correlation_id = websocket.query_params.get("correlation_id")
    raw_last_event_id = websocket.query_params.get("last_event_id")
    await manager.connect(run_id, websocket, correlation_id)
    if raw_last_event_id:
        try:
            last_event_id = int(raw_last_event_id)
            for event in get_missed_events(run_id, last_event_id, correlation_id):
                await websocket.send_json(event)
        except ValueError:
            await websocket.send_json({
                "event_id": None,
                "event_type": "REPLAY_ERROR",
                "run_id": run_id,
                "task_id": run_id,
                "correlation_id": correlation_id or f"BACK-{run_id}",
                "timestamp": None,
                "message": "last_event_id must be an integer",
                "payload": {"last_event_id": raw_last_event_id},
            })
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)
