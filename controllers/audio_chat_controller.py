from fastapi import UploadFile
from schemas.chat_schema import ChatResponse
from services.chat_service import process_message
from services.stt_service import audio_to_text
from services.tts_service import text_to_audio
import uuid
import os


def audio_chat_controller(
    audio: UploadFile,
    session_id: str | None = None
):
    # Save uploaded audio
    audio_path = f"/tmp/{uuid.uuid4()}.wav"
    with open(audio_path, "wb") as f:
        f.write(audio.file.read())

    # 1️⃣ Speech → Text
    user_text = audio_to_text(audio_path)

    # 2️⃣ Text → LLM
    session_id, reply_text = process_message(user_text, session_id)

    # 3️⃣ Text → Speech
    reply_audio_path = f"/tmp/{uuid.uuid4()}.mp3"
    text_to_audio(reply_text, reply_audio_path)

    return {
        "session_id": session_id,
        "user_text": user_text,
        "reply_text": reply_text,
        "reply_audio_path": reply_audio_path
    }
