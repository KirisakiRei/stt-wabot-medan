import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Optional, Union
from app.core.config import settings

LogPrimitive = Union[str, int, float, bool, None]


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, LogPrimitive] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject context from extra fields if present
        for field_name in (
            "request_id",
            "endpoint",
            "audio_duration",
            "processing_ms",
            "status",
            "error_code",
            "method",
            "status_code",
        ):
            if hasattr(record, field_name):
                field_value = getattr(record, field_name)
                log_entry[field_name] = field_value

        if record.exc_info and record.levelname in ("ERROR", "CRITICAL"):
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(name: str = "stt_service") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logger()
