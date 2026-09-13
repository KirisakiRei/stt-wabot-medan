from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from app.core.config import settings
from app.core.constants import SUPPORTED_EXTENSIONS, SUPPORTED_MIME_TYPES
from app.core.exceptions import (
    UnsupportedAudioFormatException,
    AudioTooLongException,
)
from app.infrastructure.ffmpeg import FFmpegWrapper
from app.infrastructure.ffprobe import FFprobeWrapper, AudioMetadata


class AudioService:
    """Handles audio validation, metadata inspection, and normalization."""

    def __init__(
        self,
        ffmpeg: Optional[FFmpegWrapper] = None,
        ffprobe: Optional[FFprobeWrapper] = None,
    ):
        self.ffmpeg = ffmpeg or FFmpegWrapper()
        self.ffprobe = ffprobe or FFprobeWrapper()

    def validate_upload_contract(self, upload_file: UploadFile) -> str:
        """
        Validates file extension and content type before reading the stream.
        Returns the resolved file extension suffix.
        """
        filename = upload_file.filename or ""
        file_extension = Path(filename).suffix.lower()

        # If extension not found or not in allowed list, check content_type
        content_type = (upload_file.content_type or "").lower()

        if file_extension not in SUPPORTED_EXTENSIONS and content_type not in SUPPORTED_MIME_TYPES:
            raise UnsupportedAudioFormatException(
                f"Unsupported audio format. Extension: '{file_extension}', Content-Type: '{content_type}'"
            )

        return file_extension if file_extension in SUPPORTED_EXTENSIONS else ".audio"

    async def inspect_and_validate(self, audio_path: Path) -> AudioMetadata:
        """
        Probes audio metadata via ffprobe and enforces business rules:
        - Must contain an audio stream
        - Duration must not exceed MAX_AUDIO_DURATION_SECONDS
        """
        metadata = await self.ffprobe.probe(audio_path)

        if metadata.duration_seconds > settings.MAX_AUDIO_DURATION_SECONDS:
            raise AudioTooLongException(
                f"Audio duration ({metadata.duration_seconds:.2f}s) exceeds "
                f"maximum limit of {settings.MAX_AUDIO_DURATION_SECONDS}s"
            )

        return metadata

    async def normalize(self, input_path: Path, output_path: Path) -> Path:
        """Normalizes audio into standardized 16kHz mono WAV format."""
        return await self.ffmpeg.normalize_audio(input_path, output_path)
