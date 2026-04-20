import json
from app.utils.logger import logger

# In-memory dictionary for short-term history. 
# Replaces Redis for the dependency-free native build.
# Keys are user_id strings, values are lists of message dictionaries.
_history_store = {}

class ShortTermMemory:
    def __init__(self):
        self.ttl = 86400  # Note: In-memory store does not use TTL. Clears on restart.

    def load(self, user_id: str) -> list[dict]:
        """Load last 20 messages from in-memory store."""
        key = f"conv:{user_id}"
        messages = _history_store.get(key, [])
        
        history = []
        for msg in messages:
            try:
                history.append(json.loads(msg))
            except Exception:
                continue
        return history

    def save(self, user_id: str, human_msg: str, ai_msg: str) -> None:
        """Append turn to in-memory list, trim to last 20"""
        key = f"conv:{user_id}"
        
        if key not in _history_store:
            _history_store[key] = []
            
        # We store as structured format for LangChain's BaseMessage processing later
        human_data = json.dumps({"role": "user", "content": human_msg})
        ai_data = json.dumps({"role": "assistant", "content": ai_msg})
        
        _history_store[key].append(human_data)
        _history_store[key].append(ai_data)
        
        # Trim to keep only the last 40 items (20 turns)
        _history_store[key] = _history_store[key][-40:]
        
        logger.debug("Saved short term memory", extra={"user_id": user_id})
