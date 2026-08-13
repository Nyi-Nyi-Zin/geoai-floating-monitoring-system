from fastapi import APIRouter

from app.schemas.health import HealthResponse
from app.services.health import get_health

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="API health")
def api_health() -> HealthResponse:
    return get_health()
