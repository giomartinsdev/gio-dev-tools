FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY worker/bzzoiro-acl/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY worker/bzzoiro-acl/ bzzoiro-acl/

ENV PYTHONPATH=/app:/app/bzzoiro-acl

EXPOSE 8000

CMD ["sh", "-c", "opentelemetry-instrument uvicorn app.main:app --host 0.0.0.0 --port 8000"]
