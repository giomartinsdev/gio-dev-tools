from shared.auto_trace import install
install(["app"])
import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

import httpx

FAAS_GATEWAY_URL = os.environ.get("FAAS_GATEWAY_URL", "https://of.giomartins.dev")
CF_CLIENT_ID = os.environ["CF_ACCESS_CLIENT_ID"]
CF_CLIENT_SECRET = os.environ["CF_ACCESS_CLIENT_SECRET"]
PORT = int(os.environ.get("PORT", "3000"))
KANBAN_URL = os.environ.get("KANBAN_URL", "http://kanban:8000")
OBSIDIAN_URL = os.environ.get("OBSIDIAN_URL", "http://obsidian:8000")

_HOP_BY_HOP = {
    "connection", "keep-alive", "transfer-encoding",
    "te", "trailers", "upgrade", "proxy-authorization",
    "proxy-authenticate", "host",
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _forward(request: Request, target: str) -> Response:
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
            timeout=120.0,
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


async def _forward_internal(request: Request, target: str) -> Response:
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            content=await request.body(),
            params=request.query_params,
            timeout=120.0,
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


@app.api_route("/kanban", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/kanban/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_kanban(request: Request, path: str = ""):
    target = f"{KANBAN_URL}/{path}" if path else KANBAN_URL
    return await _forward_internal(request, target)


@app.api_route("/obsidian", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/obsidian/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_obsidian(request: Request, path: str = ""):
    target = f"{OBSIDIAN_URL}/{path}" if path else OBSIDIAN_URL
    return await _forward_internal(request, target)


@app.api_route("/fn/{function_name}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/fn/{function_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(function_name: str, request: Request, path: str = ""):
    target = f"{FAAS_GATEWAY_URL}/function/{function_name}"
    if path:
        target += f"/{path}"
    return await _forward(request, target)


@app.api_route("/fn-async/{function_name}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/fn-async/{function_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_async(function_name: str, request: Request, path: str = ""):
    target = f"{FAAS_GATEWAY_URL}/async-function/{function_name}"
    if path:
        target += f"/{path}"
    return await _forward(request, target)


@app.get("/health")
def health():
    return {
        "status": "OK",
        "faas_gateway_url": FAAS_GATEWAY_URL,
        "kanban_url": KANBAN_URL,
        "obsidian_url": OBSIDIAN_URL,
    }
