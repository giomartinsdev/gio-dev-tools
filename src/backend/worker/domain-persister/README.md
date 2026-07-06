# domain-persister

Consumes everything ACL workers publish and persists it: raw payloads into an
append-only event store (for replay), canonical domain events into read
models (`matches`, `odds_snapshots`, `odds_comparisons`,
`polymarket_snapshots`), and ML predictions (`InsightGenerated`) into an
`insights` table. All three queues are declared idempotently on startup from
the same `shared.rabbitmq_topology` module `bzzoiro-acl` uses, so producer
and consumer can never disagree on exchange/queue/binding names.

It also runs the **value-bet detector**: every time a new odds comparison or
a new insight lands for a match, it recomputes the edge between bzzoiro's
own model probability and the best market price, and keeps a `value_bets`
table of everything currently above threshold — see below.

## Env vars (via Infisical, `shared.secret_manager.SecretManager`)

| Var | Purpose |
|---|---|
| `if_id`, `if_secret`, `if_project_id`, `if_env` | Infisical universal-auth client |
| `DATABASE_URL` | Postgres DSN (event store + read models) |
| `RABBITMQ_URI` | amqp:// URI to consume `q.archive.raw` / `q.persister` / `q.insight.projector` |

Plain env vars (no secret needed):

| Var | Default | Purpose |
|---|---|---|
| `VALUE_BET_EDGE_THRESHOLD` | `0.05` | Minimum `model_probability - implied_probability` to record/keep a value bet (5 percentage points) |

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
- `GET /value-bets`, `GET /value-bets?match_id=...` — currently-detected
  edges above `VALUE_BET_EDGE_THRESHOLD`, highest edge first.

## Value-bet detection

`ValueBetDetector.evaluate(match_id)` runs after projecting either an
`OddsComparisonCaptured` or an `InsightGenerated` event for that match — a
no-op if the other half of the correlation isn't there yet. It maps
bzzoiro's own prediction markets onto bzzoiro's odds markets:

| Model probability (`InsightModel.feature_snapshot`) | Odds market / outcome |
|---|---|
| `match_result.prob_home` / `prob_draw` / `prob_away` | `1x2` / `HOME`, `DRAW`, `AWAY` |
| `over_under.prob_over_15` / `prob_over_25` / `prob_over_35` | `over_under_15` / `over_under_25` / `over_under_35`, `over` |
| `btts.prob_yes` | `btts` / `yes` |

For each pair present on both sides: `implied_probability = 1 / best_odds`,
`edge = model_probability - implied_probability`. Above
`VALUE_BET_EDGE_THRESHOLD` it's upserted into `value_bets` keyed by
`(match_id, market, outcome)` — reflecting the *current* best-known
opportunity, not a growing history. Below threshold, any previously
recorded value bet for that key is deleted — if the market moves back, the
opportunity disappears from `GET /value-bets` on its own.

`odds_comparisons`/`polymarket_snapshots` are themselves "current state"
tables too (upserted by `match_id`, not append-only) — only the latest
picture matters for detection; the raw event-store history is what you'd
replay from if you needed the full timeline.

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
- `value_bets` is upserted keyed by `(match_id, market, outcome)` via
  `ON CONFLICT DO UPDATE` — recomputing the same edge just re-applies the
  same numbers, and a value bet that drops below threshold is deleted
  outright rather than left stale.
- Messages are acked only after the DB write commits; validation failures
  (unparseable/failing pydantic) are nacked without requeue, which routes
  them to the queue's DLX (`dlx.<queue>` → `q.<queue>.dead`) instead of
  blocking the consumer.

## Known gaps / assumptions

- No `teams`/`competitions` read-model tables: the canonical domain events
  only ever carry team/competition **ids**, never names or other
  attributes, so a table with nothing but an id column wasn't worth adding.
  If the ACL starts emitting entity metadata, add tables then.
