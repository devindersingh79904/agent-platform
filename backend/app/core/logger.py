import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware


LOG_FORMAT = (
    "[%(asctime)s.%(msecs)03d]"
    "[corr=%(correlation_id)s]"
    "[run=%(run_id)s]"
    "[task=%(task_id)s]"
    "[file=%(filename)s:%(lineno)d]"
    "[level=%(levelname)s] %(message)s"
)

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class ContextFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "-"
        if not hasattr(record, "run_id"):
            record.run_id = "-"
        if not hasattr(record, "task_id"):
            record.task_id = "-"
        return True


def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str):
    return logging.getLogger(name)


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

        logger.info(
            "%s %s -> %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "correlation_id": getattr(request.state, "correlation_id", "-"),
                "run_id": "-",
                "task_id": "-",
            },
        )
        return response
