# Secrets reference

All secrets are stored in **GitHub → Settings → Secrets and variables → Actions**.

## Shared

| Secret | Used by | Description |
|---|---|---|
| `REGISTRY_USER` | both workflows | Private registry username (`re.giomartins.dev`) |
| `REGISTRY_PASSWORD` | both workflows | Private registry password |
| `CF_ACCESS_CLIENT_ID` | `deploy.yml`, `gateway-deploy.yml` | Cloudflare Access service token ID |
| `CF_ACCESS_CLIENT_SECRET` | `deploy.yml`, `gateway-deploy.yml` | Cloudflare Access service token secret |

## Functions only

| Secret | Used by | Description |
|---|---|---|
| `SSH_PRIVATE_KEY` | `deploy.yml` | SSH key to access the server via Cloudflare tunnel |
| `SSH_HOST` | `deploy.yml` | Server hostname (Cloudflare tunnel DNS) |
| `SSH_USER` | `deploy.yml` | SSH user on the server |

## wp-message function

| Secret | Description |
|---|---|
| `EVOLUTION_URL` | Evolution API base URL (`https://evo.giomartins.dev`) |
| `EVOLUTION_API_KEY` | Evolution API key |
| `EVOLUTION_INSTANCE_NAME` | Evolution instance name (`giomartinsdev`) |

## Gateway only

| Secret | Description |
|---|---|
| `DOCKHAND_GATEWAY_WEBHOOK` | Dockhand webhook URL to trigger gateway redeploy |

> `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` for the gateway container itself are set as environment variable overrides directly in Dockhand, not in GitHub Secrets.
