import logging

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_ENDPOINT = "ingest.monium.yandex.cloud:443"


def setup_telemetry(api_key: str, monium_project: str) -> None:
    if not api_key or not monium_project:
        return

    resource = Resource.create({
        "service.name": "linni-back",
        "cluster": "prod",
        "project": monium_project,
    })
    headers = {
        "authorization": f"Api-Key {api_key}",
        "x-monium-project": monium_project,
    }

    # Traces
    span_exporter = OTLPSpanExporter(endpoint=_ENDPOINT, headers=headers)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Logs
    log_exporter = OTLPLogExporter(endpoint=_ENDPOINT, headers=headers)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)

    # Бридж Python logging → OTel (WARNING и выше уходят в Monium)
    handler = LoggingHandler(level=logging.WARNING, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
