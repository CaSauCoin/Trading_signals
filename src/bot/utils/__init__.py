def reset_user_state(user_id: int, context):
    """Reset user state"""
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    context.bot_data['user_states'][user_id] = {"waiting_for": None}

def set_user_state(user_id: int, context, waiting_for: str):
    """Set user state"""
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    context.bot_data['user_states'][user_id] = {"waiting_for": waiting_for}

def get_user_state(user_id: int, context):
    """Get user state"""
    if not hasattr(context.bot_data, 'user_states'):
        context.bot_data['user_states'] = {}
    
    return context.bot_data['user_states'].get(user_id, {"waiting_for": None})