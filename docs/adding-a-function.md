# Adding a function

## 1. Scaffold the directory

```
functions/{your-fn}/
├── handler.py
├── requirements.txt
└── src/
    └── main.py
```

Copy `handler.py` from any existing function — it never changes:

```python
from shared.auto_trace import install
install(["src"])

from fastapi import FastAPI
from fastapi.requests import Request as FastAPIRequest
from shared.request import Request
from src.main import main

app = FastAPI()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def handle(fastapi_request: FastAPIRequest):
    req = await Request.from_http(fastapi_request)
    res = main(req).send()
    return res
```

## 2. Implement `src/main.py`

The entry point must be a `main(request: Request) -> Response` function.

```python
from shared.request import Request
from shared.response import Response
from shared.logger import get_logger

logger = get_logger(__name__)

def main(request: Request) -> Response:
    return Response(body={"message": "hello"}, status_code=200)
```

For non-trivial functions, use DDD layers under `src/`:

```
src/
├── domain/          # Value objects and entities (pure Python, no I/O)
├── application/     # Use cases — orchestrate domain + infrastructure
├── infrastructure/  # HTTP clients, external APIs
└── main.py          # Wires everything, handles 400/500 responses
```

See `functions/wp-message/` for a complete example.

## 3. Add dependencies

List only function-specific packages in `requirements.txt`. Base dependencies (fastapi, uvicorn, opentelemetry) are installed in the shared base image.

## 4. Add environment variables (if needed)

In `.github/workflows/deploy.yml`, add a conditional block in the deploy step:

```yaml
if [ "${{ matrix.function }}" = "your-fn" ]; then
  EXTRA_ENVS="--env YOUR_VAR=${{ secrets.YOUR_VAR }}"
fi
```

Then add the corresponding secret in **GitHub → Settings → Secrets → Actions**.

## 5. Deploy

Push any change under `functions/{your-fn}/` to `main`. The CI pipeline will detect the change, build the image, push it to `re.giomartins.dev/{your-fn}:latest`, and deploy it to faasd automatically.

## 6. Call via gateway

```
POST https://<gateway>/fn/{your-fn}
```
