from pydantic import BaseModel, Field


class TranscriptionSuccessResponse(BaseModel):
    success: bool = Field(default=True, json_schema_extra={"example": True})
    text: str = Field(
        ...,
        description="The transcribed text result",
        json_schema_extra={"example": "Bang saya mau tanya lokasi kantor wali kota"},
    )
    language: str = Field(
        ...,
        description="Detected or requested language code",
        json_schema_extra={"example": "id"},
    )
    duration_seconds: float = Field(
        ...,
        description="Duration of the audio file in seconds",
        json_schema_extra={"example": 5.43},
    )
    processing_time_ms: int = Field(
        ...,
        description="Time taken to process the transcription in milliseconds",
        json_schema_extra={"example": 680},
    )
