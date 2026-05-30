import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.constants import RunStatus
from app.models.models import WorkflowRun, ChannelMessage
from app.runtime.engine import RuntimeService, normalize_run_input
from app.core.logger import get_logger
import json

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am Devinder AI Agent Studio Bot. Send me a message to trigger a workflow.")

async def process_telegram_update(update_payload: dict, db: Session, chat_id: str, message_text: str):
    workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    if not workflow_id:
        return "Telegram bot is not configured with a default workflow."

    try:
        from datetime import datetime
        update_id = str(update_payload.get("update_id"))
        message_id = str(update_payload.get("message", {}).get("message_id"))
        from_id = str(update_payload.get("message", {}).get("from", {}).get("id"))
        external_id = f"TG-{update_id}"
        
        # Deduplication
        existing_msg = db.query(ChannelMessage).filter(
            ChannelMessage.external_message_id == external_id,
            ChannelMessage.channel_type == "TELEGRAM"
        ).first()
        
        if existing_msg:
            logger.info(f"Duplicate update {external_id} ignored")
            return "DUPLICATE"
            
        incoming_msg = ChannelMessage(
            channel_type="TELEGRAM",
            external_message_id=external_id,
            external_user_id=from_id,
            direction="INBOUND",
            status="RECEIVED",
            payload_json=json.dumps({"text": message_text, "message_id": message_id})
        )
        db.add(incoming_msg)
        db.commit()
        db.refresh(incoming_msg)

        input_data = normalize_run_input({"message": message_text, "source": "telegram"})
        input_data["chat_id"] = chat_id
        
        import uuid
        run_id = str(uuid.uuid4())
        input_data["correlation_id"] = f"TELEGRAM-{chat_id}"
        new_run = WorkflowRun(id=run_id, workflow_id=workflow_id, input_json=json.dumps(input_data), status=RunStatus.QUEUED.value, started_at=datetime.utcnow())
        db.add(new_run)
        
        incoming_msg.run_id = run_id
        db.commit()
        db.refresh(new_run)
        
        structured_logger.info(
            "Telegram workflow run started",
            extra={"correlation_id": input_data["correlation_id"], "run_id": run_id, "task_id": run_id},
        )
        run = await RuntimeService.execute_run(db, run_id, workflow_id, input_data)
        
        if run.status == RunStatus.COMPLETED.value and run.output_json:
            output = json.loads(run.output_json)
            final_message = output.get("final_message", "Workflow completed but returned no message.")
            
            outgoing_msg = ChannelMessage(
                channel_type="TELEGRAM",
                external_message_id=f"OUT-{run_id}",
                external_user_id=from_id,
                run_id=run_id,
                direction="OUTBOUND",
                status="SENT",
                payload_json=json.dumps({"text": final_message})
            )
            db.add(outgoing_msg)
            db.commit()
            return final_message
        else:
            return f"Workflow failed or incomplete. Error: {run.error_message}"
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        return "An error occurred during workflow execution."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id = str(update.effective_chat.id)
    
    await update.message.reply_text("Starting workflow processing...")
    
    db = SessionLocal()
    try:
        update_payload = {
            "update_id": update.update_id,
            "message": {
                "message_id": update.message.message_id,
                "from": {"id": update.message.from_user.id}
            }
        }
        res = await process_telegram_update(update_payload, db, chat_id, user_message)
        if res and res != "DUPLICATE":
            await update.message.reply_text(res)

    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text("An error occurred during workflow execution.")
    finally:
        db.close()

def is_configured() -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    default_workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    return bool(token and default_workflow_id)

async def telegram_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram error while handling update", exc_info=context.error)

def main():
    if not is_configured():
        logger.info("Telegram disabled: TELEGRAM_BOT_TOKEN and DEFAULT_TELEGRAM_WORKFLOW_ID must both be configured")
        return

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(telegram_error_handler)

    logger.info("Starting Telegram polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        stop_signals=None,
    )

if __name__ == "__main__":
    main()
