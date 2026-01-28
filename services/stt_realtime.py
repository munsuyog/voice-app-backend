from openai import OpenAI
import tempfile, asyncio, time
from services.openai_service import client

_last_call = 0

async def transcribe_partial(audio_bytes: bytes) -> str:
    global _last_call

    # debounce (VERY IMPORTANT)
    if time.time() - _last_call < 0.4:
        return ""

    _last_call = time.time()

    with tempfile.NamedTemporaryFile(suffix=".webm") as f:
        f.write(audio_bytes)
        f.flush()

        result = await asyncio.to_thread(
            lambda: client.audio.transcriptions.create(
                file=open(f.name, "rb"),
                model="gpt-4o-transcribe",
            )
        )

    return result.text
