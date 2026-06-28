FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY api/finance/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY api/finance/ finance/

ENV PYTHONPATH=/app:/app/finance

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
