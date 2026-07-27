# Gateway

`src/backend/api/gateway` — the only backend service the frontend talks to directly.
A thin FastAPI reverse proxy: no business logic, no database.

## Routing

Every internal service gets a path prefix that maps 1:1 to its container:

```
{METHOD} /{service}[/{path}]  →  http://{service}:8000/{path}
```

e.g. `GET /portfolio/assets` → `http://portfolio:8000/assets`. Hop-by-hop headers
are stripped before forwarding; everything else (method, body, query params,
remaining headers) passes through as-is, and the upstream response is forwarded
back unchanged.

Two special cases:
- `GET /whatsapp/events` and `GET /bus-tracker/positions/events` — proxied as a
  streamed `text/event-stream` (SSE), not buffered like the rest
- `/fn/{function}` and `/fn-async/{function}` — legacy passthrough to an external
  OpenFaaS gateway (`FAAS_GATEWAY_URL`), predates the current service-per-domain
  architecture, kept for whatever still depends on it

## Environment variables

| Variable | Default | Points to |
|---|---|---|
| `FINANCE_URL` | `http://finance:8000` | finance API |
| `FINANCE_OCR_URL` | `http://finance-ocr:8000` | finance-ocr API |
| `ASSET_QUOTES_URL` | `http://asset-quotes:8000` | asset-quotes API |
| `PORTFOLIO_URL` | `http://portfolio:8000` | portfolio API |
| `WHATSAPP_URL` | `http://whatsapp:8000` | whatsapp API |
| `DOMAIN_DATA_INSIGHTS_URL` | `http://domain-data-insights:8000` | domain-data-insights API |
| `VALUE_BETS_REPORT_URL` | `http://value-bets-report:8000` | value_bets_report worker's HTTP surface |
| `SETTINGS_URL` | `http://settings:8000` | settings API |
| `BUS_TRACKER_URL` | `http://bus-tracker:8000` | bus-tracker API |
| `FAAS_GATEWAY_URL` | `https://of.giomartins.dev` | legacy OpenFaaS passthrough |
| `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` | — | only used for the legacy `/fn/*` passthrough |
| `PORT` | `3000` | listen port |

All the `{SERVICE}_URL` defaults already match the container names in
`src/infra/apis.yml` / `workers.yml` — you only need to override them for local dev
against a different host.

## Health check

```
GET /health
→ { "status": "OK", "finance_url": "...", "portfolio_url": "...", ... }
```

Echoes every resolved upstream URL — useful for confirming env vars actually landed
before chasing a 502 somewhere else.

## Running locally

```bash
cd src/backend/api/gateway
pip install -r requirements.txt
CF_ACCESS_CLIENT_ID=x CF_ACCESS_CLIENT_SECRET=y uvicorn app.main:app --port 3000
```

Point the frontend's `VITE_GATEWAY_URL` at `http://localhost:3000`, or run against
individual services directly for a tighter local loop.

## Adding a new service

1. Add `{SERVICE}_URL = os.environ.get("{SERVICE}_URL", "http://{service}:8000")`
2. Add a pair of `@app.api_route` handlers for `/{service}` and `/{service}/{path}`
   mirroring an existing one (e.g. `proxy_settings`)
3. Add the URL to the `/health` response
4. Set `{SERVICE}_URL` as an env override on the `gateway` service in
   `src/infra/utils.yml`
