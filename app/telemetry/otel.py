from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span


def set_span_attributes(span: Span, attrs: dict[str, Any]) -> None:
    for key, value in attrs.items():
        if value is None:
            continue
        if not isinstance(value, (str, bool, int, float)):
            value = str(value)
        span.set_attribute(key, value)


def add_instrumentation(app: FastAPI):
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor().instrument_app(app)
    OpenAIInstrumentor().instrument()
