from shared.auto_trace import src  # noqa: F401
from fastapi import FastAPI, File, UploadFile
from src.main import main

app = FastAPI()


@app.post("/")
@app.post("/{path:path}")
async def handle(file: UploadFile = File(...)):
    return await main(file)

