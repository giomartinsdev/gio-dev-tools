# CI/CD

All pipelines trigger on push to `main` and use a matrix strategy — only changed services are built and deployed.

---

## Functions — `deploy-functions.yml`

Triggers when any file under `src/backend/functions/**` changes.

### Steps

1. **Detect changes** — diffs `HEAD~1..HEAD` to find which function directories changed (excludes `shared/`)
2. **Build** — builds the Docker image for each changed function using `src/backend/functions/Dockerfile` (or a function-local `Dockerfile` if present), tagged as `re.giomartins.dev/{function}:latest` and `:{sha}`
3. **Deploy** — SSHs into the server via Cloudflare Access tunnel and runs `faas-cli deploy` with the new image and environment variables

### Function-specific env vars

Injected conditionally in the deploy step:

| Function | Variables |
|---|---|
| `wp-message` | `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE_NAME` |
| `finance` | `DATABASE_URL` |
| `finance-ocr` | `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`, `FINANCE_URL` |

All functions receive the shared OTEL variables (`OTEL_EXPORTER_OTLP_ENDPOINT`, etc.).

### Adding env vars for a new function

See [Adding a function](adding-a-function.md#4-add-environment-variables-if-needed).

---

## APIs — `deploy-api.yml`

Triggers when any file under `src/backend/api/**` changes.

### Steps

1. **Detect changes** — finds which API subdirectory changed
2. **Build** — builds `src/backend/api/{api}/Dockerfile`, pushes `re.giomartins.dev/{api}:latest` and `:{sha}`
3. **Deploy** — POSTs to the Dockhand webhook for that API (secret `DOCKHAND_{API}_WEBHOOK`), which pulls the new image and recreates the container

### Adding a new API

See [Adding an API](adding-an-api.md).

---

## Frontends — `deploy-frontends.yml`

Triggers when any file under `src/frontend/**` changes.

### Steps

1. **Detect changes** — finds which frontend subdirectory changed
2. **Build** — builds `src/frontend/{frontend}/Dockerfile`, pushes `re.giomartins.dev/{frontend}:latest` and `:{sha}`
3. **Deploy** — POSTs to the Dockhand webhook for that frontend (secret `DOCKHAND_{FRONTEND}_WEBHOOK`), which pulls the new image and recreates the container

### Adding a new frontend

See [Adding a frontend](adding-a-frontend.md).

---

## Image cache

All workflows use GitHub Actions cache (`type=gha`) scoped per service to speed up layer reuse.
