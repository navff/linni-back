from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(api_key: str, monium_project: str) -> None:
    if not api_key or not monium_project:
        return

    resource = Resource.create({
        "service.name": "linni-back",
        "cluster": "prod",
        "project": monium_project,
    })

    exporter = OTLPSpanExporter(
        endpoint="ingest.monium.yandex.cloud:443",
        headers={
            "authorization": f"Api-Key {api_key}",
            "x-monium-project": monium_project,
        },
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
