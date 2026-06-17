from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.chat import router as chat_router
from app.api.health import router as health_router

from app.core.exceptions import LLMProviderException
from app.middleware.request_id import RequestIDMiddleware

app = FastAPI(
    title="Enterprise LLM Platform",
    version="1.0.0"
)

# -----------------------------
# Middleware
# -----------------------------

app.add_middleware(RequestIDMiddleware)

# -----------------------------
# Routers
# -----------------------------

app.include_router(health_router)
app.include_router(chat_router)

# -----------------------------
# Exception Handlers
# -----------------------------


@app.exception_handler(LLMProviderException)
async def llm_exception_handler(
    request: Request,
    exc: LLMProviderException
):

    return JSONResponse(
        status_code=500,
        content={
            "message": "LLM Provider Unavailable"
        }
    )