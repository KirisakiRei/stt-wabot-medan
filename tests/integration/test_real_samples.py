from pathlib import Path
import pytest
from app.infrastructure.ffprobe import FFprobeWrapper
from app.infrastructure.ffmpeg import FFmpegWrapper
from app.engines.faster_whisper import FasterWhisperEngine

SAMPLE_FILES = [
    Path("sample/WhatsApp Ptt 2026-09-13 at 19.38.22.ogg"),
    Path("sample/WhatsApp Ptt 2026-09-13 at 19.37.34.ogg"),
    Path("sample/WhatsApp Ptt 2026-09-13 at 19.57.21.ogg"),
    Path("sample/WhatsApp Ptt 2026-09-13 at 19.57.38.ogg"),
    Path("sample/WhatsApp Ptt 2026-09-13 at 19.58.13.ogg"),
]


@pytest.mark.asyncio
async def test_real_sample_probing_and_transcription(tmp_path: Path):
    missing = [f for f in SAMPLE_FILES if not f.exists()]
    if missing:
        pytest.skip(f"Sample files missing: {missing}")

    probe = FFprobeWrapper()
    ffmpeg = FFmpegWrapper()
    engine = FasterWhisperEngine(model_size="base")
    engine.load()

    for idx, sample_file in enumerate(SAMPLE_FILES):
        metadata = await probe.probe(sample_file)
        assert metadata.format_name == "ogg"
        assert metadata.duration_seconds > 0.5

        normalized_wav = tmp_path / f"sample_{idx}_norm.wav"
        await ffmpeg.normalize_audio(sample_file, normalized_wav)
        assert normalized_wav.exists()

        result = await engine.transcribe(normalized_wav, language="id")
        assert len(result.text.strip()) > 0
        assert result.language == "id"
