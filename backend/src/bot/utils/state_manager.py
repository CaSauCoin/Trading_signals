# src/bot/utils/state_manager.py
from src.bot import constants as const

def _initialize_states(context):
    """Đảm bảo 'user_states' tồn tại trong bot_data."""
    if 'user_states' not in context.bot_data:
        context.bot_data['user_states'] = {}

def reset_user_state(user_id: int, context):
    """Reset trạng thái của người dùng."""
    _initialize_states(context)
    context.bot_data['user_states'][user_id] = {const.STATE_WAITING_FOR: None}

def set_user_state(user_id: int, context, waiting_for: str):
    """Thiết lập trạng thái chờ của người dùng."""
    _initialize_states(context)
    context.bot_data['user_states'][user_id] = {const.STATE_WAITING_FOR: waiting_for}

def get_user_state(user_id: int, context):
    """Lấy trạng thái hiện tại của người dùng."""
    _initialize_states(context)
    return context.bot_data['user_states'].get(user_id, {const.STATE_WAITING_FOR: None})