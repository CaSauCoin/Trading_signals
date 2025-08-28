import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def error_handler(update: object, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text(
            "⚠️ An error has occurred. Please try again later."
        )