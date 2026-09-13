import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import UploadFile

from app.api.deps import verify_api_key
from app.services.audio_service import AudioService
from app.services.transcription_service import TranscriptionService
from app.infrastructure.ffprobe import AudioMetadata
from app.engines.base import EngineTranscriptionResult
from app.core.exceptions import (
    UnauthorizedException,
    UnsupportedAudioFormatException,
    AudioTooLongException,
)


# --- Test Authentication Dependency ---

@pytest.mark.asyncio
async def test_verify_api_key_when_disabled(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "API_KEY", None)

    # Should not raise any exception when API_KEY is unset
    await verify_api_key(x_api_key=None)
    await verify_api_key(x_api_key="random-key")


@pytest.mark.asyncio
async def test_verify_api_key_when_enabled(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "API_KEY", "secret-test-key")

    # Missing header
    with pytest.raises(UnauthorizedException):
        await verify_api_key(x_api_key=None)

    # Wrong key
    with pytest.raises(UnauthorizedException):
        await verify_api_key(x_api_key="wrong-key")

    # Correct key
    await verify_api_key(x_api_key="secret-test-key")


# --- Test AudioService ---

def test_audio_service_validation_success():
    service = AudioService()
    file = UploadFile(file=io.BytesIO(b"audio"), filename="voice.ogg", headers={"content-type": "audio/ogg"})
    suffix = service.validate_upload_contract(file)
    assert suffix == ".ogg"


def test_audio_service_unsupported_format():
    service = AudioService()
    file = UploadFile(file=io.BytesIO(b"text"), filename="document.txt", headers={"content-type": "text/plain"})
    with pytest.raises(UnsupportedAudioFormatException):
        service.validate_upload_contract(file)


@pytest.mark.asyncio
async def test_audio_service_duration_too_long(tmp_path: Path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_AUDIO_DURATION_SECONDS", 10)

    mock_ffprobe = MagicMock()
    mock_ffprobe.probe = AsyncMock(
        return_value=AudioMetadata(
            format_name="ogg",
            duration_seconds=15.0,  # exceeds 10s
        )
    )

    service = AudioService(ffprobe=mock_ffprobe)
    sample_path = tmp_path / "sample.ogg"
    sample_path.write_bytes(b"dummy")

    with pytest.raises(AudioTooLongException):
        await service.inspect_and_validate(sample_path)


# --- Test TranscriptionService Orchestration ---

@pytest.mark.asyncio
async def test_transcription_service_orchestration(tmp_path: Path):
    mock_ffmpeg = MagicMock()
    mock_ffmpeg.normalize_audio = AsyncMock(side_effect=lambda inp, out: out)

    mock_ffprobe = MagicMock()
    mock_ffprobe.probe = AsyncMock(
        return_value=AudioMetadata(
            format_name="ogg",
            duration_seconds=4.5,
            codec_name="opus",
        )
    )

    mock_engine = MagicMock()
    mock_engine.transcribe = AsyncMock(
        return_value=EngineTranscriptionResult(
            text="Bang saya mau tanya lokasi kantor wali kota",
            language="id",
            language_probability=0.99,
            duration_seconds=4.5,
        )
    )

    audio_service = AudioService(ffmpeg=mock_ffmpeg, ffprobe=mock_ffprobe)
    transcription_service = TranscriptionService(
        audio_service=audio_service,
        engine=mock_engine,
    )

    upload_file = UploadFile(
        file=io.BytesIO(b"fake audio stream content"),
        filename="voice.ogg",
        headers={"content-type": "audio/ogg"},
    )

    result = await transcription_service.process_transcription(
        file=upload_file,
        language="id",
        request_id="req-12345",
    )

    assert result.success is True
    assert result.text == "Bang saya mau tanya lokasi kantor wali kota"
    assert result.language == "id"
    assert result.duration_seconds == 4.5
    assert result.processing_time_ms >= 0
    mock_engine.transcribe.assert_awaited_once()
    mock_ffmpeg.normalize_audio.assert_awaited_once()
