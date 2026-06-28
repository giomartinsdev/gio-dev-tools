FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY api/obsidian/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY api/obsidian/ obsidian/

ENV PYTHONPATH=/app:/app/obsidian

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
