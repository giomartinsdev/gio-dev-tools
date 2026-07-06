# bzzoiro-acl

Anti-corruption layer over the [bzzoiro](https://sports.bzzoiro.com/docs/)
football API (the only free sport bzzoiro offers). Polls fixtures, live
scores, v2 odds and v2 predictions, translates them into canonical domain
events, resolves bzzoiro's own ids to internal canonical UUIDs, and publishes
both the raw payload and the translated events to RabbitMQ. Nothing
downstream ever sees a bzzoiro id or status string.

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
| `BZZOIRO_ODDS_POLL_SECONDS` | `60` | Interval between `/api/v2/odds/` polls |
| `BZZOIRO_PREDICTIONS_POLL_SECONDS` | `600` | Interval between `/api/v2/predictions/` polls |

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
- `POST /poll/fixtures`, `POST /poll/live`, `POST /poll/odds`,
  `POST /poll/predictions` — manual trigger (same shape as `asset-quotes`'
  `/quotes/refresh`), on top of the four background poll loops that run
  continuously once the service is ready.

## Odds and predictions (v2)

`/api/v2/odds/` returns a flat array — one row per (event, bookmaker, market,
outcome), no `count/next` envelope, just `limit`/`offset`. The client keeps
paging while a full page comes back and stops on the first partial page.
The translator groups rows sharing the same (event, bookmaker, market) into
one `OddsSnapshotCaptured` event with a `selections` list, so odds history
accumulates as a new row per snapshot in `domain-persister`'s
`odds_snapshots` table rather than overwriting the previous price.

`/api/v2/predictions/` is translated into `InsightGenerated` — routed to the
`analysis.events` exchange (not `domain.events`), per the topology in
`shared/rabbitmq_topology.py`. There is currently no consumer for
`q.insight.projector` (out of scope per the original plan), so these are
published but not yet persisted anywhere; wire up a consumer in
`domain-persister` if/when that's needed.

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
- WebSocket live ingestion is a paid addon and is **not implemented** — only
  the free REST surface is polled.
- Odds/predictions use the exact schemas pulled from the live OpenAPI spec
  (`https://sports.bzzoiro.com/openapi.json`, served as YAML despite the
  `.json` extension) — `OddsItemV2Schema` and `PredictionV2Schema` — not
  guessed from the docs page.
