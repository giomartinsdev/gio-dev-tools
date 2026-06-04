import os
from fastapi import FastAPI, Request, Response

import httpx

FAAS_GATEWAY_URL = os.environ.get("FAAS_GATEWAY_URL", "https://of.giomartins.dev")
CF_CLIENT_ID = os.environ["CF_ACCESS_CLIENT_ID"]
CF_CLIENT_SECRET = os.environ["CF_ACCESS_CLIENT_SECRET"]
PORT = int(os.environ.get("PORT", "3000"))

_HOP_BY_HOP = {
    "connection", "keep-alive", "transfer-encoding",
    "te", "trailers", "upgrade", "proxy-authorization",
    "proxy-authenticate", "host",
}

app = FastAPI()


@app.api_route("/fn/{function_name}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/fn/{function_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(function_name: str, request: Request, path: str = ""):
    target = f"{FAAS_GATEWAY_URL}/function/{function_name}"
    if path:
        target += f"/{path}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
    headers["CF-Access-Client-Id"] = CF_CLIENT_ID
    headers["CF-Access-Client-Secret"] = CF_CLIENT_SECRET

    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            content=await request.body(),
            params=request.query_params,
            timeout=60.0,
        )

    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
