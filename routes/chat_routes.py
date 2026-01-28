from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from utils.context_utils import get_context, save_context, trim_context
from services.llm_service import generate_response
from services.tts_service import text_to_audio
import uuid, json, os, asyncio

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.websocket("/ws/audio/{session_id}")
async def chat_ws_audio(websocket: WebSocket, session_id: str):
    await websocket.accept()

    messages = get_context(session_id)

    partial_segments: list[str] = []

    try:
        while True:
            msg = await websocket.receive()

            if msg["type"] == "websocket.disconnect":
                break

            if not msg.get("text"):
                continue

            data = json.loads(msg["text"])

            # -------------------------
            # PARTIAL TEXT
            # -------------------------
            if data["type"] == "partial":
                text = data["text"].strip()
                if text:
                    partial_segments.append(text)

            # -------------------------
            # FINAL TEXT
            # -------------------------
            elif data["type"] == "final":
                final_text = data["text"].strip()

                if not final_text:
                    continue

                # 🔹 Use FINAL text as truth (preferred)
                # or fallback to joined partials
                user_text = final_text or " ".join(partial_segments)

                messages.append({"role": "user", "content": user_text})

                reply = await asyncio.to_thread(
                    generate_response, messages
                )

                messages.append({"role": "assistant", "content": reply})
                messages = trim_context(messages)
                save_context(session_id, messages)

                # 🔊 TTS (single response)
                reply_audio_path = f"/tmp/{uuid.uuid4()}.wav"
                text_to_audio(reply, reply_audio_path)

                with open(reply_audio_path, "rb") as f:
                    await websocket.send_bytes(f.read())

                os.remove(reply_audio_path)

                # 🔄 Reset for next turn
                partial_segments.clear()

    except WebSocketDisconnect:
        pass

    except Exception as e:
        print("❌ WS error:", e)

    finally:
        print("🧹 WS cleanup done")
