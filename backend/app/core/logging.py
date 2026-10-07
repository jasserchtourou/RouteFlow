import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Set per request by RequestContextMiddleware; read by the log formatter.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """One JSON object per line - easy to ship to any log aggregator."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _DevFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.request_id = request_id_ctx.get() or "-"
        return super().format(record)


def configure_logging(level: str, *, json_logs: bool) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if json_logs
        else _DevFormatter("%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Our middleware logs requests, so silence uvicorn's duplicate access log.
    logging.getLogger("uvicorn.access").disabled = True
