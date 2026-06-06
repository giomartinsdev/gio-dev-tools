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
    