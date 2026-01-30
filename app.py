from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chat_routes import router as chat_router

app = FastAPI(title="AI Chat Service")

# CORS – allow everything
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # allow all origins
    allow_credentials=True,
    allow_methods=["*"],        # allow all HTTP methods
    allow_headers=["*"],        # allow all headers
)

app.include_router(chat_router)

@app.get("/")
def health():
    return {"status": "ok"}
