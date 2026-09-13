import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.engines.faster_whisper import FasterWhisperEngine
from app.core.exceptions import ModelUnavailableException, TranscriptionFailedException


@pytest.mark.asyncio
async def test_faster_whisper_engine_transcribe_not_ready():
    engine = FasterWhisperEngine()
    dummy_path = Path("fake.wav")

    with pytest.raises(ModelUnavailableException):
        await engine.transcribe(dummy_path)


@pytest.mark.asyncio
async def test_faster_whisper_engine_transcribe_success(tmp_path: Path):
    engine = FasterWhisperEngine(max_concurrent_jobs=2)
    dummy_path = tmp_path / "normalized.wav"
    dummy_path.write_bytes(b"dummy wav data")

    mock_segment_1 = MagicMock()
    mock_segment_1.text = " Halo selamat"
    mock_segment_2 = MagicMock()
    mock_segment_2.text = " pagi kota Medan"

    mock_info = MagicMock()
    mock_info.language = "id"
    mock_info.language_probability = 0.98
    mock_info.duration = 3.5

    mock_whisper_model = MagicMock()
    mock_whisper_model.transcribe.return_value = (
        [mock_segment_1, mock_segment_2],
        mock_info,
    )

    with patch("app.engines.faster_whisper.WhisperModel", return_value=mock_whisper_model):
        engine.load()
        assert engine.is_ready()

        result = await engine.transcribe(dummy_path, language="id")

        assert result.text == "Halo selamat pagi kota Medan"
        assert result.language == "id"
        assert result.language_probability == 0.98
        assert result.duration_seconds == 3.5


@pytest.mark.asyncio
async def test_faster_whisper_engine_inference_failure(tmp_path: Path):
    engine = FasterWhisperEngine()
    dummy_path = tmp_path / "broken.wav"
    dummy_path.write_bytes(b"broken")

    mock_whisper_model = MagicMock()
    mock_whisper_model.transcribe.side_effect = RuntimeError("Inference kernel crashed")

    with patch("app.engines.faster_whisper.WhisperModel", return_value=mock_whisper_model):
        engine.load()
        with pytest.raises(TranscriptionFailedException):
            await engine.transcribe(dummy_path)
