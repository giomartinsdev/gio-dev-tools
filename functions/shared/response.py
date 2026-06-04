import json
import os


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
        # classic-watchdog exposes fd 200 for the function to write HTTP headers
        try:
            header_data = f"Status: {self.status_code}\n"
            for key, value in self.headers.items():
                header_data += f"{key}: {value}\n"
            os.write(200, header_data.encode())
        except OSError:
            pass

        def _serialize(obj):
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            return str(obj)

        if isinstance(self.body, (dict, list)):
            return json.dumps(self.body, default=_serialize)
        return str(self.body)
