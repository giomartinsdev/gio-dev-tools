# Architecture

## Overview

```
┌──────────────────────┐     ┌─────────────────────┐     ┌──────────────────────┐     ┌──────────────┐
│  gio-faas-dashboard  │────▶│  Gateway             │────▶│  Cloudflare Access   │────▶│  faasd       │
│  :8079               │     │  :3002               │     │  of.giomartins.dev   │     │  (openfaas)  │
└──────────────────────┘     └─────────────────────┘     └──────────────────────┘     └──────────────┘
                                                                                               │
                                                                         ┌─────────────────────┴──────────────┐
                                                                         │                                     │
                                                                  ┌──────┴──────┐                    ┌─────────┴──────┐
                                                                  │   finance   │                    │   wp-message   │
                                                                  └─────────────┘                    └────────────────┘
```

## Components

### Frontend (`src/frontend/`)

Each subdirectory is an independent React app served via nginx. Adding a new frontend requires only creating a folder with a `Dockerfile` — the CI pipeline detects and deploys it automatically.

### Gateway (`src/backend/api/gateway/`)

FastAPI service that acts as the single entry point for all function calls. Responsibilities:
- Routes `/fn/{function_name}` dynamically to the correct faasd function
- Injects `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers on every upstream request
- Strips hop-by-hop headers before forwarding
- Exposes `GET /health` for uptime checks

Runs as a Docker container managed by Dockhand on port 3002.

### Functions (`src/backend/functions/`)

Each function is an independent FastAPI app built on a shared base image. They follow this internal structure:

```
src/backend/functions/{name}/
├── handler.py        # FastAPI app entrypoint, wires Request → main()
├── requirements.txt  # Function-specific dependencies
└── src/
    └── main.py       # Business logic (DDD: domain / application / infrastructure)
```

Functions receive a `Request` object from `shared/` and return a `Response`. The faasd watchdog handles the HTTP lifecycle.

### Shared (`src/backend/functions/shared/`)

| Module | Purpose |
|---|---|
| `request.py` | Parses HTTP request into a typed `Request` dataclass |
| `response.py` | Wraps response body + status into a `JSONResponse` |
| `logger.py` | Structured stdout logger |
| `auto_trace.py` | Import hook that wraps all functions/classes in OpenTelemetry spans |

### Infra (`src/infra/`)

`docker-compose.yml` that brings up the full local stack (gateway + all frontends) with a single command:

```bash
docker compose -f src/infra/docker-compose.yml up -d
```

### Observability

All functions are instrumented via `opentelemetry-instrument` (set as the faasd `fprocess`). Traces are exported to `optel.giomartins.dev` over OTLP/HTTP, protected by Cloudflare Access.

## Networking

The gateway reaches OpenFaaS over the public DNS `https://of.giomartins.dev`, authenticated via Cloudflare Access service tokens (`CF-Access-Client-Id` / `CF-Access-Client-Secret`). Functions themselves run on the server and communicate internally without going through the gateway.
