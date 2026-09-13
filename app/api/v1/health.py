from fastapi import APIRouter, Request
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns service health status and basic engine configuration without executing transcription.",
)
async def health_check(request: Request) -> HealthResponse:
    engine = getattr(request.app.state, "engine", None)
    is_ready = engine.is_ready() if engine is not None else False

    return HealthResponse(
        status="ok" if is_ready else "starting",
        engine=settings.STT_ENGINE,
        model=settings.STT_MODEL,
        device=settings.STT_DEVICE,
    )
