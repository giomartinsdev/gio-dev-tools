# bzzoiro-acl

Anti-corruption layer over the [bzzoiro](https://sports.bzzoiro.com/docs/)
football API (the only free sport bzzoiro offers). Polls fixtures/live scores,
translates them into canonical domain events, resolves bzzoiro's own ids to
internal canonical UUIDs, and publishes both the raw payload and the
translated events to RabbitMQ. Nothing downstream ever sees a bzzoiro id or
status string.

## Env vars (via Infisical, `shared.secret_manager.SecretManager`)

| Var | Purpose |
|---|---|
| `if_id`, `if_secret`, `if_project_id`, `if_env` | Infisical universal-auth client, used to fetch the secrets below |
| `BZZOIRO_API_KEY` | `Authorization: Token <key>` header for every bzzoiro request |
| `DATABASE_URL` | Postgres DSN (provider-identity mapping table) |
| `RABBITMQ_URI` | amqp:// URI for publishing to `ingestion.events` / `domain.events` |

Plain env vars (no secret needed):

| Var | Default | Purpose |
|---|---|---|
| `BZZOIRO_FIXTURES_POLL_SECONDS` | `300` | Interval between `/api/events/` polls (upcoming/finished fixtures) |
| `BZZOIRO_LIVE_POLL_SECONDS` | `30` | Interval between `/api/live/` polls |

## Running locally

```bash
cd src/backend/worker/bzzoiro-acl
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=$(pwd):$(pwd)/.. uvicorn app.main:app --reload
```

Needs Postgres + RabbitMQ reachable (see `src/infra/persistence.yaml`) and
the env vars above set directly (bypassing Infisical) for local runs.

## Endpoints

- `GET /health` — always 200 once the process is up.
- `GET /ready` — 503 until secrets/DB are loaded and RabbitMQ is connected.
- `POST /poll/fixtures`, `POST /poll/live` — manual trigger (same shape as
  `asset-quotes`' `/quotes/refresh`), on top of the background poll loops
  that run continuously once the service is ready.

## Scaling

Single instance is expected — the poll loops are not partitioned, so running
more than one replica would just poll bzzoiro redundantly. If throughput ever
needs it, split fixtures vs. live polling into separate deployments (they're
already independent asyncio tasks) rather than replicating this whole
service.

## Known gaps / assumptions

- Base URL assumed to be `https://sports.bzzoiro.com/api/` for football
  (root, no version prefix), per `docs/bzzoiro-docs.md` section 4. The
  WebSocket docs reference `/api/v2/...` for other sports — confirm against
  Swagger (`/api/docs/`) before depending on this in production.
- WebSocket live ingestion and per-bookmaker odds (`odds_book`) are paid
  addons and are **not implemented** — only the free REST surface is polled.
- `predictions/` (ML predictions) is not polled yet; add a third poll loop
  the same way as fixtures/live if needed.
