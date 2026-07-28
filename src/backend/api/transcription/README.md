# transcription

Self-hosted speech-to-text, built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
Exposes the same request/response shape as Deepgram's `/v1/listen` prerecorded
endpoint, so any client written against Deepgram's API (e.g.
[InRealTimeNotes](https://github.com/giomartinsdev/inrealtimenotes)) works against
it unmodified — just point the client's base URL here instead of
`api.deepgram.com`.

No persistence, no domain layer, no Infisical secret — it's a stateless model
wrapper, so it doesn't follow the DDD/CQRS shape the other services use (see
[Adding a service](../../../../docs/adding-a-service.md)); that pattern is for
services with actual domain state.

## API

### `POST /v1/listen`

- Body: raw audio bytes (any container `faster-whisper`/PyAV can decode — webm/opus,
  wav, mp3, ...)
- Query params: `language` (defaults to `pt`; anything else is passed through to
  Whisper's language hint)
- Response:
  ```json
  {
    "results": {
      "channels": [
        { "alternatives": [{ "transcript": "..." }] }
      ]
    }
  }
  ```

### `GET /health`

`{"status": "ok"}` once the model has finished loading, `{"status": "loading"}`
while it's still downloading/initializing, 503 if it failed to load.

## Config (env vars)

| Var | Default | Notes |
|---|---|---|
| `WHISPER_MODEL` | `small` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`) — bigger is more accurate and slower |
| `WHISPER_DEVICE` | `cpu` | Set to `cuda` if the host has a usable GPU |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8` for CPU, `float16`/`int8_float16` for GPU |

Model weights download from Hugging Face on first request and are cached in
`/model-cache` (mounted as the `transcription-model-cache` volume in
`src/infra/apis.yml`) — restarts don't re-download.

## Building and running manually

CI/CD for this repo is currently down (see [CI/CD](../../../../docs/ci-cd.md)), so
build and deploy by hand:

```bash
# from the repo root
docker build -f src/backend/api/transcription/Dockerfile -t re.giomartins.dev/transcription:latest src/backend
docker compose -f src/infra/apis.yml up -d transcription
```

Wired into the gateway at `/transcription/*` (see `src/backend/api/gateway/app/main.py`)
and into `src/infra/apis.yml` / `src/infra/utils.yml`.

To point a client at it through the gateway, use
`https://<your-gateway-host>/transcription` as the Deepgram-compatible base URL —
no API key required (the service doesn't check one).
