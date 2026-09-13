import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.core.config import settings
from app.infrastructure.ffprobe import AudioMetadata
from app.engines.base import EngineTranscriptionResult
from tests.fixtures.audio_fixtures import create_synthetic_wav_bytes


@pytest.fixture(autouse=True)
def setup_test_app_state():
    # Setup mock engine and wrappers in app.state for integration tests
    mock_engine = MagicMock()
    mock_engine.is_ready.return_value = True
    mock_engine.transcribe = AsyncMock(
        return_value=EngineTranscriptionResult(
            text="Kantor Wali Kota Medan berada di Jalan Kapten Maulana Lubis",
            language="id",
            language_probability=0.99,
            duration_seconds=3.2,
        )
    )

    mock_ffmpeg = MagicMock()
    mock_ffmpeg.is_available.return_value = True
    mock_ffmpeg.normalize_audio = AsyncMock(side_effect=lambda inp, out: out)

    mock_ffprobe = MagicMock()
    mock_ffprobe.is_available.return_value = True
    mock_ffprobe.probe = AsyncMock(
        return_value=AudioMetadata(
            format_name="wav",
            duration_seconds=3.2,
            codec_name="pcm_s16le",
        )
    )

    app.state.engine = mock_engine
    app.state.ffmpeg = mock_ffmpeg
    app.state.ffprobe = mock_ffprobe


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["engine"] == settings.STT_ENGINE
        assert data["model"] == settings.STT_MODEL
        assert data["device"] == settings.STT_DEVICE
        # Request-ID header check
        assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_transcriptions_endpoint_success():
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=3.2)
    files = {
        "file": ("voice.wav", wav_bytes, "audio/wav"),
    }
    data = {"language": "id"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/transcriptions", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert result["text"] == "Kantor Wali Kota Medan berada di Jalan Kapten Maulana Lubis"
        assert result["language"] == "id"
        assert result["duration_seconds"] == 3.2
        assert result["processing_time_ms"] >= 0


@pytest.mark.asyncio
async def test_transcriptions_endpoint_unauthorized(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "super-secret-key")
    wav_bytes = create_synthetic_wav_bytes(duration_seconds=1.0)
    files = {"file": ("voice.wav", wav_bytes, "audio/wav")}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Missing API Key
        resp_no_key = await client.post("/api/v1/transcriptions", files=files)
        assert resp_no_key.status_code == 401
        assert resp_no_key.json()["error"]["code"] == "INVALID_API_KEY"

        # 2. Wrong API Key
        resp_wrong_key = await client.post(
            "/api/v1/transcriptions",
            files=files,
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp_wrong_key.status_code == 401
        assert resp_wrong_key.json()["error"]["code"] == "INVALID_API_KEY"

        # 3. Correct API Key
        resp_ok = await client.post(
            "/api/v1/transcriptions",
            files=files,
            headers={"X-API-Key": "super-secret-key"},
        )
        assert resp_ok.status_code == 200
        assert resp_ok.json()["success"] is True


@pytest.mark.asyncio
async def test_transcriptions_endpoint_unsupported_format():
    files = {
        "file": ("document.pdf", b"%PDF-1.4 dummy", "application/pdf"),
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/transcriptions", files=files)
        assert response.status_code == 415
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "UNSUPPORTED_AUDIO_FORMAT"


@pytest.mark.asyncio
async def test_transcriptions_endpoint_empty_file():
    files = {
        "file": ("empty.ogg", b"", "audio/ogg"),
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/transcriptions", files=files)
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "EMPTY_AUDIO"
