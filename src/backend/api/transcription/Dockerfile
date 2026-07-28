FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY api/transcription/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY api/transcription/ transcription/

ENV PYTHONPATH=/app:/app/transcription
ENV HF_HOME=/model-cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
