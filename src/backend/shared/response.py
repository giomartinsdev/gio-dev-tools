from __future__ import annotations

import json
from fastapi.responses import JSONResponse


class Response:
    status_code: int
    headers: dict[str, str]
    body: dict | list | str

    def __init__(
        self,
        body: dict | list | str,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body

    def send(self) -> JSONResponse:
        def _serialize(obj):
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            return str(obj)

        body = (
            json.loads(json.dumps(self.body, default=_serialize))
            if isinstance(self.body, (dict, list))
            else self.body
        )

        return JSONResponse(
            content=body,
            status_code=self.status_code,
            headers=self.headers,
        )
