from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.transcription import router as transcription_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(transcription_router, tags=["Transcription"])
