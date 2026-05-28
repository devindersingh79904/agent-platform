import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.constants import RunStatus
from app.models.models import WorkflowRun
from app.runtime.engine import RuntimeService, normalize_run_input
from app.core.logger import get_logger
import json

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am Yuno Agent Studio Bot. Send me a message to trigger a workflow.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = update.effective_chat.id
    
    workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    if not workflow_id:
        await update.message.reply_text("Telegram bot is not configured with a default workflow.")
        return

    await update.message.reply_text("Starting workflow processing...")
    
    db = SessionLocal()
    try:
        # Execute run synchronously within this handler for MVP simplicity (or could be background)
        # Using a simplistic approach to await the execution
        input_data = normalize_run_input({"message": user_message, "source": "telegram"})
        input_data["chat_id"] = chat_id
        
        import uuid
        from datetime import datetime
        run_id = str(uuid.uuid4())
        input_data["correlation_id"] = f"TELEGRAM-{chat_id}"
        new_run = WorkflowRun(id=run_id, workflow_id=workflow_id, input_json=json.dumps(input_data), status=RunStatus.QUEUED.value, started_at=datetime.utcnow())
        db.add(new_run)
        db.commit()
        db.refresh(new_run)
        
        structured_logger.info(
            "Telegram workflow run started",
            extra={"correlation_id": input_data["correlation_id"], "run_id": run_id, "task_id": run_id},
        )
        run = await RuntimeService.execute_run(db, run_id, workflow_id, input_data)
        
        # After run completes, send output back
        if run.status == RunStatus.COMPLETED.value and run.output_json:
            output = json.loads(run.output_json)
            final_message = output.get("final_message", "Workflow completed but returned no message.")
            await update.message.reply_text(final_message)
        else:
            await update.message.reply_text(f"Workflow failed or incomplete. Error: {run.error_message}")
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("An error occurred during workflow execution.")
    finally:
        db.close()

def is_configured() -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    default_workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    return bool(token and default_workflow_id)

def main():
    if not is_configured():
        logger.info("Telegram disabled: TELEGRAM_BOT_TOKEN and DEFAULT_TELEGRAM_WORKFLOW_ID must both be configured")
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting Telegram polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
