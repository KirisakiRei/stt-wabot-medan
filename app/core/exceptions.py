from typing import Optional
from app.core.constants import ErrorCode


class STTException(Exception):
    def __init__(
        self,
        message: str,
        code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InvalidRequestException(STTException):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_REQUEST,
            status_code=400,
            details=details,
        )


class UnauthorizedException(STTException):
    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_API_KEY,
            status_code=401,
        )


class EmptyAudioException(STTException):
    def __init__(self, message: str = "Audio file is empty"):
        super().__init__(
            message=message,
            code=ErrorCode.EMPTY_AUDIO,
            status_code=400,
        )


class UnsupportedAudioFormatException(STTException):
    def __init__(self, message: str = "Unsupported audio format"):
        super().__init__(
            message=message,
            code=ErrorCode.UNSUPPORTED_AUDIO_FORMAT,
            status_code=415,
        )


class AudioTooLargeException(STTException):
    def __init__(self, message: str = "Audio file exceeds maximum allowed size"):
        super().__init__(
            message=message,
            code=ErrorCode.AUDIO_TOO_LARGE,
            status_code=413,
        )


class AudioTooLongException(STTException):
    def __init__(self, message: str = "Audio duration exceeds maximum allowed duration"):
        super().__init__(
            message=message,
            code=ErrorCode.AUDIO_TOO_LONG,
            status_code=400,
        )


class AudioDecodeException(STTException):
    def __init__(self, message: str = "Failed to decode or parse audio file"):
        super().__init__(
            message=message,
            code=ErrorCode.AUDIO_DECODE_FAILED,
            status_code=422,
        )


class ModelUnavailableException(STTException):
    def __init__(self, message: str = "STT model is currently unavailable"):
        super().__init__(
            message=message,
            code=ErrorCode.MODEL_UNAVAILABLE,
            status_code=503,
        )


class TranscriptionFailedException(STTException):
    def __init__(self, message: str = "Transcription process failed"):
        super().__init__(
            message=message,
            code=ErrorCode.TRANSCRIPTION_FAILED,
            status_code=500,
        )


class ConcurrencyLimitExceededException(STTException):
    def __init__(self, message: str = "Server is busy processing other transcription jobs"):
        super().__init__(
            message=message,
            code=ErrorCode.CONCURRENCY_LIMIT_EXCEEDED,
            status_code=503,
        )
