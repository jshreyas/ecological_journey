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

load_dotenv()
resource = Resource(attributes={"service.name": "nicegui-app"})
trace.set_tracer_provider(TracerProvider(resource=resource))
FastAPIInstrumentor.instrument_app(app)
LOKI_URL = os.getenv("LOKI_URL")


def custom_renderer(_, __, event_dict):
    level = event_dict.pop("level", "INFO").upper()
    msg = event_dict.pop("event", "")
    return f"{level} | {msg}"


structlog.configure(
    processors=[custom_renderer],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
loki_handler = LokiHandler(
    url=f"{LOKI_URL}/loki/api/v1/push",
    tags={"application": "ej"},
    version="1",
)
loki_handler.setLevel(logging.INFO)


root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(loki_handler)

log = structlog.get_logger()
log.info("✅ Logging initialized with both Loki and console output")
