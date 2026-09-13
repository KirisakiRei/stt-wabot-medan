import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import AudioDecodeException, STTException
from app.core.constants import ErrorCode
from app.core.logging import logger


@dataclass(frozen=True)
class AudioMetadata:
    format_name: str
    duration_seconds: float
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec_name: Optional[str] = None
    bit_rate: Optional[int] = None


class FFprobeWrapper:
    """Subprocess wrapper around ffprobe to safely extract audio metadata with PyAV fallback."""

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or settings.FFPROBE_BINARY

    def is_available(self) -> bool:
        """Checks if ffprobe is installed or PyAV is available as fallback."""
        if shutil.which(self.binary_path) is not None:
            return True
        try:
            import av
            return True
        except ImportError:
            return False

    def _probe_with_pyav(self, file_path: Path) -> AudioMetadata:
        """Fallback probe using PyAV (bundled with faster-whisper) when binary is absent."""
        try:
            import av
            with av.open(str(file_path)) as container:
                audio_streams = [s for s in container.streams if s.type == "audio"]
                if not audio_streams:
                    raise AudioDecodeException("No audio stream found in the uploaded file")

                stream = audio_streams[0]
                duration_sec: Optional[float] = None

                if stream.duration is not None and stream.time_base is not None:
                    duration_sec = float(stream.duration * stream.time_base)
                elif container.duration is not None:
                    duration_sec = float(container.duration / av.time.AV_TIME_BASE)

                if duration_sec is None:
                    raise AudioDecodeException("Unable to determine audio duration")

                sample_rate = getattr(stream, "rate", None)
                channels = getattr(stream, "channels", None)
                codec_name = getattr(stream.codec_context, "name", None)
                bit_rate = getattr(container, "bit_rate", None)

                return AudioMetadata(
                    format_name=container.format.name,
                    duration_seconds=duration_sec,
                    sample_rate=sample_rate,
                    channels=channels,
                    codec_name=codec_name,
                    bit_rate=bit_rate,
                )
        except AudioDecodeException:
            raise
        except Exception as e:
            logger.warning(f"PyAV probing failed on {file_path}: {e}")
            raise AudioDecodeException("Cannot parse audio file. File may be corrupt or invalid.")

    async def probe(self, file_path: Path, timeout: float = 10.0) -> AudioMetadata:
        """
        Runs ffprobe on the given file path and returns structured AudioMetadata.
        Falls back to PyAV if ffprobe binary is not present in the environment.
        """
        has_binary = shutil.which(self.binary_path) is not None

        if not has_binary:
            try:
                import av
                return await asyncio.to_thread(self._probe_with_pyav, file_path)
            except ImportError:
                raise STTException(
                    message=f"Neither ffprobe binary at '{self.binary_path}' nor PyAV is available",
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                )

        cmd = [
            self.binary_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "-select_streams",
            "a",  # Only audio streams
            str(file_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            raise AudioDecodeException("ffprobe operation timed out while inspecting audio")
        except Exception as e:
            logger.error(f"Failed to execute ffprobe: {e}", exc_info=True)
            raise AudioDecodeException(f"Failed to execute ffprobe: {str(e)}")

        if process.returncode != 0:
            error_message = stderr.decode("utf-8", errors="replace").strip()
            logger.warning(f"ffprobe failed on {file_path}: {error_message}")
            raise AudioDecodeException("Cannot parse audio file. File may be corrupt or invalid.")

        try:
            probe_data = json.loads(stdout.decode("utf-8"))
            format_info = probe_data.get("format", {})
            streams = probe_data.get("streams", [])

            if not streams:
                raise AudioDecodeException("No audio stream found in the uploaded file")

            audio_stream = streams[0]
            duration_str = format_info.get("duration") or audio_stream.get("duration")
            if not duration_str:
                raise AudioDecodeException("Unable to determine audio duration")

            duration = float(duration_str)
            sample_rate = int(audio_stream["sample_rate"]) if "sample_rate" in audio_stream else None
            channels = int(audio_stream["channels"]) if "channels" in audio_stream else None
            codec_name = audio_stream.get("codec_name")
            bit_rate = int(format_info["bit_rate"]) if "bit_rate" in format_info else None

            return AudioMetadata(
                format_name=format_info.get("format_name", "unknown"),
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
                codec_name=codec_name,
                bit_rate=bit_rate,
            )
        except (ValueError, KeyError, json.JSONDecodeError) as parsing_error:
            logger.warning(f"Failed to parse ffprobe JSON output: {parsing_error}")
            raise AudioDecodeException("Invalid audio metadata received from ffprobe")
