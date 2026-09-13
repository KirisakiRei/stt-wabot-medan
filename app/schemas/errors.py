from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(
        ...,
        description="Machine-readable error code",
        json_schema_extra={"example": "UNSUPPORTED_AUDIO_FORMAT"},
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
        json_schema_extra={"example": "Unsupported audio format"},
    )


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, json_schema_extra={"example": False})
    error: ErrorDetail
