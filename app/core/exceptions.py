from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404, code="not_found")


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403, code="forbidden")


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, status_code=409, code="conflict")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "code": "validation_error"},
        )
