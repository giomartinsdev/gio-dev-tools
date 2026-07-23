# CI/CD

Three workflows, one per part of the stack, all triggered on push to `main`:

| Workflow | Watches | Builds |
|---|---|---|
| `.github/workflows/deploy-api.yml` | `src/backend/api/**`, `src/backend/shared/**` | Each changed service under `src/backend/api/` |
| `.github/workflows/deploy-workers.yml` | `src/backend/worker/**`, `src/backend/shared/**` | Each changed service under `src/backend/worker/` |
| `.github/workflows/deploy-frontends.yml` | `src/frontend/**` | Each changed app under `src/frontend/` |

## How change detection works

Each workflow's `detect-changes` job diffs `${{ github.event.before }}..HEAD` (the
full push, not just the last commit — a push with multiple commits used to lose
everything before the last one when this diffed `HEAD~1..HEAD` instead) to find
which service directories changed, and outputs that list as a JSON array consumed
by the `build` job's matrix.

If `src/backend/shared/**` changed, **every** API or worker is rebuilt (a shared-lib
change can affect all of them, and there's no reliable way to know which ones
without rebuilding).

## Build steps (per changed service)

1. If `features/` exists, install `requirements.txt` + `requirements-dev.txt` and
   run `python -m behave --no-capture` (workers additionally gate on **90% branch
   coverage** via `coverage run -m behave` + `coverage report`)
2. Build the Docker image (`docker/build-push-action`), tagged `:latest` and
   `:{sha}`, pushed to the private registry `re.giomartins.dev`
3. Cache: `type=gha`, scoped per service — layers are reused across runs

## Deploy step

Every workflow's `deploy` job POSTs to a Dockhand webhook
(`secrets.DOCKHAND_WEBHOOK`) with Cloudflare Access headers. Dockhand pulls the
stack's compose file from this repo and redeploys the containers with the newly
pushed image.

> Changes to `src/infra/*.yml` alone (no service code change) aren't watched by any
> workflow — if you only add/edit a compose file, trigger the Dockhand redeploy for
> that stack manually until this is wired up.

## Adding a new service to CI

Nothing to configure — the workflows auto-discover services by directory presence
under `src/backend/api/`, `src/backend/worker/`, or `src/frontend/`. Push a change
inside a new service's directory and it's picked up automatically. See
[Adding a service](adding-a-service.md).
