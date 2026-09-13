import hmac
from typing import Optional
from fastapi import Header, Request

from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ModelUnavailableException
from app.engines.base import BaseSTTEngine
from app.infrastructure.ffmpeg import FFmpegWrapper
from app.infrastructure.ffprobe import FFprobeWrapper


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> None:
    """
    Validates X-API-Key header against server settings.
    If settings.API_KEY is not configured (None or empty), authentication is bypassed.
    """
    configured_key = settings.API_KEY
    if not configured_key:
        return  # Auth disabled in development or if unset

    if not x_api_key:
        raise UnauthorizedException("Missing required X-API-Key header")

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_api_key, configured_key):
        raise UnauthorizedException("Invalid X-API-Key provided")


def get_stt_engine(request: Request) -> BaseSTTEngine:
    """Retrieves the loaded STT Engine singleton from application state."""
    engine = getattr(request.app.state, "engine", None)
    if not engine or not engine.is_ready():
        raise ModelUnavailableException("STT Engine is not available or ready")
    return engine


def get_ffmpeg_wrapper(request: Request) -> FFmpegWrapper:
    """Retrieves FFmpegWrapper from app state or instantiates default."""
    wrapper = getattr(request.app.state, "ffmpeg", None)
    return wrapper if wrapper is not None else FFmpegWrapper()


def get_ffprobe_wrapper(request: Request) -> FFprobeWrapper:
    """Retrieves FFprobeWrapper from app state or instantiates default."""
    wrapper = getattr(request.app.state, "ffprobe", None)
    return wrapper if wrapper is not None else FFprobeWrapper()
