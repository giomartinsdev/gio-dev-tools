# Secrets reference

All secrets are stored in **GitHub → Settings → Secrets and variables → Actions**.

## Shared (all workflows)

| Secret | Description |
|---|---|
| `REGISTRY_USER` | Private registry username (`re.giomartins.dev`) |
| `REGISTRY_PASSWORD` | Private registry password |
| `CF_ACCESS_CLIENT_ID` | Cloudflare Access service token ID |
| `CF_ACCESS_CLIENT_SECRET` | Cloudflare Access service token secret |

## Functions only (`deploy-functions.yml`)

| Secret | Description |
|---|---|
| `SSH_PRIVATE_KEY` | SSH key to access the server via Cloudflare tunnel |
| `SSH_HOST` | Server hostname (Cloudflare tunnel DNS) |
| `SSH_USER` | SSH user on the server |

## Function-specific

| Secret | Function | Description |
|---|---|---|
| `DATABASE_URL` | `finance` | PostgreSQL connection string |
| `EVOLUTION_URL` | `wp-message` | Evolution API base URL |
| `EVOLUTION_API_KEY` | `wp-message` | Evolution API key |
| `EVOLUTION_INSTANCE_NAME` | `wp-message` | Evolution instance name |

## APIs (`deploy-api.yml`)

| Secret | Description |
|---|---|
| `DOCKHAND_GATEWAY_WEBHOOK` | Dockhand webhook URL to trigger gateway redeploy |

## Frontends (`deploy-frontends.yml`)

| Secret | Description |
|---|---|
| `DOCKHAND_GIO_FAAS_DASHBOARD_WEBHOOK` | Dockhand webhook URL to trigger gio-faas-dashboard redeploy |

> `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` for containers running via Dockhand are set as environment variable overrides directly in Dockhand, not duplicated here.
