from fastapi import FastAPI
from routes.chat_routes import router as chat_router

app = FastAPI(title="AI Chat Service")

app.include_router(chat_router)

@app.get("/")
def health():
    return {"status": "ok"}
