from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI

from app.api.router import api_v1_router
from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.ffmpeg import FFmpegWrapper
from app.infrastructure.ffprobe import FFprobeWrapper
from app.engines.faster_whisper import FasterWhisperEngine
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.error_handler import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode",
        extra={"status": "starting"},
    )

    # 1. System dependency checks (ffmpeg & ffprobe)
    ffmpeg = FFmpegWrapper()
    ffprobe = FFprobeWrapper()

    if not ffmpeg.is_available():
        if settings.APP_ENV == "production":
            logger.critical(
                f"Production startup failed: FFmpeg binary not found at '{settings.FFMPEG_BINARY}'"
            )
            raise RuntimeError(f"FFmpeg binary not found at '{settings.FFMPEG_BINARY}'")
        logger.warning(
            f"FFmpeg binary not detected at '{settings.FFMPEG_BINARY}'. "
            "Audio normalization will fail unless installed or configured via FFMPEG_BINARY."
        )
    else:
        logger.info("FFmpeg binary verified and ready.")

    if not ffprobe.is_available():
        if settings.APP_ENV == "production":
            logger.critical(
                f"Production startup failed: FFprobe binary not found at '{settings.FFPROBE_BINARY}'"
            )
            raise RuntimeError(f"FFprobe binary not found at '{settings.FFPROBE_BINARY}'")
        logger.warning(
            f"FFprobe binary not detected at '{settings.FFPROBE_BINARY}'. "
            "Audio probing will fail unless installed or configured via FFPROBE_BINARY."
        )
    else:
        logger.info("FFprobe binary verified and ready.")

    # 2. Initialize STT engine singleton
    logger.info(f"Initializing STT engine ({settings.STT_ENGINE})...")
    engine = FasterWhisperEngine()

    # Preload model in production or if explicitly configured
    if settings.APP_ENV not in ("test", "testing"):
        try:
            engine.load()
        except Exception as load_error:
            logger.critical(f"Critical failure loading STT engine: {load_error}")
            raise

    app.state.engine = engine
    app.state.ffmpeg = ffmpeg
    app.state.ffprobe = ffprobe

    logger.info(f"{settings.APP_NAME} is healthy and ready to accept requests.")
    yield

    # Graceful shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...", extra={"status": "stopping"})
    app.state.engine = None
    logger.info("Resources successfully released. Goodbye!")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.APP_ENV == "development" else None,
        redoc_url=None,
    )

    # Middlewares
    app.add_middleware(RequestIdMiddleware)

    # Exception Handlers
    register_exception_handlers(app)

    # Routers
    app.include_router(api_v1_router)

    return app


app = create_app()
