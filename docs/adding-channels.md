# Adding New Messaging Channels

Devinder AI Agent Studio supports running workflows via external chat integrations (like Telegram, Slack, or WhatsApp). This guide explains how to add new channels using the pattern established by the Telegram integration.

## Channel Architecture

All messaging channels operate as independent workers or webhook receivers. They:
1. Ingest inbound user messages.
2. Resolve a configured or default workflow template.
3. Call `RuntimeService.execute_run()` asynchronously or inside a background task.
4. Listen for completion and reply back to the user with the final text output.

## Pattern for New Channels (e.g. Slack Worker)

To add a Slack integration:

### 1. Create the Slack Worker Module
Create `backend/app/channels/slack_worker.py`:

```python
import os
import asyncio
import logging
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.rtm_v2 import RTMClient
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import WorkflowRun
from app.runtime.engine import RuntimeService
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncWebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

def is_configured() -> bool:
    return bool(os.getenv("SLACK_BOT_TOKEN"))

async def handle_slack_message(payload):
    data = payload.get("data", {})
    if data.get("type") == "message" and not data.get("bot_id"):
        user_message = data.get("text")
        channel_id = data.get("channel")
        
        workflow_id = os.getenv("DEFAULT_SLACK_WORKFLOW_ID")
        
        # Instantiate and run
        db = SessionLocal()
        try:
            import uuid
            from datetime import datetime
            run_id = str(uuid.uuid4())
            
            # Persist run entry as QUEUED
            new_run = WorkflowRun(
                id=run_id, 
                workflow_id=workflow_id, 
                input_json=json.dumps({"message": user_message}), 
                status="QUEUED", 
                started_at=datetime.utcnow()
            )
            db.add(new_run)
            db.commit()
            
            await client.chat_postMessage(channel=channel_id, text="Starting workflow processing...")
            
            # Execute
            run = await RuntimeService.execute_run(db, run_id, workflow_id, {"message": user_message})
            
            if run.status == "COMPLETED" and run.output_json:
                output = json.loads(run.output_json)
                await client.chat_postMessage(channel=channel_id, text=output.get("final_message"))
            else:
                await client.chat_postMessage(channel=channel_id, text=f"Workflow failed: {run.error_message}")
        except Exception as e:
            logger.error(f"Slack error: {e}")
        finally:
            db.close()
```

### 2. Configure Environment variables
Add keys inside your `.env` and `.env.example`:
```env
SLACK_BOT_TOKEN=xoxb-...
DEFAULT_SLACK_WORKFLOW_ID=your-default-workflow-id
```

### 3. Add to Makefile & Docker Compose
Create a start target in the `Makefile`:
```makefile
slack:
	cd backend && ./venv/bin/python -m app.channels.slack_worker
```

Add a service definition in `docker-compose.yml`:
```yaml
  slack-worker:
    build:
      context: ./backend
    env_file:
      - .env
    depends_on:
      - backend
    command: python -m app.channels.slack_worker
    profiles:
      - slack
```
