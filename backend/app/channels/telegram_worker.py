import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.constants import RunStatus
from app.models.models import WorkflowRun, ChannelMessage, Workflow
from app.runtime.engine import RuntimeService, normalize_run_input
from app.core.logger import get_logger
from app.services.workflow_run_service import WorkflowRunService
import json

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
structured_logger = get_logger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I am Devinder AI Agent Studio Bot. Send me a message to trigger a workflow.")

async def process_telegram_update(update_payload: dict, db: Session, chat_id: str, message_text: str):
    correlation_id = f"TELEGRAM-{chat_id}"
    logger.info(
        f"TELEGRAM_MESSAGE_RECEIVED - chat_id={chat_id}",
        extra={"correlation_id": correlation_id, "run_id": "-", "task_id": "-"}
    )

    workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    if not workflow_id:
        logger.error(
            "TELEGRAM_WORKFLOW_EXECUTION_FAILED - DEFAULT_TELEGRAM_WORKFLOW_ID environment variable is missing",
            extra={"correlation_id": correlation_id, "run_id": "-", "task_id": "-"}
        )
        return "Telegram bot is not configured with a default workflow."

    try:
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
        
        logger.info(
            f"TELEGRAM_CHANNEL_MESSAGE_CREATED - channel_message_id={incoming_msg.id}",
            extra={"correlation_id": correlation_id, "run_id": "-", "task_id": "-"}
        )

        # Validate that workflow exists in the DB
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            logger.error(
                f"TELEGRAM_WORKFLOW_EXECUTION_FAILED - Configured Telegram workflow {workflow_id} does not exist in database",
                extra={"correlation_id": correlation_id, "run_id": "-", "task_id": "-"}
            )
            return "Telegram workflow is not configured correctly. Please contact the admin."

        logger.info(
            f"TELEGRAM_WORKFLOW_VALIDATED - workflow_id={workflow_id}",
            extra={"correlation_id": correlation_id, "run_id": "-", "task_id": "-"}
        )

        # Create workflow run
        input_data = {"message": message_text, "source": "telegram", "chat_id": chat_id, "correlation_id": correlation_id}
        new_run = WorkflowRunService.create_run(
            db=db,
            workflow_id=workflow_id,
            input_data=input_data,
            trigger_source="telegram",
            commit=True
        )

        logger.info(
            f"TELEGRAM_WORKFLOW_RUN_CREATED - run_id={new_run.id}",
            extra={"correlation_id": correlation_id, "run_id": new_run.id, "task_id": new_run.id}
        )

        # Link message to run
        incoming_msg.run_id = new_run.id
        db.commit()

        logger.info(
            f"TELEGRAM_CHANNEL_MESSAGE_LINKED_TO_RUN - channel_message_id={incoming_msg.id}, run_id={new_run.id}",
            extra={"correlation_id": correlation_id, "run_id": new_run.id, "task_id": new_run.id}
        )
        
        logger.info(
            f"TELEGRAM_WORKFLOW_EXECUTION_STARTED - run_id={new_run.id}",
            extra={"correlation_id": correlation_id, "run_id": new_run.id, "task_id": new_run.id}
        )
        
        try:
            run = await RuntimeService.execute_run(db, new_run.id, workflow_id, input_data)
        except Exception as exec_err:
            logger.exception("Error executing workflow run")
            db.rollback()
            new_run.status = RunStatus.FAILED.value
            new_run.error_message = str(exec_err)
            db.commit()
            logger.error(
                f"TELEGRAM_WORKFLOW_EXECUTION_FAILED - run_id={new_run.id}",
                extra={"correlation_id": correlation_id, "run_id": new_run.id, "task_id": new_run.id}
            )
            return "An error occurred during workflow execution."
        
        if run.status == RunStatus.COMPLETED.value and run.output_json:
            output = json.loads(run.output_json)
            final_message = output.get("final_message", "Workflow completed but returned no message.")
            
            outgoing_msg = ChannelMessage(
                channel_type="TELEGRAM",
                external_message_id=f"OUT-{new_run.id}",
                external_user_id=from_id,
                run_id=new_run.id,
                direction="OUTBOUND",
                status="SENT",
                payload_json=json.dumps({"text": final_message})
            )
            db.add(outgoing_msg)
            db.commit()

            logger.info(
                f"TELEGRAM_WORKFLOW_EXECUTION_COMPLETED - run_id={new_run.id}",
                extra={"correlation_id": correlation_id, "run_id": new_run.id, "task_id": new_run.id}
            )
            return final_message
        else:
            db.rollback()
            new_run.status = RunStatus.FAILED.value
            new_run.error_message = run.error_message or "Workflow run failed or was incomplete"
            db.commit()
            logger.error(
                f"TELEGRAM_WORKFLOW_EXECUTION_FAILED - run_id={new_run.id}",
                extra={"correlation_id": correlation_id, "run_id": new_run.id, "task_id": new_run.id}
            )
            return f"Workflow failed or incomplete. Error: {run.error_message}"

    except Exception as e:
        db.rollback()
        logger.exception("Error handling Telegram update")
        run_id_for_log = new_run.id if 'new_run' in locals() else "-"
        logger.error(
            f"TELEGRAM_WORKFLOW_EXECUTION_FAILED - {e}",
            extra={"correlation_id": correlation_id, "run_id": run_id_for_log, "task_id": run_id_for_log}
        )
        if 'new_run' in locals():
            try:
                new_run.status = RunStatus.FAILED.value
                new_run.error_message = str(e)
                db.commit()
            except Exception:
                db.rollback()
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
        db.rollback()
        logger.exception("Exception in handle_message")
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

    # Startup validation
    workflow_id = os.getenv("DEFAULT_TELEGRAM_WORKFLOW_ID")
    db = SessionLocal()
    try:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            logger.error(f"Startup validation failed: Telegram default workflow ID '{workflow_id}' does not exist in the database.")
    except Exception as e:
        logger.error(f"Database error during startup validation: {e}")
    finally:
        db.close()

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
