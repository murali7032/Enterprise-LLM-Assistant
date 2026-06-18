from fastapi import APIRouter

from app.security.authentication import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/token")
async def create_token(subject: str = "demo-user", role: str = "admin") -> dict[str, str]:
    """Issue a development JWT access token."""
    token = create_access_token(subject=subject, role=role)
    return {"access_token": token, "token_type": "bearer"}
