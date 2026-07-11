# value_bets_report

Sends a daily WhatsApp report of tomorrow's value bets to a configurable
list of recipients. Runs two things concurrently: a `DailyScheduler` loop
that fires at a configurable time and a RabbitMQ consumer on
`value-bets-report-trigger` — both converge on the same `ReportGenerator`,
so a manual "Enviar agora" from the dashboard and the scheduled daily send
share one code path.

Report data comes from the read-only `domain-data-insights` API
(`GET /value-bets`), never touching `bzzoiro_data` directly.

## Env vars (via Infisical, `shared.secret_manager.SecretManager`)

| Var | Purpose |
|---|---|
| `if_id`, `if_secret`, `if_project_id`, `if_env` | Infisical universal-auth client |
| `VALUE_BETS_REPORT_DATABASE_URL` | Postgres DSN for this worker's own dedicated database (config + recipients) — deliberately not `DATABASE_URL`, which is already used by `domain-persister`/`bzzoiro-acl` for `bzzoiro_data` in the same Infisical project |
| `RABBITMQ_URI` | amqp:// URI to consume `value-bets-report-trigger` and to publish to `whatsapp-send` |

Plain env vars:

| Var | Default | Purpose |
|---|---|---|
| `DOMAIN_DATA_INSIGHTS_URL` | `http://domain-data-insights:8000` | Internal URL of the read-only value-bets API (same `apis` Docker network) |

## Endpoints

- `GET /health` — always 200 once the process is up.
- `GET /ready` — 503 until secrets/DB are loaded.
- `GET /config`, `PUT /config` — `{send_time: "HH:MM", reference_day_offset: int, enabled: bool}`.
- `GET /recipients`, `POST /recipients`, `PATCH /recipients/{id}` (toggle active), `DELETE /recipients/{id}`.
- `POST /trigger` — publishes to `value-bets-report-trigger` immediately, regardless of scheduler state.

## Scheduling

No cron/APScheduler dependency — `DailyScheduler` is a plain asyncio loop
that re-reads config every cycle (so a `PUT /config` change to `send_time`
or `enabled` takes effect without a restart) and publishes a trigger
message once the configured time is reached. `reference_day_offset` (days
from today, default `1` = tomorrow) determines which calendar day of
`kickoff_at` the report covers, bucketed in `America/Sao_Paulo`.

Both the scheduled fire and a manual `POST /trigger` publish to the same
queue with no dedup — if both happen to land close together, two reports
get sent. Accepted trade-off, not worth a debounce/lock for this use case.

## Running locally

```bash
cd src/backend/worker/value_bets_report
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=$(pwd):$(pwd)/.. uvicorn app.main:app --reload
```

## Tests

```bash
coverage run -m behave --no-capture --format progress2
coverage report
```
