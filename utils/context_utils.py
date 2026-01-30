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

def trim_context(messages: list) -> list:
    if not messages:
        return messages

    # Keep ALL system messages
    system_msgs = [m for m in messages if m.get("role") == "system"]
    chat_msgs = [m for m in messages if m.get("role") != "system"]

    # Only trim if exceeding limit
    if len(chat_msgs) <= settings.MAX_MESSAGES:
        return system_msgs + chat_msgs

    return system_msgs + chat_msgs[-settings.MAX_MESSAGES:]

