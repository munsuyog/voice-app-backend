from core.config import settings
from services.openai_service import client

def generate_response(messages: list) -> str:
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,          # e.g. "gpt-5-nano"
        messages=messages,
        reasoning_effort="minimal",        # ✅ correct
    )
    return response.choices[0].message.content
