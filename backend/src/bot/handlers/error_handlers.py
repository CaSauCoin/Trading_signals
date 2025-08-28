# src/bot/handlers/error_handlers.py
import logging
from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

def error_handler(update: object, context: CallbackContext) -> None:
    """Ghi lại các lỗi và gửi thông báo cho người dùng."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        update.effective_message.reply_text(
            "⚠️ Đã có lỗi xảy ra. Vui lòng thử lại sau."
        )