# CI/CD

## Functions — `deploy.yml`

Triggers on push to `main` when any file under `functions/**` changes.

### Steps

1. **Detect changes** — diffs `HEAD~1..HEAD` to find which function directories changed (excludes `shared/`)
2. **Build** — builds the Docker image for each changed function using the shared `Dockerfile` at repo root (or a function-local `Dockerfile` if present), tagged as `re.giomartins.dev/{function}:latest` and `:{sha}`
3. **Deploy** — SSHs into the server via Cloudflare Access tunnel and runs `faas-cli deploy` with the new image and environment variables

### Function-specific env vars

Injected conditionally in the deploy step. Currently:

| Function | Variables |
|---|---|
| `wp-message` | `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME` |

All functions receive the shared OTEL variables (`OTEL_EXPORTER_OTLP_ENDPOINT`, etc.).

### Adding env vars for a new function

See [Adding a function](adding-a-function.md#4-add-environment-variables-if-needed).

---

## Gateway — `gateway-deploy.yml`

Triggers on push to `main` when any file under `gateway/**` changes.

### Steps

1. **Build** — builds `gateway/Dockerfile`, pushes `re.giomartins.dev/gateway:latest` and `:{sha}`
2. **Deploy** — POSTs to the Dockhand webhook (`DOCKHAND_GATEWAY_WEBHOOK` secret), which pulls the new image and recreates the container

### Image cache

Both workflows use GitHub Actions cache (`type=gha`) scoped per function/service to speed up layer reuse.
