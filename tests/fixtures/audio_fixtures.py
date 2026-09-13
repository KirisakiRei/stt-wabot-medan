import wave
import struct
import io


def create_synthetic_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generates valid in-memory PCM 16-bit Mono WAV bytes."""
    num_samples = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Generate simple silence / DC offset frames
        frames = struct.pack(f"<{num_samples}h", *([0] * num_samples))
        wav_file.writeframes(frames)

    return buffer.getvalue()


def create_synthetic_ogg_bytes() -> bytes:
    """Generates mock Ogg container bytes header."""
    return b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x01\x1e" + (b"\x00" * 30)
