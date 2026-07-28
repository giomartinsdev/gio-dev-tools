# CI/CD

**Status: removed (2026-07-28).** The three GitHub Actions workflows
(`deploy-api.yml`, `deploy-workers.yml`, `deploy-frontends.yml`) that used to build
on push to `main` and trigger a Dockhand redeploy were broken and have been deleted.
Deploys are manual for now — build the image on the server and restart the stack by
hand.

## Manual deploy (current process)

On the server, for any service under `src/backend/api/{service}`:

```bash
cd ~/gio-dev-tools   # or wherever this repo is checked out on the server
git pull

# build the image (context is src/backend, same as the old CI did)
docker build -f src/backend/api/{service}/Dockerfile -t re.giomartins.dev/{service}:latest src/backend

# redeploy just that stack
docker compose -f src/infra/apis.yml up -d {service}
```

Swap `apis.yml` for `workers.yml` if it's a worker, or the appropriate stack file
for a frontend.

## Re-adding CI later

If you want push-to-deploy back, the previous workflows are recoverable from git
history (`git log --all --full-history -- .github/workflows/deploy-api.yml`) — worth
fixing whatever broke them (self-hosted runner health, registry auth, or the
Dockhand webhook secret are the usual suspects) rather than rewriting from scratch.
