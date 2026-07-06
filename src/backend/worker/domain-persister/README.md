# domain-persister

Consumes everything ACL workers publish and persists it: raw payloads into an
append-only event store (for replay), canonical domain events into read
models (`matches`, `odds_snapshots`, `odds_comparisons`,
`polymarket_snapshots`, `lineups`, `h2h`, `standings`, `teams`,
`squad_members`, `venues`, `referees`, `player_stats`, `incidents`), and ML
predictions (`InsightGenerated`) into an `insights` table. All three queues
are declared idempotently on startup from the same
`shared.rabbitmq_topology` module `bzzoiro-acl` uses, so producer and
consumer can never disagree on exchange/queue/binding names.

It also runs the **value-bet detector**: every time a new odds comparison or
a new insight lands for a match, it recomputes the edge between bzzoiro's
own model probability and the best market price, and keeps a `value_bets`
table of everything currently above threshold — see below. When a match
finishes, whatever value bets were still open for it are archived into
`value_bet_outcomes` with the real score (win/loss), and a new value bet
triggers a WhatsApp alert if one is configured.

## Env vars (via Infisical, `shared.secret_manager.SecretManager`)

| Var | Purpose |
|---|---|
| `if_id`, `if_secret`, `if_project_id`, `if_env` | Infisical universal-auth client |
| `DATABASE_URL` | Postgres DSN (event store + read models) |
| `RABBITMQ_URI` | amqp:// URI to consume `q.archive.raw` / `q.persister` / `q.insight.projector`, and to publish WhatsApp alerts to `whatsapp-send` |
| `VALUE_BET_ALERT_NUMBER` | Optional. WhatsApp number to alert when a brand-new value bet is detected. If unset/unfetchable, alerting is silently disabled — this is a normal, supported state, not every deployment wants it wired up |
| `VALUE_BET_ALERT_INSTANCE` | Optional. Evolution API instance name for the alert; defaults to whatever `whatsapp-worker` uses if omitted |

Plain env vars (no secret needed):

| Var | Default | Purpose |
|---|---|---|
| `VALUE_BET_EDGE_THRESHOLD` | `0.05` | Minimum `model_probability - implied_probability` to record/keep a value bet (5 percentage points) |
| `LINEUP_CONFIDENCE_THRESHOLD` | `0.6` | Minimum predicted-lineup confidence (either side) below which a detected edge is suppressed rather than recorded |

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
- `GET /value-bets/outcomes`, `GET /value-bets/outcomes?match_id=...` —
  resolved value bets (won/lost, with the final score), most recently
  resolved first.
- `GET /value-bets/outcomes/summary` — win rate across every resolved value
  bet: `{"total", "won", "lost", "win_rate"}`.

## Value-bet outcome history (backtesting)

`ValueBetOutcomeResolver.resolve_match(match_id, home_score, away_score)`
runs when a `MatchFinished` event lands. It looks at whatever's still open
in `value_bets` for that match at that exact moment, resolves each one
against the final score (`1x2`/`over_under_*`/`btts` markets), archives the
result into the append-only `value_bet_outcomes` table, and deletes the
`value_bets` row — the match is over, so it's no longer an actionable
opportunity either way.

This only captures bets still open right at full time — a value bet that
existed earlier and closed *before* the match (edge dropped, or lineup
confidence recovered) was already deleted by `ValueBetDetector` and never
makes it into this history. That's an intentional v1 simplicity trade-off:
it answers "did my final picks win", not "did every edge that ever existed
win" (which would need `ValueBetDetector` to never delete, and this
resolver to reconcile every past snapshot instead).

Same isolation guarantee as value-bet detection: a bug here can't poison an
otherwise-valid `MatchFinished` message, since the match-finished write
already committed before this runs.

## WhatsApp alert on a new value bet

The first time `ValueBetDetector.evaluate()` upserts a value bet for a
`(match, market, outcome)` it hasn't seen before (checked via
`find_value_bet` right before the upsert), it fires a WhatsApp text through
`WhatsAppNotifier` — the same `whatsapp-send` RabbitMQ queue `api/whatsapp`'s
`POST /send` publishes to and `worker/whatsapp`'s `consume_outbound()`
already consumes. domain-persister can't reach `api/whatsapp`'s HTTP
endpoint directly (it's only on the `persistence` Docker network, not
`apis`), but it's already got a RabbitMQ connection for its own event
consumption on that same network, so publishing directly needs no new
network access — just a short-lived extra AMQP connection per alert (rare
enough not to be worth keeping one open).

Re-detecting an already-known value bet (edge just recomputed to a similar
number on a later poll) does **not** re-alert — only a genuinely new
`(match, market, outcome)` triggers a message. A failing notifier (queue
down, etc.) is caught and logged; it can never stop the value bet itself
from being recorded.

Disabled by default — set `VALUE_BET_ALERT_NUMBER` (and optionally
`VALUE_BET_ALERT_INSTANCE`) to turn it on.

## Value-bet detection

`ValueBetDetector.evaluate(match_id)` runs after projecting an
`OddsComparisonCaptured`, `OddsBestCaptured`, `InsightGenerated`, or
`LineupsCaptured` event for that match — a no-op if insight+odds aren't
both there yet. It maps bzzoiro's own prediction markets onto bzzoiro's
odds markets:

| Model probability (`InsightModel.feature_snapshot`) | Odds market / outcome |
|---|---|
| `match_result.prob_home` / `prob_draw` / `prob_away` | `1x2` / `HOME`, `DRAW`, `AWAY` |
| `over_under.prob_over_15` / `prob_over_25` / `prob_over_35` | `over_under_15` / `over_under_25` / `over_under_35`, `over` |
| `btts.prob_yes` | `btts` / `yes` |

**Fixed**: every `prob_*` field in bzzoiro's `markets` block is on a 0-100
percentage scale (confirmed live: `match_result.prob_home: 55.5`, summing
to ~100 across the three outcomes) — not the 0-1 fraction this used to
assume. Feeding a raw `55.5` into `edge = model_probability -
implied_probability` produced edges over 30 (3000+ percentage points),
which overflowed `value_bets.model_probability`'s `Numeric(6,5)` column and
turned every message for a match with both an insight and an odds
comparison into a poison message — confirmed live. `_extract_probability`
now divides by 100 before use. `InsightModel.confidence` (bzzoiro's
`model.confidence`) is a separate field and was already a genuine 0-1
fraction — not affected.

A bug in `ValueBetDetector.evaluate()` must never fail the message that
triggered it: the odds/lineup/insight write it runs after already
committed in its own transaction, so `ProjectDomainEventHandler`/
`ProjectInsightHandler` catch and log any exception from `evaluate()`
rather than letting it propagate and nack an otherwise-valid message
(this is exactly how the percentage-scale bug above was surfacing —
perfectly good `OddsComparisonCaptured` messages were dying downstream of
a bug in an unrelated calculation).

For each pair present on both sides: `implied_probability = 1 / best_odds`,
`edge = model_probability - implied_probability`. Above
`VALUE_BET_EDGE_THRESHOLD` **and** with lineup confidence at or above
`LINEUP_CONFIDENCE_THRESHOLD` (see below), it's upserted into `value_bets`
keyed by `(match_id, market, outcome)` — reflecting the *current* best-known
opportunity, not a growing history. Otherwise, any previously recorded
value bet for that key is deleted — if the market moves back, the
opportunity disappears from `GET /value-bets` on its own.

`odds_comparisons`/`polymarket_snapshots`/`lineups`/`h2h`/`standings` are
themselves "current state" tables too (upserted by `match_id` or
`competition_id`, not append-only) — only the latest picture matters for
detection/context; the raw event-store history is what you'd replay from
if you needed the full timeline.

### Lineup confidence as a trust filter, not another data source

bzzoiro's own model and the market's odds may both have been computed
before knowing a key player will miss the match. A "value bet" detected in
that window can just be stale noise, not a real mispricing. So before
recording an edge, the detector checks `LineupsCaptured.lineups.{home,away}.confidence`
(the AI-predicted lineup's confidence score per side, lowest of the two
wins) against `LINEUP_CONFIDENCE_THRESHOLD`:

- No lineup captured yet for the match → filter doesn't apply, detection
  proceeds normally (missing data isn't the same as "known unreliable").
- Lineup captured but confidence below threshold → the edge is suppressed
  (deleted if previously recorded), logged as "value bet suppressed... team
  news may not be priced in yet".
- Lineup captured with confidence at/above threshold → detection proceeds
  as if no lineup data existed.

### Odds/best: a cheap 1x2 feed that merges, never replaces

`bzzoiro-acl`'s `PollOddsBestHandler` polls `/api/v2/odds/best/` — one
paginated call covering the best 1x2 price for every event with tracked
odds, far cheaper than the per-event `/odds/comparison/` poll. Since it
only ever knows about the `1x2` market, `OddsBestCaptured` is projected via
`merge_odds_comparison_markets` — a single `UPDATE ... SET markets =
odds_comparisons.markets || EXCLUDED.markets` (Postgres JSONB concat) —
instead of `upsert_odds_comparison`'s full replace. That means a cheap,
frequent 1x2 update can't wipe out `over_under`/`btts` data a slower, fuller
comparison poll already captured for the same match.

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
  same numbers, and a value bet that drops below threshold (or whose
  lineup confidence drops too low) is deleted outright rather than left
  stale.
- `lineups`/`h2h` are upserted by `match_id`, `standings` by
  `competition_id` — same "current state, overwritten" shape as
  `odds_comparisons`.
- Messages are acked only after the DB write commits; validation failures
  (unparseable/failing pydantic) are nacked without requeue, which routes
  them to the queue's DLX (`dlx.<queue>` → `q.<queue>.dead`) instead of
  blocking the consumer.

## Known gaps / assumptions

- No `competitions` read-model table: `MatchModel.competition_id` is the
  only place a competition/league id is stored — there's no separate table
  for competition names/attributes yet. `teams` and `squad_members` do
  exist (`TeamModel`/`SquadMemberModel`), populated from `TeamUpdated`/
  `SquadUpdated`.
- **`Base.metadata.create_all()` only creates missing tables — it never
  ALTERs an existing one when a model gains/renames a column.** Confirmed
  live: `TeamModel` gained `short_name`/`country`/`venue_id`/`updated_at`
  after the `teams` table was first created, and every `upsert_team` since
  then failed with `psycopg2.errors.UndefinedColumn` and silently went to
  the DLX — `teams` sat at 0 rows while `squad_members` (a table created
  fresh, matching its model exactly) filled up normally. There's no
  Alembic/migration tool in this repo (matches the finance/asset-quotes
  "create_all on boot" convention), so any future column added to an
  existing model needs a manual `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  run against the live DB — `create_all()` alone will not apply it. See
  `docs/fix-teams-schema-drift.sql` in the repo root for the one-off fix
  and a general drift-check query across every table in `bzzoiro_data`.
- `MatchScheduled.venue` still always projects as `None` even though a
  `venues` table now exists (populated from `VenueCaptured`, keyed by
  `venue_id`) — nothing currently joins `MatchModel.venue` to it at
  projection time. Doing that join is a small follow-up, not implemented
  yet in this pass.
