# domain-persister

Consumes everything ACL workers publish and persists it: raw payloads into an
append-only event store (for replay), canonical domain events into read
models (`matches`, `odds_snapshots`), and ML predictions (`InsightGenerated`)
into an `insights` table. All three queues are declared idempotently on
startup from the same `shared.rabbitmq_topology` module `bzzoiro-acl` uses,
so producer and consumer can never disagree on exchange/queue/binding names.

## Env vars (via Infisical, `shared.secret_manager.SecretManager`)

| Var | Purpose |
|---|---|
| `if_id`, `if_secret`, `if_project_id`, `if_env` | Infisical universal-auth client |
| `DATABASE_URL` | Postgres DSN (event store + read models) |
| `RABBITMQ_URI` | amqp:// URI to consume `q.archive.raw` / `q.persister` / `q.insight.projector` |

## Running locally

```bash
cd src/backend/worker/domain-persister
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=$(pwd):$(pwd)/.. uvicorn app.main:app --reload
```

## Endpoints

- `GET /health` — always 200 once the process is up.
- `GET /ready` — 503 until secrets/DB are loaded.
- `GET /matches`, `GET /matches/{match_id}` — read-model queries.
- `GET /insights`, `GET /insights?match_id=...` — ML predictions, most
  recent first.

## Idempotency

- `q.archive.raw` → `event_store` table, `PRIMARY KEY (event_id)` with
  `ON CONFLICT DO NOTHING`: a redelivered raw message is a no-op.
- `q.persister` → read-model upserts keyed by natural key (`match_id`) via
  `ON CONFLICT DO UPDATE`: reprocessing the same domain event re-applies the
  same field values instead of duplicating a row. `odds_snapshots` is keyed
  by the event's own `event_id` (there's no natural key across snapshots
  over time) with `ON CONFLICT DO NOTHING`.
- `q.insight.projector` → `insights` table, keyed by `insight_id` with
  `ON CONFLICT DO NOTHING` — same "point-in-time, never overwritten" shape
  as `odds_snapshots`.
- Messages are acked only after the DB write commits; validation failures
  (unparseable/failing pydantic) are nacked without requeue, which routes
  them to the queue's DLX (`dlx.<queue>` → `q.<queue>.dead`) instead of
  blocking the consumer.

## Known gaps / assumptions

- No `teams`/`competitions` read-model tables: the canonical domain events
  only ever carry team/competition **ids**, never names or other
  attributes, so a table with nothing but an id column wasn't worth adding.
  If the ACL starts emitting entity metadata, add tables then.
