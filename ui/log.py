import logging
import os

import structlog
from dotenv import load_dotenv
from logging_loki import LokiHandler
from nicegui import app
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from structlog.contextvars import merge_contextvars

load_dotenv()
resource = Resource(attributes={"service.name": "nicegui-app"})
trace.set_tracer_provider(TracerProvider(resource=resource))
FastAPIInstrumentor.instrument_app(app)
LOKI_URL = os.getenv("LOKI_URL")
LOKI_USER = os.getenv("LOKI_USER")
LOKI_PASS = os.getenv("LOKI_PASS")


def custom_renderer(_, __, event_dict):
    level = event_dict.pop("level", "INFO").upper()
    user = event_dict.pop("user", "anonymous")
    msg = event_dict.pop("event", "")
    return f"{level} | 👤 {user} | {msg}"


structlog.configure(
    processors=[
        merge_contextvars,
        custom_renderer,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)


# Define a safer LokiHandler that doesn't raise on failure
class SafeLokiHandler(LokiHandler):
    _loki_failed = False

    def emit(self, record):
        try:
            super().emit(record)
        except Exception:
            if not SafeLokiHandler._loki_failed:
                SafeLokiHandler._loki_failed = True
            self.handleError(record)


loki_handler = SafeLokiHandler(
    url=f"{LOKI_URL}/loki/api/v1/push", tags={"application": "ej"}, version="1", auth=(LOKI_USER, LOKI_PASS)
)
loki_handler.setLevel(logging.INFO)


root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(loki_handler)

logging.raiseExceptions = False  # suppresses handler errors from printing to stderr

log = structlog.get_logger()
log.info("✅ Logging initialized with both Loki and console output")
