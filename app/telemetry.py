from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(api_key: str, folder_id: str) -> None:
    if not api_key or not folder_id:
        return

    resource = Resource.create({
        "service.name": "linni-back",
        "cluster": "prod",
        "project": f"folder__{folder_id}",
    })

    exporter = OTLPSpanExporter(
        endpoint="ingest.monium.yandex.cloud:443",
        headers={
            "Authorization": f"Api-Key {api_key}",
            "x-monium-project": f"folder__{folder_id}",
        },
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
