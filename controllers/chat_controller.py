from services.chat_service import process_message
from schemas.chat_schema import ChatRequest, ChatResponse

def chat_controller(payload: ChatRequest) -> ChatResponse:
    session_id, reply = process_message(
        payload.message,
        payload.session_id
    )

    return ChatResponse(
        session_id=session_id,
        reply=reply
    )
