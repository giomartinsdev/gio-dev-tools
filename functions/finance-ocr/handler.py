from shared.auto_trace import install
install(["src"])

from fastapi import FastAPI, UploadFile
from fastapi.requests import Request as FastAPIRequest
from fastapi.responses import JSONResponse
from src.main import main

app = FastAPI()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def handle(fastapi_request: FastAPIRequest, path: str = ""):
    if fastapi_request.method != "POST":
        return JSONResponse({"error": "method not allowed"}, status_code=405)

    form = await fastapi_request.form()
    file = form.get("file")

    if not isinstance(file, UploadFile):
        return JSONResponse({"error": "file field required"}, status_code=400)

    return await main(file)
