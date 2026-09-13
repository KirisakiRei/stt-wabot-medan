import asyncio
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import AudioDecodeException, STTException
from app.core.constants import ErrorCode
from app.core.logging import logger


class FFmpegWrapper:
    """
    Subprocess wrapper around ffmpeg to safely normalize audio into standard format:
    WAV, Mono (1 channel), 16000 Hz, PCM 16-bit little-endian (pcm_s16le).
    Includes PyAV fallback when ffmpeg binary is not installed locally.
    """

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or settings.FFMPEG_BINARY

    def is_available(self) -> bool:
        """Checks if ffmpeg is installed or PyAV is available as fallback."""
        if shutil.which(self.binary_path) is not None:
            return True
        try:
            import av
            return True
        except ImportError:
            return False

    def _normalize_with_pyav(self, input_path: Path, output_path: Path) -> Path:
        """Fallback audio normalizer using PyAV (C-level FFmpeg bindings)."""
        try:
            import av
            in_container = av.open(str(input_path))
            audio_streams = [s for s in in_container.streams if s.type == "audio"]
            if not audio_streams:
                in_container.close()
                raise AudioDecodeException("No audio stream found in the input file")

            in_stream = audio_streams[0]
            out_container = av.open(str(output_path), mode="w", format="wav")
            out_stream = out_container.add_stream("pcm_s16le", rate=16000, layout="mono")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)

            for frame in in_container.decode(in_stream):
                for resampled_frame in resampler.resample(frame):
                    for packet in out_stream.encode(resampled_frame):
                        out_container.mux(packet)

            # Flush remaining buffered packets
            for packet in out_stream.encode(None):
                out_container.mux(packet)

            out_container.close()
            in_container.close()

            if not output_path.exists() or output_path.stat().st_size == 0:
                raise AudioDecodeException("Audio conversion produced an empty output file")

            return output_path
        except AudioDecodeException:
            raise
        except Exception as conversion_error:
            logger.error(f"PyAV audio normalization failed: {conversion_error}", exc_info=True)
            raise AudioDecodeException("Audio conversion failed. File may have unsupported codec or be corrupted.")

    async def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        timeout: float = 30.0,
    ) -> Path:
        """
        Converts any supported input audio into 16kHz mono 16-bit PCM WAV.
        Uses argument list execution to prevent command injection.
        Falls back to PyAV if ffmpeg binary is not present in the environment.
        """
        has_binary = shutil.which(self.binary_path) is not None

        if not has_binary:
            try:
                import av
                return await asyncio.to_thread(self._normalize_with_pyav, input_path, output_path)
            except ImportError:
                raise STTException(
                    message=f"Neither ffmpeg binary at '{self.binary_path}' nor PyAV is available",
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                )

        cmd = [
            self.binary_path,
            "-y",  # Overwrite output without asking
            "-i",
            str(input_path),
            "-vn",  # Discard video if any
            "-ac",
            "1",  # Force 1 channel (mono)
            "-ar",
            "16000",  # Force 16,000 Hz sample rate
            "-c:a",
            "pcm_s16le",  # 16-bit PCM audio codec
            str(output_path),
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
            raise AudioDecodeException("ffmpeg normalization timed out")
        except Exception as execution_error:
            logger.error(f"Failed to execute ffmpeg: {execution_error}", exc_info=True)
            raise AudioDecodeException(f"Failed to execute ffmpeg: {str(execution_error)}")

        if process.returncode != 0:
            error_message = stderr.decode("utf-8", errors="replace").strip()
            logger.warning(f"ffmpeg conversion failed for {input_path}: {error_message}")
            raise AudioDecodeException("Audio conversion failed. File may have unsupported codec or be corrupted.")

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise AudioDecodeException("Audio conversion produced an empty or missing output file")

        return output_path
