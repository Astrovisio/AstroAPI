import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from api.exceptions import APIException

logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions"""
    logger.error(f"API Exception: {exc.detail}", extra={"context": exc.context})

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "context": exc.context,
            }
        },
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """Handle database errors"""
    logger.error(f"Database error: {str(exc)}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "DATABASE_ERROR",
                "message": "An internal database error occurred",
                "context": {},
            }
        },
    )


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors (including custom validators)"""
    # Check if it's one of our custom validation errors
    for error in exc.errors():
        if error.get("type") == "value_error" and hasattr(
            error.get("ctx", {}), "error_code"
        ):
            # This is one of our custom APIExceptions wrapped in ValidationError
            custom_exc = error["ctx"]
            return await api_exception_handler(request, custom_exc)

    # Default Pydantic validation error handling
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "context": {"details": exc.errors()},
            }
        },
    )
