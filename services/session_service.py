import uuid
from utils.context_utils import save_context

def create_session(system_prompt: str):
    session_id = str(uuid.uuid4())

    messages = [
        {"role": "system", "content": system_prompt}
    ]

    save_context(session_id, messages)
    return session_id
