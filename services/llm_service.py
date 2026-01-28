from core.config import settings
from services.openai_service import client

# Replace with your LLM client
def generate_response(messages: list) -> str:
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=messages
    )
    return response.choices[0].message.content
