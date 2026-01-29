from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from utils.context_utils import get_context, save_context, trim_context
from services.llm_service import generate_response
from services.tts_service import text_to_audio
import uuid, json, os, asyncio
from prompts.doctor import DOCTOR_PROMPT
from services.session_service import create_session
import re

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/doctor")
def start_doctor_chat():
    session_id = create_session(DOCTOR_PROMPT)
    return {
        "session_id": session_id,
        "role": "doctor"
    }
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

                user_text = final_text or " ".join(partial_segments)
                messages.append({"role": "user", "content": user_text})

                # 🔹 Get SAFE JSON response from LLM
                llm_raw = await asyncio.to_thread(generate_response, messages)

                # 🛡️ ROBUST JSON PARSING WITH FALLBACK
                llm_json = {
                    "transcript": "Sorry, try again. What hurts?",
                    "hint": "",
                    "grammarMistake": "",
                    "correctGrammar": ""
                }

                try:
                    parsed = json.loads(llm_raw)
                    # Validate required fields
                    required_fields = ["transcript", "hint", "grammarMistake", "correctGrammar"]
                    if all(k in parsed for k in required_fields):
                        llm_json = parsed
                        
                        # 🔐 Sanitize transcript for JSON safety
                        transcript = str(llm_json["transcript"])
                        # Remove JSON artifacts, limit length
                        transcript = transcript.replace('"{', '{').replace('"}', '}') \
                                             .replace('\\"', '"').replace("\\n", "\n") \
                                             .replace("```json", "").replace("```", "")
                        if len(transcript) > 400:
                            transcript = transcript[:397] + "..."
                        
                        llm_json["transcript"] = transcript
                    else:
                        print(f"❌ Missing fields in LLM response: {llm_raw[:100]}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ LLM JSON Error: {e} | Raw: {llm_raw[:200]}...")
                    # Extract usable text if possible
                    clean_text = re.sub(r'[{\[\]}"]', '', llm_raw).strip()
                    if clean_text:
                        llm_json["transcript"] = clean_text[:200]

                # Final safety check
                if not llm_json["transcript"].strip():
                    llm_json["transcript"] = "Please speak clearly. What is wrong?"

                # Update messages with clean transcript
                messages.append({
                    "role": "assistant", 
                    "content": llm_json["transcript"]
                })

                messages = trim_context(messages)
                save_context(session_id, messages)

                # 🔊 TTS only clean transcript
                reply_audio_path = f"/tmp/{uuid.uuid4()}.wav"
                text_to_audio(llm_json["transcript"], reply_audio_path)

                # 📤 Send bulletproof JSON first
                await websocket.send_text(json.dumps({
                    "type": "assistant_response",
                    "payload": llm_json
                }, ensure_ascii=False))

                # 📤 Send audio
                try:
                    with open(reply_audio_path, "rb") as f:
                        await websocket.send_bytes(f.read())
                except FileNotFoundError:
                    print("❌ Audio file missing")
                
                # 🧹 Cleanup
                if os.path.exists(reply_audio_path):
                    os.remove(reply_audio_path)

                partial_segments.clear()

    except WebSocketDisconnect:
        print(f"🔌 WS disconnected: {session_id}")
    except Exception as e:
        print(f"❌ WS error {session_id}: {e}")
        await websocket.close(code=1011)  # Internal error
    finally:
        print(f"🧹 WS cleanup complete: {session_id}")
