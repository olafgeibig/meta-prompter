from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from openinference.semconv.resource import ResourceAttributes

resource = Resource(attributes={
    ResourceAttributes.PROJECT_NAME: 'docs2prompt'
})

# OpenAI Instrumentation
def openai_instrumentation():
    from phoenix.otel import register
    tracer_provider = register(
        project_name="docs2prompt",
        endpoint="http://localhost:6006/v1/traces"
    )
    from openinference.instrumentation.openai import OpenAIInstrumentor 
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

def litellm_instrumentation():
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    endpoint = "http://127.0.0.1:6006/v1/traces"
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))
    from openinference.instrumentation.litellm import LiteLLMInstrumentor
    LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)

def crewai_instrumentation():
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from openinference.instrumentation.crewai import CrewAIInstrumentor
    endpoint = "http://127.0.0.1:6006/v1/traces"
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))
    from openinference.instrumentation.litellm import LiteLLMInstrumentor
    LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)
    CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)

## 
# from arize_otel import register_otel, Endpoints
# register_otel(
#     endpoints = Endpoints.LOCAL_PHOENIX_HTTP,
#     space_id = "docs2prompt", # in app space settings page
#     api_key = "your-api-key", # in app space settings page
#     model_id = "your-model-id", # name this to whatever you would like
# )
