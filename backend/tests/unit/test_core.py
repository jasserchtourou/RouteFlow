"""Infrastructure code: logging, clock, request-context middleware."""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.core.clock import get_clock, utcnow
from app.core.logging import JsonFormatter, configure_logging, request_id_ctx
from app.core.middleware import RequestContextMiddleware


def _record(message: str = "hello", exc_info: Any = None) -> logging.LogRecord:
    return logging.LogRecord("app.test", logging.WARNING, __file__, 1, message, (), exc_info)


def test_json_formatter_emits_one_valid_json_object_with_request_id() -> None:
    token = request_id_ctx.set("req-123")
    try:
        line = JsonFormatter().format(_record("shipment %s late"))
    finally:
        request_id_ctx.reset(token)

    entry = json.loads(line)
    assert entry["level"] == "WARNING"
    assert entry["logger"] == "app.test"
    assert entry["message"] == "shipment %s late"
    assert entry["request_id"] == "req-123"
    assert datetime.fromisoformat(entry["timestamp"]).tzinfo is not None
    assert "\n" not in line  # one line per event, so log shippers can parse it


def test_json_formatter_includes_exception_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _record(exc_info=sys.exc_info())

    entry = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in entry["exception"]


@pytest.mark.parametrize(
    ("json_logs", "expected"), [(True, JsonFormatter), (False, logging.Formatter)]
)
def test_configure_logging_selects_formatter(json_logs: bool, expected: type) -> None:
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    try:
        configure_logging("WARNING", json_logs=json_logs)

        [handler] = root.handlers
        assert isinstance(handler.formatter, expected)
        assert (type(handler.formatter) is JsonFormatter) == json_logs
        assert root.level == logging.WARNING
    finally:
        root.handlers, root.level = saved[0], saved[1]


def test_clock_returns_timezone_aware_utc_now() -> None:
    now = get_clock()()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    assert abs(utcnow() - datetime.now(UTC)) < timedelta(seconds=1)


async def test_middleware_passes_non_http_scopes_through_untouched() -> None:
    seen: list[str] = []

    async def inner(scope: Any, receive: Any, send: Any) -> None:
        seen.append(scope["type"])

    middleware = RequestContextMiddleware(inner)

    await middleware({"type": "lifespan"}, None, None)  # type: ignore[arg-type]
    await middleware({"type": "websocket"}, None, None)  # type: ignore[arg-type]

    assert seen == ["lifespan", "websocket"]
