#!/usr/bin/env bash
# Build and deploy finance-ocr directly on the server.
# Run from the repo root after git pull:
#
#   bash scripts/build-finance-ocr.sh
#
# Pushes to localhost:5000 (bypasses Cloudflare upload limit).
# The deploy still uses re.giomartins.dev (pulling works fine through Cloudflare).
# Credentials are stored in ~/.faas-cf-creds after the first run.

set -euo pipefail

LOCAL_REGISTRY="localhost:5000"
REMOTE_REGISTRY="${REGISTRY:-re.giomartins.dev}"
GATEWAY="${GATEWAY:-http://127.0.0.1:8080}"
FINANCE_URL="${FINANCE_URL:-https://of.giomartins.dev/function/finance}"
OTEL_ENDPOINT="${OTEL_ENDPOINT:-https://optel.giomartins.dev}"
SKIP_DEPLOY="${SKIP_DEPLOY:-0}"
FUNCTION="finance-ocr"
CREDS_FILE="$HOME/.faas-cf-creds"

# ---------------------------------------------------------------------------
# Load / prompt for credentials
# ---------------------------------------------------------------------------
if [[ -f "$CREDS_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CREDS_FILE"
    echo "==> Loaded credentials from $CREDS_FILE"
fi

_need_creds=0
[[ -z "${CF_ACCESS_CLIENT_ID:-}"  ]] && _need_creds=1
[[ -z "${REGISTRY_USER:-}"        ]] && _need_creds=1
[[ -z "${REGISTRY_PASSWORD:-}"    ]] && _need_creds=1

if [[ "$_need_creds" == "1" ]]; then
    echo "Some credentials are missing. Enter them now (saved to $CREDS_FILE)."
    [[ -z "${CF_ACCESS_CLIENT_ID:-}"  ]] && read -rp  "CF_ACCESS_CLIENT_ID:     " CF_ACCESS_CLIENT_ID
    [[ -z "${CF_ACCESS_CLIENT_SECRET:-}" ]] && read -rsp "CF_ACCESS_CLIENT_SECRET: " CF_ACCESS_CLIENT_SECRET && echo ""
    [[ -z "${REGISTRY_USER:-}"        ]] && read -rp  "REGISTRY_USER:           " REGISTRY_USER
    [[ -z "${REGISTRY_PASSWORD:-}"    ]] && read -rsp "REGISTRY_PASSWORD:       " REGISTRY_PASSWORD && echo ""

    {
        echo "CF_ACCESS_CLIENT_ID=$CF_ACCESS_CLIENT_ID"
        echo "CF_ACCESS_CLIENT_SECRET=$CF_ACCESS_CLIENT_SECRET"
        echo "REGISTRY_USER=$REGISTRY_USER"
        echo "REGISTRY_PASSWORD=$REGISTRY_PASSWORD"
    } > "$CREDS_FILE"
    chmod 600 "$CREDS_FILE"
    echo "==> Saved to $CREDS_FILE"
fi

export CF_ACCESS_CLIENT_ID CF_ACCESS_CLIENT_SECRET REGISTRY_USER REGISTRY_PASSWORD

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")

# Push to localhost:5000 to bypass Cloudflare's upload limit.
# Pull / deploy still reference re.giomartins.dev (same registry, download is fine).
LOCAL_IMAGE_LATEST="$LOCAL_REGISTRY/$FUNCTION:latest"
LOCAL_IMAGE_SHA="$LOCAL_REGISTRY/$FUNCTION:$SHA"
REMOTE_IMAGE_LATEST="$REMOTE_REGISTRY/$FUNCTION:latest"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTEXT="$REPO_ROOT/functions"
DOCKERFILE="$CONTEXT/$FUNCTION/Dockerfile"

if [[ ! -d "$CONTEXT" ]]; then
    echo "ERROR: could not find functions/ dir at $CONTEXT" >&2
    exit 1
fi

if command -v docker &>/dev/null; then
    BUILD="docker"
elif command -v nerdctl &>/dev/null; then
    BUILD="nerdctl"
else
    echo "ERROR: neither docker nor nerdctl found." >&2
    exit 1
fi

echo "==> Build tool  : $BUILD"
echo "==> Local push  : $LOCAL_IMAGE_LATEST"
echo "==> Deploy ref  : $REMOTE_IMAGE_LATEST"
echo ""

# ---------------------------------------------------------------------------
# Login to local registry
# ---------------------------------------------------------------------------
echo "==> Logging in to $LOCAL_REGISTRY..."
echo "$REGISTRY_PASSWORD" | $BUILD login "$LOCAL_REGISTRY" \
    --username "$REGISTRY_USER" --password-stdin

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
echo ""
echo "==> Building (first run downloads torch + model, may take a while)..."

$BUILD build \
    --file "$DOCKERFILE" \
    --build-arg "FUNCTION_DIR=$FUNCTION" \
    --tag "$LOCAL_IMAGE_LATEST" \
    --tag "$LOCAL_IMAGE_SHA" \
    "$CONTEXT"

# ---------------------------------------------------------------------------
# Push to localhost:5000 (same registry as re.giomartins.dev, but bypasses
# Cloudflare so there's no 413 on large layers)
# ---------------------------------------------------------------------------
echo ""
echo "==> Pushing to $LOCAL_REGISTRY (bypassing Cloudflare)..."
$BUILD push "$LOCAL_IMAGE_LATEST"
$BUILD push "$LOCAL_IMAGE_SHA"

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
if [[ "$SKIP_DEPLOY" == "1" ]]; then
    echo "==> SKIP_DEPLOY=1 — skipping faas-cli deploy."
    exit 0
fi

echo ""
echo "==> Pulling image into openfaas-fn namespace (via $REMOTE_REGISTRY)..."
sudo ctr -n openfaas-fn images pull \
    --user "$REGISTRY_USER:$REGISTRY_PASSWORD" \
    "$REMOTE_IMAGE_LATEST"

echo "==> Removing existing function (if any)..."
faas-cli remove "$FUNCTION" --gateway "$GATEWAY" 2>/dev/null || true

echo "==> Waiting for container cleanup..."
for i in $(seq 1 30); do
    if ! sudo ctr -n openfaas-fn containers list | grep -q "^${FUNCTION}"; then
        echo "    Clean after ${i}s"
        break
    fi
    echo "    Waiting... ${i}s"
    sleep 1
done

sudo ctr -n openfaas-fn snapshots rm "${FUNCTION}-snapshot" 2>/dev/null || true

echo "==> Deploying $FUNCTION..."
faas-cli deploy \
    --image "$REMOTE_IMAGE_LATEST" \
    --name "$FUNCTION" \
    --gateway "$GATEWAY" \
    --env "read_timeout=120s" \
    --env "write_timeout=120s" \
    --env "exec_timeout=120s" \
    --env "CF_ACCESS_CLIENT_ID=$CF_ACCESS_CLIENT_ID" \
    --env "CF_ACCESS_CLIENT_SECRET=$CF_ACCESS_CLIENT_SECRET" \
    --env "FINANCE_URL=$FINANCE_URL" \
    --env "OTEL_EXPORTER_OTLP_ENDPOINT=$OTEL_ENDPOINT" \
    --env "OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf" \
    --env "OTEL_EXPORTER_OTLP_HEADERS=CF-Access-Client-Id=$CF_ACCESS_CLIENT_ID,CF-Access-Client-Secret=$CF_ACCESS_CLIENT_SECRET" \
    --env "OTEL_SERVICE_NAME=$FUNCTION" \
    --env "OTEL_TRACES_EXPORTER=otlp" \
    --env "OTEL_METRICS_EXPORTER=none" \
    --env "OTEL_LOGS_EXPORTER=none" \
    --env "OTEL_PYTHON_LOG_CORRELATION=true"

echo ""
echo "==> Done! finance-ocr deployed."
