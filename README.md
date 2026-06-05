# faasd-server-like-lambda

Python serverless functions running on [faasd](https://github.com/openfaas/faasd), with a lightweight API gateway that proxies requests to each function.

## Architecture

```
Client → Gateway (:3002) → Cloudflare Access → OpenFaaS (of.giomartins.dev) → Function
```

- **Gateway** — FastAPI proxy that routes `/fn/{function}` to the OpenFaaS function, injecting Cloudflare Access credentials
- **Functions** — Python FastAPI apps deployed as faasd functions, with auto-tracing via OpenTelemetry
- **Shared** — Common request/response abstractions and auto-tracer used across all functions

## Docs

- [Architecture](docs/architecture.md)
- [Adding a function](docs/adding-a-function.md)
- [Gateway](docs/gateway.md)
- [CI/CD](docs/ci-cd.md)
- [Secrets reference](docs/secrets.md)
