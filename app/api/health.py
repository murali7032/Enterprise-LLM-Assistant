from fastapi import APIRouter, Depends

from app.clients.qdrant_client import QdrantClientWrapper
from app.clients.redis_client import RedisClient
from app.dependencies import get_qdrant_client, get_redis_client

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "UP"}


@router.get("/live")
async def live() -> dict[str, str]:
    """Alias liveness endpoint."""
    return {"status": "ALIVE"}


@router.get("/ready")
async def ready(
    redis_client: RedisClient = Depends(get_redis_client),
    qdrant_client: QdrantClientWrapper = Depends(get_qdrant_client),
) -> dict[str, object]:
    """Readiness probe with dependency checks."""
    checks: dict[str, object] = {"api": True, "redis": False, "qdrant": False}
    try:
        checks["redis"] = await redis_client.ping()
    except Exception:
        checks["redis"] = False
    try:
        checks["qdrant"] = await qdrant_client.health()
    except Exception:
        checks["qdrant"] = False
    status = "READY" if all(checks.values()) else "DEGRADED"
    return {"status": status, "checks": checks}
