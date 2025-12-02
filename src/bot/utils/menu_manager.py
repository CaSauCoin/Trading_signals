import logging
from telegram.ext import CallbackContext
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

ACTIVE_MENU_ID = "active_menu_id"

def set_active_menu(user_id: int, context: CallbackContext, message_id: int):
    """Lưu message_id của menu đang hoạt động."""
    context.user_data[ACTIVE_MENU_ID] = message_id

def get_active_menu(user_id: int, context: CallbackContext) -> int | None:
    """Lấy message_id của menu đang hoạt động."""
    return context.user_data.get(ACTIVE_MENU_ID)

def delete_active_menu(user_id: int, context: CallbackContext):
    """Xóa menu đang hoạt động trước đó (nếu có)."""
    active_menu_id = get_active_menu(user_id, context)
    if active_menu_id:
        try:
            context.bot.delete_message(chat_id=user_id, message_id=active_menu_id)
        except BadRequest as e:
            if "message to delete not found" in str(e).lower() or "message can't be deleted" in str(e).lower():
                logger.info(f"Không thể xóa menu cũ (ID: {active_menu_id}) cho user {user_id}.")
            else:
                logger.error(f"Lỗi khi xóa menu cũ (ID: {active_menu_id}): {e}")
        finally:
            if ACTIVE_MENU_ID in context.user_data:
                del context.user_data[ACTIVE_MENU_ID]