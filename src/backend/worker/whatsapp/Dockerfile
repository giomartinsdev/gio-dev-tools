FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY worker/whatsapp/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY worker/whatsapp/worker.py .

ENV PYTHONPATH=/app

CMD ["python", "-u", "worker.py"]
