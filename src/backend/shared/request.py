from __future__ import annotations

import json
import uuid
from fastapi import Request as FastAPIRequest


class Request:
    function_id: str
    method: str
    path: str
    query_string: str
    query: dict[str, str | list[str]]
    headers: dict[str, str]
    _raw_body: str

    def __init__(
        self,
        *,
        method: str,
        path: str,
        query_string: str,
        query: dict[str, str | list[str]],
        headers: dict[str, str],
        raw_body: str,
    ) -> None:
        self.function_id = str(uuid.uuid4())
        self.method = method
        self.path = path
        self.query_string = query_string
        self.query = query
        self.headers = headers
        self._raw_body = raw_body

    @classmethod
    async def from_http(cls, fastapi_request: FastAPIRequest) -> "Request":
        raw_body = await fastapi_request.body()
        return cls(
            method=fastapi_request.method,
            path=fastapi_request.url.path,
            query_string=str(fastapi_request.url.query),
            query=dict(fastapi_request.query_params),
            headers=dict(fastapi_request.headers),
            raw_body=raw_body.decode(),
        )

    @property
    def body(self) -> dict | list | str:
        content_type = self.headers.get("content-type", "")
        if "application/json" in content_type and self._raw_body:
            try:
                return json.loads(self._raw_body)
            except json.JSONDecodeError:
                pass
        return self._raw_body

    def to_dict(self) -> dict:
        return {
            "function_id": self.function_id,
            "method": self.method,
            "path": self.path,
            "query_string": self.query_string,
            "query": self.query,
            "headers": self.headers,
            "body": self.body,
        }

    def __repr__(self) -> str:
        return json.dumps(self.to_dict(), default=str)
