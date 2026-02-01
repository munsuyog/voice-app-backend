from fastapi import APIRouter, WebSocket, HTTPException
from starlette.websockets import WebSocketDisconnect
from utils.context_utils import get_context, save_context, trim_context
from services.llm_service import generate_response
from services.tts_service import text_to_audio
import uuid, json, os, asyncio
from prompts.doctor import DOCTOR_PROMPT
from services.session_service import create_session
import re
from prompts.insights import LEARNING_INSIGHTS_PROMPT
from prompts.shivaji_maharaj import HISTORY_PROMPT
from prompts.friend import FRIEND_PROMPT
from prompts.geography import INDIA_GEOGRAPHY_PROMPT
from utils.overpass import overpass_to_geojson
from prompts.convo import INTRODUCE_YOURSELF_PROMPT

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/doctor")
def start_doctor_chat():
    session_id = create_session(DOCTOR_PROMPT)
    return {
        "session_id": session_id,
        "role": "doctor"
    }
    
@router.post("/shivaji-maharaj")
def start_history_chat():
    session_id = create_session(HISTORY_PROMPT)
    return {
        "session_id": session_id,
        "role": "shivaji-maharaj"
    }
    
@router.post("/friend")
def start_friend_chat():
    session_id = create_session(FRIEND_PROMPT)
    return {
        "session_id": session_id,
        "role": "doctor"
    }
    
    
@router.post("/introduce")
def start_intro_chat():
    session_id = create_session(INTRODUCE_YOURSELF_PROMPT)
    return {
        "session_id": session_id,
        "role": "teacher"
    }

@router.post("/geography")
def start_geography():
    session_id = create_session(INDIA_GEOGRAPHY_PROMPT)
    return {
        "session_id": session_id,
        "role": "doctor"
    }


@router.get("/insights/deep/{session_id}")
async def get_deep_chat_insights(session_id: str):
    messages = get_context(session_id)

    if not messages or len(messages) < 3:
        raise HTTPException(
            status_code=400,
            detail="Not enough conversation data for deep analysis"
        )

    analysis_messages = [
        {"role": "system", "content": LEARNING_INSIGHTS_PROMPT},
        {
            "role": "user",
            "content": "Conversation:\n" + "\n".join(
                f"{m['role'].upper()}: {m['content']}"
                for m in messages
                if m["role"] in ["user", "assistant"]
            )
        }
    ]

    llm_raw = await asyncio.to_thread(generate_response, analysis_messages)

    # Strong fallback structure
    fallback = {
        "overallLevel": "beginner",
        "confidenceLevel": "low",
        "communicationReadiness": {
            "realWorldDoctorVisit": "not_ready",
            "reason": "Limited sentence clarity"
        },
        "skillBreakdown": {
            "grammar": "weak",
            "vocabulary": "weak",
            "fluency": "weak",
            "pronunciationClarity": "average"
        },
        "recurringMistakes": [],
        "vocabularyGaps": [],
        "strengths": [],
        "priorityFocusAreas": [],
        "practicePlan": {
            "dailyExercises": [],
            "rolePlaySuggestions": [],
            "sentencePatternsToPractice": []
        },
        "teacherFeedbackSummary": "Needs guided practice"
    }

    try:
        insights = json.loads(llm_raw)
    except json.JSONDecodeError:
        print("❌ Deep insights JSON error")
        clean = re.sub(r'[^\w\s,.:-]', '', llm_raw)
        fallback["teacherFeedbackSummary"] = clean[:200]
        insights = fallback

    return {
        "session_id": session_id,
        "insights": insights
    }    

@router.websocket("/ws/audio/{session_id}")
async def chat_ws_audio(websocket: WebSocket, session_id: str):
    await websocket.accept()

    messages = get_context(session_id)
    if messages is None:
        messages = []
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


@router.websocket("/ws/geography/{session_id}")
async def geography_ws(websocket: WebSocket, session_id: str):
    await websocket.accept()

    messages = get_context(session_id)
    if messages is None:
        messages = []
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
            # PARTIAL TEXT (speech streaming)
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
                partial_segments.clear()

                messages.append({"role": "user", "content": user_text})

                # 1️⃣ LLM RESPONSE
                llm_raw = await asyncio.to_thread(generate_response, messages)

                # 🛡️ ROBUST JSON PARSING WITH FALLBACK
                llm_json = {
                    "transcript": "I can help you explore India's geography. What would you like to know?",
                    "overpassQuery": None
                }

                try:
                    parsed = json.loads(llm_raw)
                    
                    # Validate it's a dict and has transcript
                    if isinstance(parsed, dict) and "transcript" in parsed:
                        llm_json = parsed
                    else:
                        print(f"❌ Invalid LLM structure: {llm_raw[:200]}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Geography LLM JSON Error: {e}")
                    print(f"Raw response: {llm_raw[:300]}")
                    
                    # Try to extract usable text
                    clean_text = re.sub(r'```json|```|[{}\[\]]', '', llm_raw).strip()
                    if clean_text and len(clean_text) > 10:
                        llm_json["transcript"] = clean_text[:300]

                transcript = llm_json.get("transcript", "Could you please rephrase that?")
                overpass_query = llm_json.get("overpassQuery")
                highlights = llm_json.get("highlights", [])

                # 2️⃣ RUN OVERPASS & TTS IN PARALLEL ⚡
                audio_path = f"/tmp/{uuid.uuid4()}.wav"
                
                async def fetch_geojson():
                    """Fetch GeoJSON data from Overpass API"""
                    if overpass_query:
                        try:
                            return await overpass_to_geojson(overpass_query)
                        except Exception as e:
                            print(f"❌ Overpass error: {e}")
                            return None
                    return None
                
                async def generate_audio():
                    """Generate TTS audio file"""
                    try:
                        await asyncio.to_thread(text_to_audio, transcript, audio_path)
                    except Exception as e:
                        print(f"❌ TTS error: {e}")
                
                # Execute both tasks concurrently - saves time!
                results = await asyncio.gather(
                    fetch_geojson(),
                    generate_audio(),
                    return_exceptions=True
                )
                
                geojson = results[0] if not isinstance(results[0], Exception) else None

                # 3️⃣ SEND GEOJSON FIRST (MAP CAN RENDER NOW)
                if geojson:
                    await websocket.send_text(json.dumps({
                        "type": "geojson",
                        "payload": geojson
                    }))

                # 3.5️⃣ SEND HIGHLIGHTS (POINT MARKERS)
                if highlights and isinstance(highlights, list):
                    await websocket.send_text(json.dumps({
                        "type": "highlights",
                        "payload": highlights
                    }))

                # 4️⃣ SAVE CLEAN ASSISTANT MESSAGE
                messages.append({
                    "role": "assistant",
                    "content": transcript
                })
                messages = trim_context(messages)
                save_context(session_id, messages)

                # 5️⃣ SEND TEXT RESPONSE
                await websocket.send_text(json.dumps({
                    "type": "assistant_response",
                    "payload": llm_json
                }, ensure_ascii=False))

                # 6️⃣ SEND AUDIO (ALREADY GENERATED IN PARALLEL)
                try:
                    with open(audio_path, "rb") as f:
                        await websocket.send_bytes(f.read())
                except FileNotFoundError:
                    print("❌ Audio file not generated")
                finally:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)

    except WebSocketDisconnect:
        print(f"🔌 Geography WS disconnected: {session_id}")
    except Exception as e:
        print(f"❌ Geography WS error: {e}")
        await websocket.close(code=1011)
    finally:
        print(f"🧹 Geography WS cleanup complete: {session_id}")