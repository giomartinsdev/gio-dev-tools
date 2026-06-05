FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY api/gateway/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY api/gateway/app/ app/

ENV PORT=3000

EXPOSE 3000

CMD ["sh", "-c", "opentelemetry-instrument uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
