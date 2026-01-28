from uuid import uuid4
from utils.context_utils import get_context, save_context, trim_context
from services.llm_service import generate_response

def process_message(message: str, session_id: str | None):
    if not session_id:
        session_id = str(uuid4())

    messages = get_context(session_id)

    messages.append({"role": "user", "content": message})

    reply = generate_response(messages)

    messages.append({"role": "assistant", "content": reply})

    messages = trim_context(messages)
    save_context(session_id, messages)

    return session_id, reply
