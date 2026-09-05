from enum import StrEnum

from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorResponse


class ErrorCode(StrEnum):
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"


class AppError(Exception):
    def __init__(self, *, status_code: int, code: ErrorCode, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def _error_response(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    payload = ErrorResponse(error=message, code=code, details=None)
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_exception(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(FastAPIHTTPException)
    async def handle_http_exception(_: Request, exc: FastAPIHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            code = ErrorCode.UNAUTHORIZED
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            code = ErrorCode.FORBIDDEN
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            code = ErrorCode.NOT_FOUND
        elif exc.status_code == status.HTTP_409_CONFLICT:
            code = ErrorCode.CONFLICT
        else:
            code = ErrorCode.INTERNAL_ERROR
        return _error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.VALIDATION_ERROR,
            str(exc),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred.",
        )
