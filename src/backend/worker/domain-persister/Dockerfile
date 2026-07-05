FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY worker/domain-persister/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY worker/domain-persister/ domain-persister/

ENV PYTHONPATH=/app:/app/domain-persister

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
