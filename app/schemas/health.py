from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", json_schema_extra={"example": "ok"})
    engine: Optional[str] = Field(default=None, json_schema_extra={"example": "faster_whisper"})
    model: Optional[str] = Field(default=None, json_schema_extra={"example": "small"})
    device: Optional[str] = Field(default=None, json_schema_extra={"example": "cpu"})
