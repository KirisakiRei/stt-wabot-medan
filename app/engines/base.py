from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class EngineTranscriptionResult:
    text: str
    language: str
    language_probability: float
    duration_seconds: float


class BaseSTTEngine(ABC):
    """Abstract Base Class for Speech-To-Text engines."""

    @abstractmethod
    def load(self) -> None:
        """Loads the model into memory during startup."""
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> EngineTranscriptionResult:
        """
        Transcribes the normalized audio file asynchronously.
        Must handle threadpool offloading and concurrency limits.
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns True if the engine model is loaded and ready."""
        pass
