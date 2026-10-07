import logging
import re
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class RequestContextMiddleware:
    """Pure ASGI middleware: request id propagation + one access-log line per request.

    Written as raw ASGI (not BaseHTTPMiddleware) to avoid its known problems with
    streaming responses and background tasks - relevant later for streamed AI answers.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = MutableHeaders(scope=scope).get(REQUEST_ID_HEADER, "")
        # Only trust a client-supplied id if it is harmless (prevents log injection).
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> %s (%.1f ms)", scope["method"], scope["path"], status_code, elapsed_ms
            )
            request_id_ctx.reset(token)
