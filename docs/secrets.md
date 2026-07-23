# Secrets reference

Two separate systems, for two separate concerns — don't mix them up.

## GitHub Actions secrets (CI-time only)

**GitHub → Settings → Secrets and variables → Actions.** Used to build and deploy;
never reach a running container.

| Secret | Used by | Description |
|---|---|---|
| `REGISTRY_USER` / `REGISTRY_PASSWORD` | all deploy workflows | Private registry creds (`re.giomartins.dev`) |
| `DOCKHAND_WEBHOOK` | all deploy workflows | Webhook URL that tells Dockhand to redeploy after a push |
| `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` | all deploy workflows | Cloudflare Access headers required to call the Dockhand webhook |

## Infisical (runtime secrets)

Every backend service (API or worker) resolves its actual runtime secrets — DB
connection string, API keys, tokens — from **Infisical** at boot, via
`shared.secret_manager.SecretManager`. The container only needs the credentials to
*reach* Infisical:

```yaml
environment:
  if_id: ${IF_ID}
  if_secret: ${IF_SECRET}
  if_project_id: ${IF_PROJECT_ID}
  if_env: prod
```

These four are the only "secrets" that exist in the compose files
(`src/infra/*.yml`), sourced from a `.env` on the host — never hardcoded, never
committed. Everything else (`DATABASE_URL`, `BRAPI_TOKEN`, `RABBITMQ_URI`,
`EVOLUTION_API_KEY`, `BZZOIRO_API_KEY`, ...) is fetched from Infisical by name
inside `_init()`/`main()` at process startup — grep any service's `app/main.py` for
`sm.get_secret(...)` to see exactly which keys it needs.

The [Configuração](../src/frontend/gio-faas-dashboard/src/modules/settings) screen
in the frontend tracks *which* service uses *which* Infisical key (`secret_ref`) —
it's a pointer for humans, not a copy of the value. The `settings` service's
database never stores an actual secret.

## Adding a new secret

1. Add the key/value in Infisical under the shared project
2. Call `sm.get_secret("YOUR_KEY")` wherever the service needs it (see any
   `app/main.py`'s `_init()` for the pattern)
3. Optionally register it in Configuração (`secret_ref`) so it shows up in the
   service registry
