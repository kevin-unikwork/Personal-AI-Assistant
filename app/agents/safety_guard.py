# In-memory dictionary for pending transactions
# Replaces Redis for dependency-free setup
_pending_actions = {}

class SafetyGuard:
    def __init__(self):
        self.ttl = 3600  # Memory dict does not handle ttl out of the box, clears on restart

    def set_pending_action(self, user_phone: str, action_data: dict, original_message: str):
        key = f"pending:{user_phone}"
        action_data["original_message"] = original_message
        _pending_actions[key] = action_data

    def get_pending_action(self, user_phone: str) -> dict | None:
        key = f"pending:{user_phone}"
        return _pending_actions.get(key)

    def clear_pending_action(self, user_phone: str):
        key = f"pending:{user_phone}"
        if key in _pending_actions:
            del _pending_actions[key]
