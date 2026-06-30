FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY whatsapp-worker/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY whatsapp-worker/worker.py .

ENV PYTHONPATH=/app

CMD ["python", "-u", "worker.py"]
