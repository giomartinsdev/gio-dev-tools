# gio-dev-tools

Personal developer tooling platform: serverless functions, API gateway, and web frontends running on self-hosted infrastructure.

## Architecture

```
Client → gio-faas-dashboard (:8079) → Gateway (:3002) → Cloudflare Access → OpenFaaS (of.giomartins.dev) → Function
```

- **Frontend** — React dashboards served via nginx, one app per folder under `src/frontend/`
- **Gateway** — FastAPI proxy that routes `/fn/{function}` to the correct OpenFaaS function, injecting Cloudflare Access credentials
- **Functions** — Python FastAPI apps deployed as faasd functions, with auto-tracing via OpenTelemetry
- **Shared** — Common request/response abstractions and auto-tracer used across all functions

## Structure

```
src/
├── backend/
│   ├── api/
│   │   └── gateway/          # FastAPI proxy
│   └── functions/
│       ├── shared/            # Shared abstractions
│       ├── finance/
│       ├── finance-ocr/
│       └── wp-message/
├── frontend/
│   └── gio-faas-dashboard/   # Main React dashboard
└── infra/
    └── docker-compose.yml    # Brings up gateway + all frontends
```

## Docs

- [Architecture](docs/architecture.md)
- [Adding a function](docs/adding-a-function.md)
- [Adding an API](docs/adding-an-api.md)
- [Adding a frontend](docs/adding-a-frontend.md)
- [Gateway](docs/gateway.md)
- [CI/CD](docs/ci-cd.md)
- [Secrets reference](docs/secrets.md)
