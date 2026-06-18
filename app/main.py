from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.exceptions import AppException, LLMProviderException
from app.dependencies import validate_provider_configuration
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_provider_configuration()
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", debug=settings.DEBUG, lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(agents_router)

if settings.METRICS_ENABLED:
    app.mount("/metrics", make_asgi_app())


@app.exception_handler(AppException)
async def app_exception_handler(_, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})


@app.exception_handler(LLMProviderException)
async def llm_exception_handler(_, exc: LLMProviderException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"message": exc.message})
