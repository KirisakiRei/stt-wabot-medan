import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from app.infrastructure.ffprobe import FFprobeWrapper
from app.infrastructure.ffmpeg import FFmpegWrapper
from app.core.exceptions import AudioDecodeException, STTException


@pytest.mark.asyncio
async def test_ffprobe_success(tmp_path: Path):
    wrapper = FFprobeWrapper(binary_path="ffprobe")
    dummy_file = tmp_path / "sample.ogg"
    dummy_file.write_bytes(b"dummy")

    mock_json = {
        "format": {
            "format_name": "ogg",
            "duration": "5.43",
            "bit_rate": "64000",
        },
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "opus",
                "sample_rate": "48000",
                "channels": 1,
            }
        ],
    }

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(return_value=(json.dumps(mock_json).encode(), b""))

    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch.object(wrapper, "is_available", return_value=True), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        metadata = await wrapper.probe(dummy_file)
        assert metadata.format_name == "ogg"
        assert metadata.duration_seconds == 5.43
        assert metadata.codec_name == "opus"
        assert metadata.channels == 1
        assert metadata.sample_rate == 48000


@pytest.mark.asyncio
async def test_ffprobe_missing_binary(tmp_path: Path):
    wrapper = FFprobeWrapper(binary_path="nonexistent_ffprobe")
    dummy_file = tmp_path / "sample.ogg"
    dummy_file.write_bytes(b"dummy")

    with patch("shutil.which", return_value=None), \
         patch.dict("sys.modules", {"av": None}):
        with pytest.raises(STTException) as exc_info:
            await wrapper.probe(dummy_file)
        assert exc_info.value.code == "INTERNAL_ERROR"


@pytest.mark.asyncio
async def test_ffprobe_corrupted_file(tmp_path: Path):
    wrapper = FFprobeWrapper(binary_path="ffprobe")
    dummy_file = tmp_path / "corrupted.ogg"
    dummy_file.write_bytes(b"corrupted")

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.communicate = AsyncMock(return_value=(b"", b"Invalid data found when processing input"))

    with patch("shutil.which", return_value="/usr/bin/ffprobe"), \
         patch.object(wrapper, "is_available", return_value=True), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(AudioDecodeException):
            await wrapper.probe(dummy_file)


@pytest.mark.asyncio
async def test_ffmpeg_normalize_success(tmp_path: Path):
    wrapper = FFmpegWrapper(binary_path="ffmpeg")
    input_file = tmp_path / "input.ogg"
    input_file.write_bytes(b"input audio")
    output_file = tmp_path / "output.wav"

    async def fake_communicate():
        output_file.write_bytes(b"normalized wav audio")
        return (b"", b"")

    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.communicate = AsyncMock(side_effect=fake_communicate)

    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch.object(wrapper, "is_available", return_value=True), \
         patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        res = await wrapper.normalize_audio(input_file, output_file)
        assert res == output_file
        assert output_file.exists()
        assert output_file.read_bytes() == b"normalized wav audio"
