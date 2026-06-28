from shared.logger import get_logger
from shared.request import Request
from shared.response import Response

from . import webdav

logger = get_logger(__name__)


def main(request: Request) -> Response:
    try:
        body = request.body if isinstance(request.body, dict) else {}

        if request.method == "GET":
            path = request.query.get("path", "gio")
            if request.query.get("type") == "file":
                return _read_file(str(path))
            return _list_dir(str(path))

        if request.method == "POST":
            action = body.get("action", "create")
            if action == "mkdir":
                return _make_dir(body)
            return _create_file(body)

        if request.method == "PUT":
            return _update_file(body)

        if request.method == "DELETE":
            return _delete(body)

        if request.method == "PATCH":
            return _move(body)

        return Response(body={"error": "method not allowed"}, status_code=405)

    except ValueError as e:
        return Response(body={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"unhandled error: {e}", exc_info=True)
        return Response(body={"error": "internal server error"}, status_code=500)


def _list_dir(path: str) -> Response:
    entries = webdav.list_directory(path)
    return Response(body=entries, status_code=200)


def _read_file(path: str) -> Response:
    content = webdav.read_file(path)
    return Response(body={"content": content, "path": path}, status_code=200)


def _create_file(body: dict) -> Response:
    path = str(body.get("path", ""))
    content = str(body.get("content", ""))
    if not path:
        raise ValueError("path is required")
    webdav.write_file(path, content)
    return Response(body={"created": True, "path": path}, status_code=201)


def _update_file(body: dict) -> Response:
    path = str(body.get("path", ""))
    content = str(body.get("content", ""))
    if not path:
        raise ValueError("path is required")
    webdav.write_file(path, content)
    return Response(body={"updated": True, "path": path}, status_code=200)


def _delete(body: dict) -> Response:
    path = str(body.get("path", ""))
    if not path:
        raise ValueError("path is required")
    webdav.delete_resource(path)
    return Response(body={"deleted": True}, status_code=200)


def _move(body: dict) -> Response:
    from_path = str(body.get("from", ""))
    to_path = str(body.get("to", ""))
    if not from_path or not to_path:
        raise ValueError("from and to are required")
    webdav.move_resource(from_path, to_path)
    return Response(body={"moved": True}, status_code=200)


def _make_dir(body: dict) -> Response:
    path = str(body.get("path", ""))
    if not path:
        raise ValueError("path is required")
    webdav.make_directory(path)
    return Response(body={"created": True, "path": path}, status_code=201)
