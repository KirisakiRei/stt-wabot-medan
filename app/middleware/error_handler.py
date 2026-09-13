from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import STTException
from app.core.constants import ErrorCode
from app.core.logging import logger


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(STTException)
    async def stt_exception_handler(request: Request, exception: STTException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            f"Business exception occurred: {exception.message}",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": exception.status_code,
                "error_code": exception.code,
                "status": "error",
            },
        )
        return JSONResponse(
            status_code=exception.status_code,
            content={
                "success": False,
                "error": {
                    "code": exception.code,
                    "message": exception.message,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            "Request validation failed",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": 422,
                "error_code": ErrorCode.INVALID_REQUEST,
                "status": "error",
            },
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": ErrorCode.INVALID_REQUEST,
                    "message": "Invalid request parameters or payload",
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exception: StarletteHTTPException
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        error_code = ErrorCode.INVALID_REQUEST if exception.status_code < 500 else ErrorCode.INTERNAL_ERROR
        logger.warning(
            f"HTTP exception: {exception.detail}",
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": exception.status_code,
                "error_code": error_code,
                "status": "error",
            },
        )
        return JSONResponse(
            status_code=exception.status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": str(exception.detail),
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exception: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "Unhandled internal server error",
            exc_info=True,
            extra={
                "request_id": request_id,
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": 500,
                "error_code": ErrorCode.INTERNAL_ERROR,
                "status": "error",
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "An unexpected error occurred. Please try again later.",
                },
            },
        )
