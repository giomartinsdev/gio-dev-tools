import json
import os
import uuid
from urllib.parse import parse_qs


class Request:
    function_id: str
    method: str
    path: str
    query_string: str
    query: dict[str, str | list[str]]
    headers: dict[str, str]
    _raw_body: str

    def __init__(self, raw_body: str) -> None:
        self.function_id = str(uuid.uuid4())
        self.method = os.environ.get("Http_Method", "GET").upper()
        self.path = os.environ.get("Http_Path", "/")
        self.query_string = os.environ.get("Http_Query", "")
        self.query = {
            k: v[0] if len(v) == 1 else v
            for k, v in parse_qs(self.query_string).items()
        }
        self.headers = {
            k[5:].replace("_", "-").title(): v
            for k, v in os.environ.items()
            if k.startswith("Http_")
            and k
            not in (
                "Http_Method",
                "Http_Path",
                "Http_Query",
            )
        }
        self._raw_body = raw_body

    @property
    def body(self) -> dict | list | str:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type and self._raw_body:
            try:
                return json.loads(self._raw_body)
            except json.JSONDecodeError:
                pass
        return self._raw_body

    def __repr__(self) -> str:
        return (
            f"Request("
            f"function_id={self.function_id!r}, "
            f"method={self.method!r}, "
            f"path={self.path!r}, "
            f"query={self.query!r}, "
            f"headers={self.headers!r}, "
            f"body={self.body!r}"
            f")"
        )
