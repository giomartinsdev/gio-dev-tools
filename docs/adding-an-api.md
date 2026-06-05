# Adding an API

## 1. Create the directory

```
src/backend/api/{your-api}/
├── Dockerfile
└── ...
```

The CI pipeline detects any new subdirectory under `src/backend/api/` and builds it automatically.

## 2. Add a Dockerfile

The API can be any language or framework. Example for a FastAPI service:

```dockerfile
FROM re.giomartins.dev/python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

ENV PORT=3000
EXPOSE 3000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

## 3. Add environment variables (if needed)

In `.github/workflows/deploy-api.yml`, add a conditional block in the deploy step:

```yaml
if [ "${{ matrix.api }}" = "your-api" ]; then
  WEBHOOK_URL="${{ secrets.DOCKHAND_YOUR_API_WEBHOOK }}"
fi
```

Then add the `DOCKHAND_YOUR_API_WEBHOOK` secret in **GitHub → Settings → Secrets → Actions** with the Dockhand webhook URL for that service.

## 4. Add to the infra compose

In `src/infra/docker-compose.yml`, add the new service:

```yaml
your-api:
  image: re.giomartins.dev/your-api:latest
  ports:
    - "3003:3000"
  restart: unless-stopped
```

## 5. Deploy

Push any change under `src/backend/api/{your-api}/` to `main`. The CI pipeline detects the change, builds the image, pushes `re.giomartins.dev/{your-api}:latest`, and triggers the Dockhand redeploy.
