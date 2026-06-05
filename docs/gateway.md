# Gateway

Located at `src/backend/api/gateway/`.

## Routing

All requests follow the pattern:

```
{METHOD} /fn/{function_name}[/{path}]
```

The gateway strips hop-by-hop headers, injects Cloudflare Access credentials, and forwards the request — including body, query params, and remaining headers — to:

```
https://of.giomartins.dev/function/{function_name}[/{path}]
```

The response (status code, headers, body) is forwarded back as-is.

## Health check

```
GET /health
→ { "status": "OK", "faas_gateway_url": "https://of.giomartins.dev" }
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `FAAS_GATEWAY_URL` | No | `https://of.giomartins.dev` | OpenFaaS gateway base URL |
| `CF_ACCESS_CLIENT_ID` | Yes | — | Cloudflare Access service token ID |
| `CF_ACCESS_CLIENT_SECRET` | Yes | — | Cloudflare Access service token secret |
| `PORT` | No | `3000` | Port the gateway listens on |

## Running locally

```bash
cd src/backend/api/gateway
CF_ACCESS_CLIENT_ID=xxx CF_ACCESS_CLIENT_SECRET=yyy uvicorn app.main:app --port 3000
```

Or via the infra compose (brings up gateway + all frontends):

```bash
docker compose -f src/infra/docker-compose.yml up -d
```

## Dockhand stack

The gateway runs as a Docker container managed by Dockhand. Redeploys are triggered automatically by the CI pipeline via the `DOCKHAND_GATEWAY_WEBHOOK` secret.

`CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` for the container must be set as environment variable overrides in Dockhand (not committed to the compose file).

To trigger a manual redeploy:

```bash
curl -X POST "<DOCKHAND_WEBHOOK_URL>" \
  -H "CF-Access-Client-Id: <id>" \
  -H "CF-Access-Client-Secret: <secret>"
```
