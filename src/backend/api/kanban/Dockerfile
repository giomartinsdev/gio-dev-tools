FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY api/kanban/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY api/kanban/ kanban/

ENV PYTHONPATH=/app:/app/kanban

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
