class ErrorCode:
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_API_KEY = "INVALID_API_KEY"
    EMPTY_AUDIO = "EMPTY_AUDIO"
    UNSUPPORTED_AUDIO_FORMAT = "UNSUPPORTED_AUDIO_FORMAT"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    AUDIO_TOO_LONG = "AUDIO_TOO_LONG"
    AUDIO_DECODE_FAILED = "AUDIO_DECODE_FAILED"
    TRANSCRIPTION_FAILED = "TRANSCRIPTION_FAILED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    CONCURRENCY_LIMIT_EXCEEDED = "CONCURRENCY_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


SUPPORTED_MIME_TYPES = {
    "audio/ogg",
    "audio/opus",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/webm",
}

SUPPORTED_EXTENSIONS = {
    ".ogg",
    ".opus",
    ".mp3",
    ".m4a",
    ".wav",
    ".webm",
    ".mp4",
}
