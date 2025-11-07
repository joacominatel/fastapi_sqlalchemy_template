from fastapi import APIRouter
from core.config import settings

router = APIRouter()

@router.get("/health", summary="Health check", tags=["health"])
async def healthcheck():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}
