# domain-data-insights

Read-only API over `bzzoiro_data` — the Postgres schema `bzzoiro-acl` and
`domain-persister` populate. Neither worker is on the `apis` Docker network
(they're workers, not gateway-routed services), so this service exists
purely to give the `gio-faas-dashboard` frontend a way to plot that data:
it queries the same tables directly (same cross-service read pattern
`asset-quotes` already uses against `portfolio`'s `assets` table) and never
writes to them, migrates them, or duplicates domain-persister's own
internal query logic.

## Env vars (via Infisical, `shared.secret_manager.SecretManager`)

| Var | Purpose |
|---|---|
| `if_id`, `if_secret`, `if_project_id`, `if_env` | Infisical universal-auth client |
| `DATABASE_URL` | Same Postgres DSN bzzoiro-acl/domain-persister use — `bzzoiro_data` lives there |

## Running locally

```bash
cd src/backend/api/domain-data-insights
pip install -r requirements.txt -r requirements-dev.txt
PYTHONPATH=$(pwd):$(pwd)/.. uvicorn app.main:app --reload
```

## Endpoints

- `GET /health` — always 200 once the process is up.
- `GET /overview` — row count + most recent timestamp per `bzzoiro_data`
  table, the at-a-glance "is data actually arriving" view.
- `GET /matches`, `GET /matches?limit=&offset=` — recent matches, joined
  with home/away team names, newest kickoff first.
- `GET /value-bets` — currently open value bets, highest edge first,
  joined with team names.
- `GET /value-bets/outcomes/summary` — `{total, won, lost, win_rate}`
  across every resolved value bet.
- `GET /insights` — recent ML predictions, joined with team names.

## Known gaps

- No pagination beyond `limit`/`offset`; no endpoints yet for venues,
  referees, player stats, or incidents — those tables exist in
  `bzzoiro_data` but this service doesn't surface them. Add a query +
  route the same way as the ones above if the dashboard needs them.
- No BDD tests for `app/` (matches every other `api/*` service in this
  repo — none of them have a `.coveragerc` or app-level tests either);
  only `src/infrastructure/read_only_repository.py` has feature coverage.
