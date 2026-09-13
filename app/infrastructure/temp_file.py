import os
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import AudioTooLargeException, EmptyAudioException
from app.core.logging import logger


class SafeTempFileManager:
    """Manages temporary files for audio processing with guaranteed cleanup."""

    def __init__(self, base_dir: str = settings.TEMP_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._tracked_paths: List[Path] = []

    def create_temp_path(self, suffix: str = ".tmp") -> Path:
        """Generates a unique path within the temporary directory."""
        filename = f"{uuid.uuid4().hex}{suffix}"
        path = self.base_dir / filename
        self._tracked_paths.append(path)
        return path

    async def save_upload_file(
        self, upload_file: UploadFile, suffix: str = ".audio"
    ) -> Path:
        """
        Streams an UploadFile to a unique temporary file without loading
        the entire content into memory at once.
        """
        max_bytes = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
        temp_path = self.create_temp_path(suffix=suffix)

        bytes_written = 0
        chunk_size = 1024 * 64  # 64 KB chunks

        try:
            with open(temp_path, "wb") as destination:
                while chunk := await upload_file.read(chunk_size):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise AudioTooLargeException(
                            f"Audio size exceeds {settings.MAX_AUDIO_SIZE_MB}MB limit"
                        )
                    destination.write(chunk)

            if bytes_written == 0:
                raise EmptyAudioException("Uploaded audio file is empty (0 bytes)")

            return temp_path
        except Exception:
            # If upload fails or validation aborts, clean up immediately
            self.remove_file(temp_path)
            raise

    def remove_file(self, path: Path) -> None:
        """Safely removes a single file if it exists."""
        try:
            if path.exists():
                os.remove(path)
            if path in self._tracked_paths:
                self._tracked_paths.remove(path)
        except OSError as e:
            logger.warning(
                f"Failed to delete temp file {path}: {e}",
                extra={"status": "warning", "file_path": str(path)},
            )

    def cleanup(self) -> None:
        """Cleans up all tracked files created during this manager instance's lifecycle."""
        for path in list(self._tracked_paths):
            self.remove_file(path)


@contextmanager
def temporary_audio_workspace(base_dir: str = settings.TEMP_DIR) -> Generator[SafeTempFileManager, None, None]:
    """
    Context manager that provides a SafeTempFileManager instance and guarantees
    all created files are cleaned up upon exiting the context.
    """
    manager = SafeTempFileManager(base_dir=base_dir)
    try:
        yield manager
    finally:
        manager.cleanup()
