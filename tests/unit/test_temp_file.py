import io
from pathlib import Path
import pytest
from fastapi import UploadFile

from app.infrastructure.temp_file import SafeTempFileManager, temporary_audio_workspace
from app.core.exceptions import AudioTooLargeException, EmptyAudioException


@pytest.mark.asyncio
async def test_save_upload_file_success(tmp_path: Path):
    manager = SafeTempFileManager(base_dir=str(tmp_path))
    content = b"RIFF dummy audio content for testing"
    upload_file = UploadFile(file=io.BytesIO(content), filename="test.ogg")

    temp_path = await manager.save_upload_file(upload_file, suffix=".ogg")
    try:
        assert temp_path.exists()
        assert temp_path.read_bytes() == content
    finally:
        manager.cleanup()
        assert not temp_path.exists()


@pytest.mark.asyncio
async def test_save_upload_file_empty_fails(tmp_path: Path):
    manager = SafeTempFileManager(base_dir=str(tmp_path))
    upload_file = UploadFile(file=io.BytesIO(b""), filename="empty.ogg")

    with pytest.raises(EmptyAudioException):
        await manager.save_upload_file(upload_file)

    manager.cleanup()


@pytest.mark.asyncio
async def test_save_upload_file_oversized_fails(tmp_path: Path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_AUDIO_SIZE_MB", 1)
    manager = SafeTempFileManager(base_dir=str(tmp_path))

    # Create content larger than 1MB
    large_content = b"x" * (1024 * 1024 + 100)
    upload_file = UploadFile(file=io.BytesIO(large_content), filename="large.ogg")

    with pytest.raises(AudioTooLargeException):
        await manager.save_upload_file(upload_file)

    # Verify no leaked files in tmp_path
    remaining = list(tmp_path.glob("*"))
    assert len(remaining) == 0


def test_temporary_audio_workspace_guaranteed_cleanup(tmp_path: Path):
    tracked_file: Path
    with temporary_audio_workspace(base_dir=str(tmp_path)) as workspace:
        tracked_file = workspace.create_temp_path(".wav")
        tracked_file.write_bytes(b"test data")
        assert tracked_file.exists()

    assert not tracked_file.exists()
