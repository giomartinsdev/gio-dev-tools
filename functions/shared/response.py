import json


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
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.body = body

    def send(self) -> str:
        def _serialize(obj):
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            return str(obj)

        return json.dumps({
            "statusCode": self.status_code,
            "headers": self.headers,
            "body": self.body,
        }, default=_serialize)
