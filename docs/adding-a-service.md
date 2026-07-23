# Adding a service

Every backend service — API or worker — follows the same DDD/CQRS-lite shape. The
`settings` service (`src/backend/api/settings`) is the newest and cleanest reference
to copy from; `portfolio` is the oldest and most complete (has an event-driven
immutable ledger and a full BDD suite).

## 1. Scaffold the layout

```
{service}/
├── app/
│   ├── main.py       # FastAPI app, lifespan-based async init, /health
│   ├── router.py     # HTTP routes, thin — delegates to command handlers
│   ├── schemas.py     # Pydantic request bodies
│   └── deps.py        # FastAPI Depends() — repo/bus injection, readiness gate
├── src/
│   ├── domain/
│   │   ├── {entity}.py     # Pydantic model + .create()/.to_dict()
│   │   ├── events.py       # DomainEvent subclasses
│   │   └── repository.py   # ABC — save/update/delete/find_all/find_by_id
│   ├── application/commands/
│   │   ├── create_{entity}.py   # Command (pydantic) + Handler (validates, saves, publishes event)
│   │   ├── update_{entity}.py
│   │   └── delete_{entity}.py
│   └── infrastructure/
│       ├── models.py        # SQLAlchemy model
│       ├── repository.py    # Postgres{Entity}Repository — implements the ABC
│       └── event_bus.py     # copy verbatim from any existing service
├── features/                # BDD (behave), optional but expected for new services
│   ├── environment.py       # copy verbatim
│   └── steps/
├── requirements.txt
├── requirements-dev.txt     # just `behave==1.2.6`
└── Dockerfile
```

## 2. Domain entity

Pydantic model with a `.create(...)` classmethod (generates the id, applies
defaults) and a `.to_dict()` for API responses. No I/O, no framework imports.

## 3. Commands, not a service layer

One file per use case: a `{Verb}{Entity}Command` (pydantic, the handler's input)
and a `{Verb}{Entity}Handler` (`__init__(self, repo, bus)`, `.handle(cmd)` does
validation → repository call → `bus.publish(Event(...))` → return the entity).
Routes stay thin — they build the command, call the handler, translate
`ValueError` → `HTTPException(400)`.

## 4. Repository

Abstract base in `domain/repository.py`; Postgres implementation in
`infrastructure/repository.py`. Soft-delete (`deleted_at`) over hard delete in
every existing service — keep doing that.

## 5. Wire it up in `app/main.py`

Copy the `lifespan()` + `_init()` pattern from `settings/app/main.py`: init runs in
a background thread so the app can serve `/health` immediately, sets
`app.state._init_done` / `app.state._init_error`, and `deps.py`'s `_ready()`
dependency blocks requests until init finishes (or 503s if it failed).

```python
sm = SecretManager()
TransactionManager.configure(TransactionConfig(url=sm.get_secret("DATABASE_URL")))
Base.metadata.create_all(TransactionManager.get().engine)
```

No manual migration step — `create_all` is idempotent and every service shares one
Postgres instance (see `docs/architecture.md`).

## 6. BDD tests

Behave scenarios against an **in-memory** repository (not Postgres) — see
`settings/features/steps/service_steps.py` for the pattern: a
`InMemory{Entity}Repository` implementing the same ABC, wired into the real command
handlers. This is what lets `python -m behave` run with zero external
dependencies, locally or in CI.

## 7. Dockerfile

Copy any existing service's Dockerfile and change the two `{service}` path
substitutions — they're otherwise identical (same base image, same
`COPY shared/`, same `PYTHONPATH`).

## 8. Wire it into the gateway and infra

- Add `{SERVICE}_URL` + proxy routes to `src/backend/api/gateway/app/main.py` (see
  [Gateway](gateway.md#adding-a-new-service))
- Add the service to `src/infra/apis.yml` (API) or `src/infra/workers.yml` (worker)
- No CI changes needed — see [CI/CD](ci-cd.md#adding-a-new-service-to-ci)

## 9. Frontend module (if it needs a screen)

Add a route in `src/frontend/gio-faas-dashboard/src/main.tsx`, a metadata entry in
`src/nav.ts`, and a module component under `src/modules/{service}/`. Wrap loading
states in `<Skeleton name="..." loading={...}>` from `boneyard-js/react` where the
content is div-based (tables can't hold a `<Skeleton>`'s wrapper element without
breaking `<tbody>` — leave those with a plain spinner), then run
`npx boneyard-js build` against a running dev server to capture real bones before
shipping.
