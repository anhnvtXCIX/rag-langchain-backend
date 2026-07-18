import logging
import logging.config
import os
import time
from collections.abc import Awaitable, Callable

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from starlette.responses import Response


def setup_logging() -> None:
    env = os.getenv("ENV", "dev").lower()
    json_logs = os.getenv("LOG_JSON", "").lower() in {"1", "true", "yes", "on"}
    if env in {"prod", "production"}:
        json_logs = True

    formatter = "json" if json_logs else "text"
    formatters: dict[str, dict[str, object]] = {
        "text": {
            "class": "uvicorn.logging.DefaultFormatter",
            "format": "%(levelprefix)s %(asctime)s [%(correlation_id)s] [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
            "use_colors": True,
        },
        "json": {
            "class": "pythonjsonlogger.json.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(correlation_id)s %(message)s",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        },
    }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "correlation_id": {
                    "()": "asgi_correlation_id.CorrelationIdFilter",
                    "uuid_length": 32,
                    "default_value": "-",
                }
            },
            "formatters": formatters,
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "filters": ["correlation_id"],
                    "formatter": formatter,
                }
            },
            "root": {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "handlers": ["default"],
            },
            # Avoid duplicate HTTP request lines once custom request logs are enabled.
            "loggers": {
                "uvicorn.access": {"handlers": [], "propagate": False},
            },
        }
    )


def configure_app_logging(app: FastAPI) -> None:
    logger = logging.getLogger(__name__)

    @app.middleware("http")
    async def log_exceptions(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled exception for %s %s", request.method, request.url.path
            )
            raise

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start_time
        logger.info(
            "%s %s %s %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response

    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        update_request_header=True,
    )
