from __future__ import annotations

import os
import tempfile
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from faster_whisper import WhisperModel

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")
DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

_model: WhisperModel | None = None


def _init(app: FastAPI) -> None:
    global _model
    try:
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    except Exception as e:
        app.state._init_error = e
    finally:
        app.state._init_done.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state._init_done = threading.Event()
    app.state._init_error = None
    threading.Thread(target=_init, args=(app,), daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    ready = app.state._init_done.is_set()
    error = app.state._init_error
    if error:
        return Response(status_code=503, content=f'{{"status":"error","detail":"{error}"}}', media_type="application/json")
    return {"status": "ok" if ready else "loading"}


# Formato de request/response compatível com o endpoint /v1/listen do Deepgram,
# para que clientes escritos contra a API do Deepgram funcionem sem alteração.
@app.post("/v1/listen")
async def listen(request: Request, language: str | None = None):
    if not app.state._init_done.is_set():
        return Response(status_code=503, content='{"error":"modelo ainda carregando"}', media_type="application/json")
    if app.state._init_error:
        return Response(status_code=503, content='{"error":"modelo falhou ao carregar"}', media_type="application/json")

    body = await request.body()
    lang = language if language and language != "multi" else "pt"

    with tempfile.NamedTemporaryFile(suffix=".webm") as f:
        f.write(body)
        f.flush()
        segments, _info = _model.transcribe(f.name, language=lang, vad_filter=True)
        transcript = "".join(seg.text for seg in segments).strip()

    return {
        "results": {
            "channels": [
                {"alternatives": [{"transcript": transcript}]}
            ]
        }
    }
