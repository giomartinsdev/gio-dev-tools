# Adding a frontend

## 1. Create the directory

```
src/frontend/{your-app}/
├── Dockerfile
├── nginx.conf
└── ...
```

The CI pipeline detects any new subdirectory under `src/frontend/` and builds it automatically.

## 2. Add a Dockerfile

Copy from `src/frontend/gio-faas-dashboard/Dockerfile` as a starting point:

```dockerfile
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_GATEWAY_URL=https://gateway.giomartins.dev
ENV VITE_GATEWAY_URL=${VITE_GATEWAY_URL}
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

## 3. Wire the Dockhand webhook

In `.github/workflows/deploy-frontends.yml`, add a conditional block in the deploy step:

```yaml
if [ "${{ matrix.frontend }}" = "your-app" ]; then
  WEBHOOK_URL="${{ secrets.DOCKHAND_YOUR_APP_WEBHOOK }}"
fi
```

Then add the `DOCKHAND_YOUR_APP_WEBHOOK` secret in **GitHub → Settings → Secrets → Actions** with the Dockhand webhook URL for that service.

## 4. Add to the infra compose

In `src/infra/docker-compose.yml`, add the new service:

```yaml
your-app:
  image: re.giomartins.dev/your-app:latest
  ports:
    - "8080:80"
  restart: unless-stopped
```

## 5. Deploy

Push any change under `src/frontend/{your-app}/` to `main`. The CI pipeline detects the change, builds the image, pushes `re.giomartins.dev/{your-app}:latest`, and triggers the Dockhand redeploy.
