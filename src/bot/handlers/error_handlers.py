# src/bot/handlers/error_handlers.py
import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def error_handler(update: object, context: CallbackContext) -> None:
    """Log errors and send notification to user."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again later."
        )