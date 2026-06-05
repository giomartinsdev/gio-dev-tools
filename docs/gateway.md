# Gateway

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
cd gateway
CF_ACCESS_CLIENT_ID=xxx CF_ACCESS_CLIENT_SECRET=yyy uvicorn app.main:app --port 3000
```

## Dockhand stack

The gateway runs as a Docker container managed by Dockhand. The stack is defined in `gateway/docker-compose.yml` and deployed from this repo via webhook.

`CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` must be set as environment variable overrides in Dockhand (not committed to the compose file).

To trigger a manual redeploy, use the Dockhand UI or call the webhook directly:

```bash
curl -X POST "<DOCKHAND_WEBHOOK_URL>" \
  -H "CF-Access-Client-Id: <id>" \
  -H "CF-Access-Client-Secret: <secret>"
```
