from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.messages import resolve_message


class DomainError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message_key: str, params: dict | None = None):
        super().__init__(message_key)
        self.message_key = message_key
        self.params = params or {}


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(DomainError):
    status_code = status.HTTP_409_CONFLICT


class UnprocessableError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


def handle_api_exception(exc: Exception, context: dict) -> Response | None:
    if isinstance(exc, DomainError):
        body = {
            "code": exc.message_key,
            "detail": resolve_message(exc.message_key, exc.params),
            "params": {name: _to_json_value(value) for name, value in exc.params.items()},
        }
        return Response(body, status=exc.status_code)
    return exception_handler(exc, context)


def _to_json_value(value: object) -> object:
    if isinstance(value, Decimal | UUID):
        return str(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value
