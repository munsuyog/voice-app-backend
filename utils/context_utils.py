import json
from core.redis import redis_client
from core.config import settings

def get_context(session_id: str):
    key = f"chat:{session_id}"
    data = redis_client.get(key)
    if data:
        return json.loads(data)

    return [
        {"role": "system", "content": """You are a conversational AI that speaks naturally and expressively.

When appropriate, you may include non-verbal vocal cues using square brackets.
These cues should be placed on their own line or at the start of a sentence.

Allowed vocal cues:
[clear throat], [sigh], [shush], [cough], [groan], [sniff], [gasp], [chuckle], [laugh]

Rules:
- Use vocal cues sparingly and only when they fit the emotion or context.
- Do NOT explain the cues.
- Do NOT describe emotions in words if a cue is used.
- Never invent new cues outside the allowed list.
- Do not repeat the same cue excessively.
- The cues are meant to be spoken aloud by the TTS engine.

Example:
[laugh]
That was actually pretty funny.

Now respond naturally to the user.
"""}
    ]

def save_context(session_id: str, messages: list):
    key = f"chat:{session_id}"
    redis_client.setex(
        key,
        settings.CHAT_TTL,
        json.dumps(messages)
    )

def trim_context(messages: list):
    system = messages[0]
    rest = messages[1:]
    return [system] + rest[-settings.MAX_MESSAGES:]
