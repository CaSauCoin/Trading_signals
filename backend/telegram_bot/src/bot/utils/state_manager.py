from datetime import datetime

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

def log_state_change(user_id: int, new_state: str):
    """Log state changes"""
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] User {user_id} state changed to: {new_state}")

# Keep the class if you want to use it later
class StateManager:
    def __init__(self):
        self.user_states = {}

    def set_user_state(self, user_id, state):
        self.user_states[user_id] = state

    def get_user_state(self, user_id):
        return self.user_states.get(user_id, None)

    def reset_user_state(self, user_id):
        if user_id in self.user_states:
            del self.user_states[user_id]

    def log_state_change(self, user_id, new_state):
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] User {user_id} state changed to: {new_state}")