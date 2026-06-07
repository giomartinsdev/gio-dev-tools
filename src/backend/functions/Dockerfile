FROM re.giomartins.dev/of-watchdog:0.9.15 AS watchdog

FROM re.giomartins.dev/python:3.11-slim

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
        fastapi==0.111.0 \
        uvicorn==0.27.0 \
        opentelemetry-distro==0.55b0 \
        opentelemetry-sdk==1.34.0 \
        opentelemetry-api==1.34.0 \
        opentelemetry-exporter-otlp-proto-http==1.34.0 \
        opentelemetry-instrumentation-fastapi==0.55b0 \
        opentelemetry-instrumentation-httpx==0.55b0 \
        opentelemetry-instrumentation-logging==0.55b0 \
        opentelemetry-instrumentation-requests==0.55b0 \
        opentelemetry-instrumentation-urllib3==0.55b0 \
        opentelemetry-instrumentation-sqlalchemy==0.55b0 \
        wrapt==1.17.2

ARG FUNCTION_DIR
WORKDIR /app

COPY functions/${FUNCTION_DIR}/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY functions/${FUNCTION_DIR}/ .

ENV fprocess="opentelemetry-instrument uvicorn handler:app --host 0.0.0.0 --port 5000"
ENV mode="http"
ENV upstream_url="http://127.0.0.1:5000"

HEALTHCHECK --interval=5s CMD curl -sf http://localhost:8080/_/health || exit 1
CMD ["/usr/bin/fwatchdog"]
