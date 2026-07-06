# bzzoiro-acl

Anti-corruption layer over the [bzzoiro](https://sports.bzzoiro.com/docs/)
football API (the only free sport bzzoiro offers). Polls fixtures, live
scores, v2 odds (comparison + a cheap 1x2-only feed), v2 predictions,
teams/squads, AI-predicted lineups, head-to-head records, league
standings, venues, referees, per-player match stats, and match incident
timelines, translates them into canonical domain events, resolves
bzzoiro's own ids to internal canonical UUIDs, and publishes both the raw
payload and the translated events to RabbitMQ. Nothing downstream ever
sees a bzzoiro id or status string.

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
| `BZZOIRO_ODDS_COMPARISON_POLL_SECONDS` | `90` | Interval between per-event odds-comparison + Polymarket polls |
| `BZZOIRO_ODDS_BEST_POLL_SECONDS` | `60` | Interval between `/api/v2/odds/best/` polls (cheap, single-call 1x2 coverage) |
| `BZZOIRO_LINEUPS_POLL_SECONDS` | `300` | Interval between per-event predicted-lineup polls |
| `BZZOIRO_H2H_POLL_SECONDS` | `3600` | Interval between per-event head-to-head polls |
| `BZZOIRO_STANDINGS_POLL_SECONDS` | `3600` | Interval between per-league standings polls |
| `BZZOIRO_VENUES_POLL_SECONDS` | `86400` | Interval between per-venue detail polls (venue attributes barely change) |
| `BZZOIRO_REFEREES_POLL_SECONDS` | `86400` | Interval between per-referee detail polls (career stats barely change) |
| `BZZOIRO_PLAYER_STATS_POLL_SECONDS` | `600` | Interval between per-event player-stats polls (only fixtures that have kicked off are polled) |
| `BZZOIRO_INCIDENTS_POLL_SECONDS` | `120` | Interval between per-event incident-timeline polls (only fixtures that have kicked off are polled) |

## Running locally

```bash
cd src/backend/worker/bzzoiro-acl
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=$(pwd):$(pwd)/.. uvicorn app.main:app --reload
```

Needs Postgres + RabbitMQ reachable (see `src/infra/persistence.yaml`) and
the env vars above set directly (bypassing Infisical) for local runs.

## Observability (OTel traces)

Same zero-code setup already used by `api/gateway` — no manual
`TracerProvider`/exporter wiring in application code:

- The Dockerfile's `CMD` runs the process under `opentelemetry-instrument`
  (from `opentelemetry-distro`), which auto-patches every installed
  `opentelemetry-instrumentation-*` package (FastAPI, httpx, logging) at
  startup — this is what actually turns HTTP requests/responses and log
  lines into spans, no explicit `FastAPIInstrumentor.instrument_app(...)`
  call needed.
- `app/main.py`'s very first lines are `from shared.auto_trace import
  install; install(["app", "src"])` — a homegrown import hook
  (`shared/auto_trace.py`) that wraps every function/method defined in the
  `app` and `src` packages in a span as soon as each submodule is
  imported. Unlike gateway (whose entire logic lives directly in
  `app/main.py`, so nothing outside of FastAPI's own instrumentation gets
  traced), most of this service's actual work — poll handlers, the
  translator, the bzzoiro client, the RabbitMQ publisher — lives under
  `src/`, so it's included here to get real spans around every poll cycle
  and translation step, not just the two manual-trigger HTTP endpoints.
- `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_SERVICE_NAME` are set directly in
  `src/infra/workers.yml` (plain env vars, not Infisical secrets — an OTLP
  collector URL isn't sensitive) pointing at `http://otel-collector:4318`,
  the same `otel-collector` service `src/infra/observability-stack.yml`
  runs on the shared `persistence` network this service is already on.
  `OTEL_SERVICE_NAME` is set to match the container name (`bzzoiro-acl`)
  so traces line up with the `container` label Loki/Promtail already use —
  required for the Tempo↔Loki trace-to-logs correlation in the shared
  Grafana dashboard to work.
- `shared/logger.py` already reads the active span's `trace_id`/`span_id`
  into every log line's `trace=... span=...` fields whenever a span is
  active — this "just works" once the packages above are installed, no
  change needed there.

## Endpoints

- `GET /health` — always 200 once the process is up.
- `GET /ready` — 503 until secrets/DB are loaded and RabbitMQ is connected.
- `POST /poll/fixtures`, `POST /poll/live`, `POST /poll/odds-comparison`,
  `POST /poll/odds-best`, `POST /poll/lineups`, `POST /poll/h2h`,
  `POST /poll/standings`, `POST /poll/predictions`, `POST /poll/venues`,
  `POST /poll/referees`, `POST /poll/player-stats`, `POST /poll/incidents`
  — manual trigger, on top of the fourteen background poll loops that run
  continuously once the service is ready.
- `POST /poll/odds?force=true`, `POST /poll/teams?force=true` — same, but
  these two also read/write a sync checkpoint (see below); `force=true`
  ignores it and does a full resync for that feed only.
- `POST /resync` — forces a full resync of **all fourteen** feeds in one
  call (odds and teams with `force=True`, the rest just run once). Use this
  after a schema change, a suspected gap, or whenever you want a clean
  slate without waiting for the natural poll interval.

## Odds comparison, Polymarket, and value-bet detection

`POST /poll/odds-comparison` (loop: `BZZOIRO_ODDS_COMPARISON_POLL_SECONDS`)
is the part that actually closes the loop from raw data to an actionable
signal:

- For every match in the same date window `PollFixturesHandler` uses (not
  the global `/api/v2/odds/` firehose, and not the broken
  `/api/v2/events/live/` — see below), it fetches
  `GET /api/v2/events/{id}/odds/comparison/`: every bookmaker's price for
  every market/outcome, plus bzzoiro's own precomputed best price per
  outcome. Translated into `OddsComparisonCaptured`, `markets` kept verbatim
  since that's exactly what the shape the value-bet detector needs.
- It also fetches `GET /api/v2/events/{id}/polymarket/` (prediction-market
  implied probabilities — a third, independent probability source, separate
  from both bookmaker odds and bzzoiro's own ML model) into
  `PolymarketSnapshotCaptured`. **No live example ever returned real market
  data while this was written** — every match probed (including World Cup
  fixtures) returned `404 {"detail": "No Polymarket markets available for
  this event."}` — so the ingestion is defensive: archived and translated
  best-effort, logged and skipped if the shape doesn't match what's
  expected, never crashes the poll.
- **Value-bet detection** happens in `domain-persister`, not here: it
  correlates the `InsightGenerated` (bzzoiro's own model probability) it
  already ingests via `/api/v2/predictions/` against the best price from
  `OddsComparisonCaptured` for the same match. `edge = model_probability -
  (1 / best_odds)`; above `VALUE_BET_EDGE_THRESHOLD` (default `0.05`, set on
  domain-persister) it's recorded as a value bet, queryable at
  `GET /value-bets` on that service. See its README for the full mapping
  from bzzoiro's prediction markets (match_result, over_under, btts) to
  odds markets (1x2, over_under_15/25/35, btts).

## Lineups, head-to-head, league standings, and cheap 1x2 odds

Four more per-event/per-league polls, each independently resilient (one
event/league failing doesn't abort the rest of that poll cycle, same
pattern as odds comparison):

- **`POST /poll/lineups`** — `GET /api/v2/events/{id}/lineups/`, bzzoiro's
  AI-predicted starting XI per side with a `confidence` score and an
  overall `lineup_status` (confirmed live: `"predicted"`, `beta: true`).
  Translated into `LineupsCaptured`. This is the one that actually changes
  value-bet quality, not just adds context: `domain-persister`'s
  `ValueBetDetector` reads lineup confidence as a trust filter — if either
  side's predicted lineup is below `LINEUP_CONFIDENCE_THRESHOLD` (default
  `0.6`, set on domain-persister), a detected edge is suppressed rather
  than recorded, since an unconfident lineup prediction means real team
  news might not be priced into the model or the odds yet.
- **`POST /poll/odds-best`** — `GET /api/v2/odds/best/`, a single paginated
  call covering the best 1x2 price for every event bzzoiro tracks odds for
  (confirmed live: 26 events in one call, vs. one call per event the full
  comparison poll needs). Translated into `OddsBestCaptured` and merged
  (not replaced) into the same `odds_comparisons` row the full comparison
  poll writes — see domain-persister's README for how the merge avoids
  clobbering over_under/btts data with a 1x2-only update.
- **`POST /poll/h2h`** — `GET /api/v2/events/{id}/h2h/`, head-to-head record
  between the two sides. Pure context (doesn't feed edge detection) —
  confirmed live that pairings with no shared history return a 200 with
  every field zeroed rather than a 404, so this is translated the same as
  a populated record.
- **`POST /poll/standings`** — `GET /api/v2/leagues/{id}/standings/`,
  scoped to leagues actually active in the current fixtures date window
  (extracted from each event's `league_id`, not a full league catalogue
  crawl). Pure context, same "why" dashboard role as h2h.

## Venues, referees, player stats, and match incidents

Four more polls, all pure context (none feed edge detection), each scoped
to the current fixtures date window rather than a full catalogue crawl —
same independent-resilience pattern as the rest:

- **`POST /poll/venues`** — `GET /api/v2/venues/{id}/`, scoped to
  `venue_id`s seen on fixtures in the window. Confirmed live shape:
  `{id, name, city, country, capacity, ...}` (plus pitch/geo fields not
  captured). Translated into `VenueCaptured`. This is what finally lets
  `MatchScheduled.venue` carry a real name instead of always `None` — the
  events feed only ever has `venue_id`, never a name string — though
  wiring that join up on the domain-persister side is still a follow-up
  (see its README's "Known gaps").
- **`POST /poll/referees`** — `GET /api/v2/referees/{id}/`, scoped to
  `referee_id`s seen on fixtures in the window (often `null` for
  not-yet-assigned fixtures, confirmed live, so those are naturally
  skipped). Confirmed live shape: `{id, name, country, avg_yellow_per_match,
  avg_red_per_match, career_games, ...}`. Translated into `RefereeCaptured`,
  full payload kept verbatim in `details`.
- **`POST /poll/player-stats`** — `GET /api/v2/events/{id}/player-stats/`,
  only for fixtures whose `status` isn't `notstarted`/`postponed`/
  `cancelled` (bzzoiro only populates this once a match has kicked off).
  Confirmed live shape: `{event_id, count, player_stats: [...]}`, one entry
  per player who featured (rating, touches, shots, passes, cards, etc.).
  Translated into `PlayerStatsCaptured`, kept verbatim as one blob per
  match.
- **`POST /poll/incidents`** — `GET /api/v2/events/{id}/incidents/`, same
  kicked-off-only filter as player stats. Confirmed live shape:
  `{event_id, incidents: [...]}`, each entry a goal/card/substitution/
  period marker. Translated into `IncidentsCaptured`; an empty list is
  still a valid capture (nothing's happened yet in a live 0-0), so this is
  checked by key presence, not truthiness.

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

`status=upcoming` predictions cover every fixture bzzoiro considers upcoming
with **no date bound** — confirmed live: 293 matches in one poll, vs. the
handful `PollFixturesHandler`'s 3-day window captures. Left alone, an insight
can point at a `match_id` with no row yet in `domain-persister`'s `matches`/
`teams` tables, showing up as blank team names anywhere that joins on them
(e.g. the `domain-data-insights` dashboard API). Fixed by
`translate_prediction_context()`: it reuses `translate_event()` on the
prediction payload's own embedded `event` sub-object (which already carries
`id`/`event_date`/`status`/`league_id`/`home_team_id`/`away_team_id` — the
same shape the fixtures feed uses) to emit `MatchScheduled`/
`MatchStatusChanged`, plus two `TeamUpdated` events built from the embedded
flat `home_team`/`away_team` name strings via `translate_team()`. Only the
name is ever known this way — short_name/country/venue_id stay blank until
the real teams poll's `TeamUpdated` upserts over these placeholder rows, which
is safe since upserts never regress data, only fill it in.

The predictions poll also has **no checkpoint** (unlike odds/teams) — every
600s cycle re-fetches and re-translates the *entire* "upcoming" set, not just
what changed. `translate_prediction()` used to assign a fresh `uuid4()` as
`insight_id` on every call, so redelivering the same still-unchanged
prediction inserted a brand new `insights` row every time instead of being
skipped by `insert_insight`'s `ON CONFLICT (id) DO NOTHING` — confirmed live:
one match sitting for weeks with an unchanged prediction piled up dozens of
byte-for-byte-identical insight rows, crowding out everything else in
`domain-data-insights`'s "most recent" view. Fixed by resolving `insight_id`
from bzzoiro's own prediction `id` (entity_type `"insight"`), the same
identity-resolution pattern every other provider entity already goes
through — same prediction id now always resolves to the same canonical
insight UUID, so redelivery is idempotent.

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
- **Fixed**: `GET /api/v2/events/live/`'s envelope uses an `events` key
  (`{"count": N, "events": [...]}`), not `results` — `fetch_live()` now
  reads it directly instead of going through `_paginate_v2`. Also fixed:
  the `status` filter on `/api/v2/events/` silently ignored the v1-style
  values (`upcoming`/`live`) this code used to send — bzzoiro doesn't
  validate the param, it just drops values it doesn't recognize and
  returns the unfiltered set. `fetch_events(status=...)` now translates our
  vocabulary to the real v2 enum (confirmed against the live OpenAPI spec:
  `notstarted`/`inprogress`/`finished`/etc.) before sending.
- **Fixed**: `translate_squad` (team `/squad/` polling) assumed a schema
  (`status`/`club`/`club_country`/`caps`/`goals`/`player_id`) that actually
  belongs to a different endpoint entirely — `/api/v2/worldcup/squads/`
  (national-team call-ups). The real `/api/v2/teams/{id}/squad/` payload is
  leaner (`id`/`name`/`position`/`jersey_number`/`nationality`/
  `date_of_birth`), and was throwing `KeyError: 'status'` on every single
  team. Now defaults the missing fields and resolves player identity off
  the squad item's own `id` (confirmed live: it *is* the player's provider
  ref, not a distinct `player_id` field that never existed on this
  endpoint).
- **Fixed**: `translate_event` (fixtures ingestion) used to read
  `payload.get("home")`/`payload.get("away")`/`payload.get("date")`/
  `payload.get("league", {}).get("id")` — none of which exist on the real
  `EventDetailV2Schema` payload confirmed live via `GET /api/v2/events/`.
  The actual fields are flat: `home_team_id`, `away_team_id`, `event_date`,
  `league_id`, `home_score`/`away_score` (also flat, not nested under
  `score`), `current_minute` (not `minute`). Confirmed in production: the
  `matches` table sat at a fraction of the real fixture count and stopped
  advancing entirely, while every other feed kept updating. Also fixed in
  the same pass: `_STATUS_MAP` only recognized `"upcoming"`/`"live"`, not
  the real value `"notstarted"` (confirmed the most common status,
  7161/11608+ events sampled) or any of the `1st_half`/`inprogress`/etc.
  in-play values — so `MatchStatusChanged`/`MatchFinished` almost never
  fired either. There's no venue-name string on this payload (only
  `venue_id`, an int) — `MatchScheduled.venue` stays `None` until a venue
  lookup exists. The embedded per-event `odds` dict this code used to parse
  never exists on the real payload either (removed — the free-standing
  `/api/v2/odds/` poll already covers odds correctly).
