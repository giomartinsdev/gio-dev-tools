# bzzoiro-acl

Anti-corruption layer over the [bzzoiro](https://sports.bzzoiro.com/docs/)
football API (the only free sport bzzoiro offers). Polls fixtures, live
scores, v2 odds, v2 predictions and teams/squads, translates them into
canonical domain events, resolves bzzoiro's own ids to internal canonical
UUIDs, and publishes both the raw payload and the translated events to
RabbitMQ. Nothing downstream ever sees a bzzoiro id or status string.

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
| `BZZOIRO_TEAMS_POLL_SECONDS` | `86400` | Interval between team/squad polls, and the minimum time that must pass before a restart re-triggers one (see "Sync checkpoints" below) |

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
- `POST /poll/fixtures`, `POST /poll/live`, `POST /poll/predictions` — manual
  trigger, on top of the five background poll loops that run continuously
  once the service is ready.
- `POST /poll/odds?force=true`, `POST /poll/teams?force=true` — same, but
  these two also read/write a sync checkpoint (see below); `force=true`
  ignores it and does a full resync for that feed only.
- `POST /resync` — forces a full resync of **all five** feeds in one call
  (odds and teams with `force=True`, the rest just run once). Use this after
  a schema change, a suspected gap, or whenever you want a clean slate
  without waiting for the natural poll interval.

## Sync checkpoints (why restarts don't re-fetch everything)

`/api/v2/odds/` alone has 200k+ historical rows — polling it with no filter
on every restart is what caused the "starts over every time" problem. Fixed
with a `sync_checkpoints` table (`bzzoiro_data.sync_checkpoints`) that
**bzzoiro-acl owns and writes to itself** — nothing else reads or writes it,
unlike an earlier version of this that inferred progress from
domain-persister's `odds_snapshots.captured_at`, which is a different
service's read model and can lag behind what was actually fetched.

- **Odds**: after each successful poll, the highest `updated_at` seen across
  all fetched rows is saved as the `odds` checkpoint and sent as
  `updated_after` on the next poll — confirmed against the live API that
  this filter genuinely narrows the result set (`count` drops from ~278k to
  ~16k for "today", to 0 for a future date), so this is a real incremental
  sync, not just cosmetic.
- **Teams**: squads barely change, so instead of an incremental filter, a
  full crawl (one `/squad/` request per team) is skipped entirely if the
  `teams` checkpoint is younger than `BZZOIRO_TEAMS_POLL_SECONDS` — a
  restart 10 minutes after the last successful sync won't trigger another
  one; a restart 2 days later will.
- **Force a resync**: `POST /poll/odds?force=true`, `POST
  /poll/teams?force=true`, or `POST /resync` for everything at once. Force
  bypasses the checkpoint for that call but still updates it afterward.

`/api/v2/odds/` returns the same `{count, next, previous, results}` envelope
`/api/v2/events/` uses — despite the OpenAPI schema documenting a plain
array (bitten by doc/reality mismatches enough times now that the client
accepts either shape defensively; see `bzzoiro_client.py::_paginate_v2`).
The translator groups rows sharing the same (event, bookmaker, market) into
one `OddsSnapshotCaptured` event with a `selections` list, so odds history
accumulates as a new row per snapshot in `domain-persister`'s
`odds_snapshots` table rather than overwriting the previous price.

`/api/v2/predictions/` is translated into `InsightGenerated` — routed to the
`analysis.events` exchange (not `domain.events`), per the topology in
`shared/rabbitmq_topology.py`. `domain-persister` consumes `q.insight.projector`
and persists these into its `insights` table (`GET /insights` on that
service).

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
