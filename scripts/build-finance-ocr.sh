#!/usr/bin/env bash
# Build and deploy finance-ocr directly on the server.
# Run from the repo root after git pull:
#
#   bash scripts/build-finance-ocr.sh
#
# Credentials are stored in ~/.faas-cf-creds after the first run.

set -euo pipefail

REGISTRY="${REGISTRY:-re.giomartins.dev}"
GATEWAY="${GATEWAY:-http://127.0.0.1:8080}"
FINANCE_URL="${FINANCE_URL:-https://of.giomartins.dev/function/finance}"
OTEL_ENDPOINT="${OTEL_ENDPOINT:-https://optel.giomartins.dev}"
SKIP_DEPLOY="${SKIP_DEPLOY:-0}"
FUNCTION="finance-ocr"
CREDS_FILE="$HOME/.faas-cf-creds"

# ---------------------------------------------------------------------------
# Load / prompt for CF credentials
# ---------------------------------------------------------------------------
if [[ -z "${CF_ACCESS_CLIENT_ID:-}" && -f "$CREDS_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CREDS_FILE"
    echo "==> Loaded credentials from $CREDS_FILE"
fi

if [[ -z "${CF_ACCESS_CLIENT_ID:-}" ]]; then
    echo "CF credentials not found. Enter them now (saved to $CREDS_FILE for future runs)."
    read -rp "CF_ACCESS_CLIENT_ID: " CF_ACCESS_CLIENT_ID
    read -rsp "CF_ACCESS_CLIENT_SECRET: " CF_ACCESS_CLIENT_SECRET
    echo ""

    {
        echo "CF_ACCESS_CLIENT_ID=$CF_ACCESS_CLIENT_ID"
        echo "CF_ACCESS_CLIENT_SECRET=$CF_ACCESS_CLIENT_SECRET"
    } > "$CREDS_FILE"
    chmod 600 "$CREDS_FILE"
    echo "==> Saved to $CREDS_FILE"
fi

export CF_ACCESS_CLIENT_ID CF_ACCESS_CLIENT_SECRET

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")
IMAGE_LATEST="$REGISTRY/$FUNCTION:latest"
IMAGE_SHA="$REGISTRY/$FUNCTION:$SHA"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTEXT="$REPO_ROOT/functions"
DOCKERFILE="$CONTEXT/$FUNCTION/Dockerfile"

if command -v docker &>/dev/null; then
    BUILD="docker"
elif command -v nerdctl &>/dev/null; then
    BUILD="nerdctl"
else
    echo "ERROR: neither docker nor nerdctl found." >&2
    exit 1
fi

echo "==> Build tool : $BUILD"
echo "==> Image      : $IMAGE_LATEST  (sha: $SHA)"
echo ""
echo "==> Building (first run downloads torch + model, may take a while)..."

$BUILD build \
    --file "$DOCKERFILE" \
    --build-arg "FUNCTION_DIR=$FUNCTION" \
    --tag "$IMAGE_LATEST" \
    --tag "$IMAGE_SHA" \
    "$CONTEXT"

echo ""
echo "==> Pushing images..."
$BUILD push "$IMAGE_LATEST"
$BUILD push "$IMAGE_SHA"

# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------
if [[ "$SKIP_DEPLOY" == "1" ]]; then
    echo "==> SKIP_DEPLOY=1 — skipping faas-cli deploy."
    exit 0
fi

echo ""
echo "==> Pulling image into openfaas-fn namespace..."
sudo ctr -n openfaas-fn images pull "$IMAGE_LATEST"

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
    --image "$IMAGE_LATEST" \
    --name "$FUNCTION" \
    --gateway "$GATEWAY" \
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
