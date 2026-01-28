from openai import OpenAI
from pathlib import Path
from services.openai_service import client

def text_to_audio(text: str, out_path: str):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        input=text,
        speed=1
    )

    with open(out_path, "wb") as f:
        f.write(response.read())
