import json
from core.redis import redis_client
from core.config import settings

def get_context(session_id: str):
    data = redis_client.get(f"chat:{session_id}")
    return json.loads(data) if data else None

def save_context(session_id: str, messages: list):
    redis_client.setex(
        f"chat:{session_id}",
        settings.CHAT_TTL,
        json.dumps(messages)
    )

def trim_context(messages: list):
    system = messages[0]
    rest = messages[1:]
    return [system] + rest[-settings.MAX_MESSAGES:]
