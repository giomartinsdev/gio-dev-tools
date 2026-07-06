FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY api/domain-data-insights/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY api/domain-data-insights/ domain-data-insights/

ENV PYTHONPATH=/app:/app/domain-data-insights

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
