import threading
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urlparse

import httpx
from shared.secret_manager import SecretManager

_sm = SecretManager()
_webdav_url: str | None = None
_webdav_user: str | None = None
_webdav_password: str | None = None
_init_done = threading.Event()

_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<D:propfind xmlns:D="DAV:">'
    "<D:prop><D:resourcetype/><D:getcontentlength/><D:getlastmodified/></D:prop>"
    "</D:propfind>"
)


def _ensure_init() -> None:
    global _webdav_url, _webdav_user, _webdav_password
    if _webdav_url is None:
        _webdav_url = _sm.get_secret("WEBDAV_URL").rstrip("/")
        _webdav_user = _sm.get_secret("WEBDAV_USER")
        _webdav_password = _sm.get_secret("WEBDAV_PASSWORD")


def _prefetch() -> None:
    try:
        _ensure_init()
    except Exception:
        pass
    finally:
        _init_done.set()


threading.Thread(target=_prefetch, daemon=True).start()


def _auth() -> httpx.DigestAuth:
    _init_done.wait()
    _ensure_init()
    return httpx.DigestAuth(_webdav_user, _webdav_password)


def _url(path: str) -> str:
    _init_done.wait()
    _ensure_init()
    parts = [quote(p, safe="") for p in path.strip("/").split("/") if p]
    return f"{_webdav_url}/{'/'.join(parts)}"


def _parse_href(href: str) -> str:
    _init_done.wait()
    _ensure_init()
    parsed = urlparse(href)
    raw_path = parsed.path if parsed.scheme else href

    base_path = urlparse(_webdav_url).path.rstrip("/")
    if base_path and raw_path.startswith(base_path + "/"):
        raw_path = raw_path[len(base_path):]
    elif base_path and raw_path == base_path:
        raw_path = "/"

    return unquote(raw_path).strip("/")


def list_directory(path: str) -> list[dict]:
    url = _url(path) + "/"
    with httpx.Client() as client:
        resp = client.request(
            "PROPFIND",
            url,
            headers={"Depth": "1", "Content-Type": "application/xml"},
            content=_PROPFIND_BODY.encode(),
            auth=_auth(),
            timeout=30,
        )
    if resp.status_code != 207:
        raise ValueError(f"list_directory failed: {resp.status_code} {resp.text[:200]}")

    root = ET.fromstring(resp.content)
    ns = {"D": "DAV:"}
    request_path = path.strip("/")
    entries = []

    for response in root.findall("D:response", ns):
        href = response.findtext("D:href", namespaces=ns) or ""
        entry_path = _parse_href(href)

        if entry_path == request_path or not entry_path:
            continue

        propstat = response.find("D:propstat", ns)
        if propstat is None:
            continue
        prop = propstat.find("D:prop", ns)
        if prop is None:
            continue

        resourcetype = prop.find("D:resourcetype", ns)
        is_dir = resourcetype is not None and resourcetype.find("D:collection", ns) is not None

        name = entry_path.split("/")[-1]
        size_text = prop.findtext("D:getcontentlength", namespaces=ns)
        modified = prop.findtext("D:getlastmodified", namespaces=ns)

        entries.append({
            "name": name,
            "path": entry_path,
            "is_dir": is_dir,
            "size": int(size_text) if size_text else 0,
            "modified": modified,
        })

    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    return entries


def read_file(path: str) -> str:
    with httpx.Client() as client:
        resp = client.get(_url(path), auth=_auth(), timeout=30)
    if resp.status_code != 200:
        raise ValueError(f"read_file failed: {resp.status_code}")
    return resp.text


def write_file(path: str, content: str) -> None:
    with httpx.Client() as client:
        resp = client.put(
            _url(path),
            auth=_auth(),
            content=content.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            timeout=30,
        )
    if resp.status_code not in (200, 201, 204):
        raise ValueError(f"write_file failed: {resp.status_code}")


def delete_resource(path: str) -> None:
    with httpx.Client() as client:
        resp = client.delete(_url(path), auth=_auth(), timeout=30)
    if resp.status_code not in (200, 204):
        raise ValueError(f"delete_resource failed: {resp.status_code}")


def move_resource(from_path: str, to_path: str) -> None:
    destination = _url(to_path)
    with httpx.Client() as client:
        resp = client.request(
            "MOVE",
            _url(from_path),
            auth=_auth(),
            headers={"Destination": destination, "Overwrite": "T"},
            timeout=30,
        )
    if resp.status_code not in (200, 201, 204):
        raise ValueError(f"move_resource failed: {resp.status_code}")


def make_directory(path: str) -> None:
    with httpx.Client() as client:
        resp = client.request(
            "MKCOL",
            _url(path) + "/",
            auth=_auth(),
            timeout=30,
        )
    if resp.status_code not in (200, 201, 204):
        raise ValueError(f"make_directory failed: {resp.status_code}")
