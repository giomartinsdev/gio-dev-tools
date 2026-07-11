FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app

COPY worker/value_bets_report/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

COPY shared/ shared/
COPY worker/value_bets_report/ value_bets_report/

ENV PYTHONPATH=/app:/app/value_bets_report

EXPOSE 8000

CMD ["sh", "-c", "opentelemetry-instrument uvicorn app.main:app --host 0.0.0.0 --port 8000"]
