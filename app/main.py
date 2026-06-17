from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.chat import router as chat_router

app = FastAPI(
    title="LLMOps Assistant",
    version="1.0.0"
)

app.include_router(health_router)

app.include_router(chat_router)