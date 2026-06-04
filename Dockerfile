FROM ghcr.io/openfaas/of-watchdog:0.9.15 AS watchdog

FROM python:3.11-slim

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog

ARG FUNCTION_DIR
WORKDIR /app

COPY ${FUNCTION_DIR}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ shared/
COPY ${FUNCTION_DIR}/ .

ENV mode="http"
ENV fprocess="uvicorn handler:app --host 0.0.0.0 --port 5000"
ENV upstream_url="http://127.0.0.1:5000"

HEALTHCHECK --interval=5s CMD curl -sf http://localhost:8080/_/health || exit 1

CMD ["/usr/bin/fwatchdog"]
