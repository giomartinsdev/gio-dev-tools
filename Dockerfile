FROM ghcr.io/openfaas/classic-watchdog:latest AS watchdog

FROM python:3.11-slim

COPY --from=watchdog /fwatchdog /usr/bin/fwatchdog
RUN chmod +x /usr/bin/fwatchdog

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY handler.py .

ENV fprocess="python handler.py"
ENV mode="http"
ENV upstream_url="http://127.0.0.1:8000"

HEALTHCHECK --interval=5s CMD curl -sf http://localhost:8080/_/health || exit 1

CMD ["/usr/bin/fwatchdog"]
