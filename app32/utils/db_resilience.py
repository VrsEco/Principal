from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.exc import OperationalError

from models import db

T = TypeVar("T")

_DISCONNECT_MARKERS = (
    "ssl error: decryption failed or bad record mac",
    "server closed the connection unexpectedly",
    "could not receive data from server",
    "connection not open",
)


def is_transient_disconnect_error(exc: OperationalError) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _DISCONNECT_MARKERS)


def run_with_disconnect_retry(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except OperationalError as exc:
        if not is_transient_disconnect_error(exc):
            raise
        db.session.rollback()
        db.engine.dispose()
        return operation()
