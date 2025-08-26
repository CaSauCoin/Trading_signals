import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def error_handler(update: object, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text(
            "⚠️ Đã xảy ra lỗi. Vui lòng thử lại sau."
        )