from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "stt-service"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001

    # STT Engine
    STT_ENGINE: str = "faster_whisper"
    STT_MODEL: str = "models/small"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"
    STT_CPU_THREADS: int = 4
    STT_MAX_CONCURRENT_JOBS: int = 2
    HF_HUB_OFFLINE: int = 1
    TRANSFORMERS_OFFLINE: int = 1

    # Language & Audio Limits
    DEFAULT_LANGUAGE: str = "id"
    INITIAL_PROMPT: Optional[str] = (
        "Percakapan dan pengaduan layanan publik warga Kota Medan. "
        "Mencakup Kantor Wali Kota, Disdukcapil, Dishub, Dinkes, Disdik, DPMPTSP, Bapenda, Satpol PP, "
        "kecamatan, kelurahan, kepala dinas, camat, lurah, kepling, "
        "KTP elektronik, Kartu Keluarga KK, akta kelahiran, perizinan, dan pengaduan masyarakat."
    )
    MAX_AUDIO_SIZE_MB: int = 25
    MAX_AUDIO_DURATION_SECONDS: int = 300

    # Storage & Binaries
    TEMP_DIR: str = "/tmp/stt"
    FFMPEG_BINARY: str = "ffmpeg"
    FFPROBE_BINARY: str = "ffprobe"

    # Security
    API_KEY: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
