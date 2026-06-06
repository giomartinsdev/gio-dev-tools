from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from src.main import main

app = FastAPI()


@app.post("/")
@app.post("/{path:path}")
async def handle(file: UploadFile = File(...)):
    return await main(file)

