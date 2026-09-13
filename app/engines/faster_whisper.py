import asyncio
from pathlib import Path
from typing import Optional
from faster_whisper import WhisperModel

from app.core.config import settings
from app.core.exceptions import (
    ModelUnavailableException,
    TranscriptionFailedException,
    ConcurrencyLimitExceededException,
)
from app.core.logging import logger
from app.engines.base import BaseSTTEngine, EngineTranscriptionResult


class FasterWhisperEngine(BaseSTTEngine):
    """
    Faster-Whisper implementation of BaseSTTEngine.
    Runs inference via CTranslate2 on CPU (int8) with concurrency control.
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        cpu_threads: Optional[int] = None,
        max_concurrent_jobs: Optional[int] = None,
    ):
        self.model_size = model_size or settings.STT_MODEL
        self.device = device or settings.STT_DEVICE
        self.compute_type = compute_type or settings.STT_COMPUTE_TYPE
        self.cpu_threads = cpu_threads or settings.STT_CPU_THREADS
        self.max_concurrent_jobs = max_concurrent_jobs or settings.STT_MAX_CONCURRENT_JOBS

        self._model: Optional[WhisperModel] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    def load(self) -> None:
        """Initializes and loads the Whisper model into memory."""
        try:
            # Resolve model path: check local directory first, then fallback to model name
            model_target = self.model_size
            local_path = Path(self.model_size)
            if local_path.exists() and (local_path / "model.bin").exists():
                model_target = str(local_path.resolve())
                logger.info(
                    f"Resolved local offline model path: '{model_target}'",
                    extra={"status": "local_model_found"},
                )

            logger.info(
                f"Loading faster-whisper model '{model_target}' "
                f"on {self.device} with compute_type='{self.compute_type}', "
                f"cpu_threads={self.cpu_threads}...",
                extra={"status": "loading_model"},
            )
            self._model = WhisperModel(
                model_size_or_path=model_target,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            )
            self._semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
            logger.info(
                f"faster-whisper model '{self.model_size}' loaded successfully",
                extra={"status": "model_ready"},
            )
        except Exception as e:
            logger.critical(f"Failed to load faster-whisper model: {e}", exc_info=True)
            raise ModelUnavailableException(f"Failed to initialize faster-whisper model: {str(e)}")

    def is_ready(self) -> bool:
        return self._model is not None

    def _sync_transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> EngineTranscriptionResult:
        """Synchronous CPU-bound transcription called in separate thread."""
        if not self._model:
            raise ModelUnavailableException("STT model has not been loaded")

        target_lang = language or settings.DEFAULT_LANGUAGE

        try:
            segments, info = self._model.transcribe(
                audio=str(audio_path),
                language=target_lang,
                beam_size=5,
                vad_filter=True,
                initial_prompt=settings.INITIAL_PROMPT,
            )

            # Consume the segments generator
            text_segments = [seg.text.strip() for seg in segments]
            full_text = " ".join(text_segments).strip()

            return EngineTranscriptionResult(
                text=full_text,
                language=info.language,
                language_probability=info.language_probability,
                duration_seconds=info.duration,
            )
        except Exception as e:
            logger.error(f"Inference error during transcription: {e}", exc_info=True)
            raise TranscriptionFailedException(f"Inference execution failed: {str(e)}")

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> EngineTranscriptionResult:
        """
        Asynchronously handles transcription requests within concurrency limits.
        """
        if not self.is_ready():
            raise ModelUnavailableException("STT model is not ready")

        if not self._semaphore:
            self._semaphore = asyncio.Semaphore(self.max_concurrent_jobs)

        try:
            # Acquire semaphore to avoid CPU starvation
            async with self._semaphore:
                return await asyncio.to_thread(
                    self._sync_transcribe,
                    audio_path=audio_path,
                    language=language,
                )
        except (ModelUnavailableException, TranscriptionFailedException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error during transcription scheduling: {e}", exc_info=True)
            raise TranscriptionFailedException(str(e))
