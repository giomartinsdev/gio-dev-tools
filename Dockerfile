FROM ghcr.io/openfaas/classic-watchdog:latest AS watchdog

FROM python:3.11-slim

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir \
    opentelemetry-distro \
    opentelemetry-exporter-otlp-proto-grpc \
    opentelemetry-instrumentation-fastapi \
    opentelemetry-instrumentation-httpx \
    opentelemetry-instrumentation-logging && \
    opentelemetry-bootstrap -a install

COPY . .

ENV fprocess="opentelemetry-instrument uvicorn handler:app --host 0.0.0.0 --port 5000"
ENV mode="http"
ENV upstream_url="http://127.0.0.1:5000"

ENV OTEL_EXPORTER_OTLP_ENDPOINT="http://SEU_IP:4317"
ENV OTEL_SERVICE_NAME="hello-fn"
ENV OTEL_TRACES_EXPORTER="otlp"
ENV OTEL_METRICS_EXPORTER="none"
ENV OTEL_LOGS_EXPORTER="none"
ENV OTEL_PYTHON_LOG_CORRELATION="true"

HEALTHCHECK --interval=5s CMD curl -sf http://localhost:8080/_/health || exit 1
CMD ["/usr/bin/fwatchdog"]
