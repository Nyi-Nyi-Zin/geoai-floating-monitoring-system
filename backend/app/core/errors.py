from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


def _payload(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                _payload(
                    request,
                    code="validation_error",
                    message="The request contains invalid data.",
                    details=exc.errors(),
                )
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code", "http_error"))
            message = str(exc.detail.get("message", "Request failed."))
            details = exc.detail.get("details")
        else:
            code = "http_error"
            message = str(exc.detail)
            details = None
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(
                request,
                code=code,
                message=message,
                details=details,
            ),
            headers=exc.headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(
        request: Request,
        _exc: SQLAlchemyError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content=_payload(
                request,
                code="database_unavailable",
                message="The database operation could not be completed.",
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        _exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_payload(
                request,
                code="internal_error",
                message="An unexpected error occurred.",
            ),
        )
