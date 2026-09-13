import time
from dataclasses import dataclass
from typing import Optional
from fastapi import UploadFile

from app.core.logging import logger
from app.engines.base import BaseSTTEngine
from app.infrastructure.temp_file import temporary_audio_workspace
from app.services.audio_service import AudioService


@dataclass(frozen=True)
class TranscriptionResponseDTO:
    success: bool
    text: str
    language: str
    duration_seconds: float
    processing_time_ms: int


class TranscriptionService:
    """
    Orchestrates the entire transcription lifecycle:
    1. Receive upload stream into safe temporary file
    2. Probe metadata and validate limits (duration, format)
    3. Normalize audio via FFmpeg
    4. Execute STT Engine inference
    5. Calculate metrics (processing time, duration)
    6. Ensure complete cleanup of all temporary files
    """

    def __init__(
        self,
        audio_service: AudioService,
        engine: BaseSTTEngine,
    ):
        self.audio_service = audio_service
        self.engine = engine

    async def process_transcription(
        self,
        file: UploadFile,
        language: Optional[str] = None,
        request_id: str = "unknown",
    ) -> TranscriptionResponseDTO:
        start_time = time.perf_counter()

        # Step 1: Validate contract before creating files
        suffix = self.audio_service.validate_upload_contract(file)

        with temporary_audio_workspace() as workspace:
            # Step 2: Stream upload to temporary file
            raw_audio_path = await workspace.save_upload_file(file, suffix=suffix)

            # Step 3: Probe metadata and validate duration
            metadata = await self.audio_service.inspect_and_validate(raw_audio_path)

            # Step 4: Normalize audio to WAV mono 16kHz
            normalized_path = workspace.create_temp_path(suffix=".wav")
            await self.audio_service.normalize(raw_audio_path, normalized_path)

            # Step 5: Execute STT Engine
            engine_result = await self.engine.transcribe(
                audio_path=normalized_path,
                language=language,
            )

            # Step 6: Compute processing metrics
            processing_time_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(
                "Audio transcription completed successfully",
                extra={
                    "request_id": request_id,
                    "audio_duration": metadata.duration_seconds,
                    "processing_ms": processing_time_ms,
                    "status": "success",
                },
            )

            return TranscriptionResponseDTO(
                success=True,
                text=engine_result.text,
                language=engine_result.language,
                duration_seconds=round(metadata.duration_seconds, 2),
                processing_time_ms=processing_time_ms,
            )
