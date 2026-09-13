from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.api.deps import (
    verify_api_key,
    get_stt_engine,
    get_ffmpeg_wrapper,
    get_ffprobe_wrapper,
)
from app.engines.base import BaseSTTEngine
from app.infrastructure.ffmpeg import FFmpegWrapper
from app.infrastructure.ffprobe import FFprobeWrapper
from app.schemas.transcription import TranscriptionSuccessResponse
from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService

router = APIRouter()


@router.post(
    "/transcriptions",
    response_model=TranscriptionSuccessResponse,
    dependencies=[Depends(verify_api_key)],
    summary="Transcribe Audio File",
    description="Accepts an audio file upload via multipart/form-data, normalizes it, and returns the transcription result.",
)
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio file to transcribe (.ogg, .opus, .mp3, .wav, .m4a, etc.)"),
    language: Optional[str] = Form(None, description="Optional language code (e.g. 'id'). Defaults to server setting."),
    engine: BaseSTTEngine = Depends(get_stt_engine),
    ffmpeg: FFmpegWrapper = Depends(get_ffmpeg_wrapper),
    ffprobe: FFprobeWrapper = Depends(get_ffprobe_wrapper),
) -> TranscriptionSuccessResponse:
    request_id = getattr(request.state, "request_id", "unknown")

    audio_service = AudioService(ffmpeg=ffmpeg, ffprobe=ffprobe)
    transcription_service = TranscriptionService(audio_service=audio_service, engine=engine)

    transcription_dto = await transcription_service.process_transcription(
        file=file,
        language=language,
        request_id=request_id,
    )

    return TranscriptionSuccessResponse(
        success=transcription_dto.success,
        text=transcription_dto.text,
        language=transcription_dto.language,
        duration_seconds=transcription_dto.duration_seconds,
        processing_time_ms=transcription_dto.processing_time_ms,
    )
