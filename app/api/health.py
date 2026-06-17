from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():

    return {
        "status": "UP"
    }


@router.get("/ready")
def ready():

    """
    Later this endpoint will verify:
        - Redis
        - PostgreSQL
        - Qdrant
        - OpenAI
    """

    return {
        "status": "READY"
    }