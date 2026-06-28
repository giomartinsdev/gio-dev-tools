import json
from unittest.mock import MagicMock, patch

from behave import given, then, use_step_matcher, when

use_step_matcher("re")


# ---------------------------------------------------------------------------
# Minimal request stub — avoids importing fastapi in the test environment
# ---------------------------------------------------------------------------

class FakeRequest:
    def __init__(self, method, query=None, raw_body=None):
        self.method = method
        self.path = "/"
        self.query_string = ""
        self.query = query or {}
        self.headers = {"content-type": "application/json"}
        self._raw_body = raw_body or ""

    @property
    def body(self):
        if self._raw_body:
            try:
                return json.loads(self._raw_body)
            except json.JSONDecodeError:
                pass
        return self._raw_body


def _make_request(method, query=None, body=None):
    raw = json.dumps(body) if body is not None else ""
    return FakeRequest(method=method, query=query or {}, raw_body=raw)


def _run(context):
    from src.main import main
    with patch("src.main.webdav", context.webdav_mock):
        context.response = main(context.request)


def _body(context):
    b = context.response.body
    if isinstance(b, str):
        return json.loads(b)
    return b


# ---------------------------------------------------------------------------
# Given
# ---------------------------------------------------------------------------

@given(r'the WebDAV directory "([^"]+)" contains a folder "([^"]+)" and a file "([^"]+)"')
def step_dir_folder_and_file(context, path, folder_name, file_name):
    context.webdav_mock = MagicMock()
    context.webdav_mock.list_directory.return_value = [
        {"name": folder_name, "path": f"{path}/{folder_name}", "is_dir": True, "size": 0, "modified": None},
        {"name": file_name, "path": f"{path}/{file_name}", "is_dir": False, "size": 100, "modified": None},
    ]


@given(r'the WebDAV directory "([^"]+)" contains a file "([^"]+)"')
def step_dir_single_file(context, path, file_name):
    context.webdav_mock = MagicMock()
    context.webdav_mock.list_directory.return_value = [
        {"name": file_name, "path": f"{path}/{file_name}", "is_dir": False, "size": 50, "modified": None},
    ]


@given(r'the WebDAV directory listing raises an error')
def step_dir_raises(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.list_directory.side_effect = ValueError("connection refused")


@given(r'the WebDAV file "([^"]+)" has content "([^"]+)"')
def step_file_content(context, path, content):
    context.webdav_mock = MagicMock()
    context.webdav_mock.read_file.return_value = content


@given(r'the WebDAV file read raises an error')
def step_read_raises(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.read_file.side_effect = ValueError("not found")


@given(r'the WebDAV write succeeds')
def step_write_succeeds(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.write_file.return_value = None


@given(r'the WebDAV mkdir succeeds')
def step_mkdir_succeeds(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.make_directory.return_value = None


@given(r'the WebDAV delete succeeds')
def step_delete_succeeds(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.delete_resource.return_value = None


@given(r'the WebDAV delete raises an error')
def step_delete_raises(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.delete_resource.side_effect = ValueError("forbidden")


@given(r'the WebDAV move succeeds')
def step_move_succeeds(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.move_resource.return_value = None


@given(r'the WebDAV move raises an error')
def step_move_raises(context):
    context.webdav_mock = MagicMock()
    context.webdav_mock.move_resource.side_effect = ValueError("conflict")


# ---------------------------------------------------------------------------
# When
# ---------------------------------------------------------------------------

@when(r'I send GET with path "([^"]+)" and type "([^"]+)"')
def step_get_path_type(context, path, type_):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("GET", query={"path": path, "type": type_})
    _run(context)


@when(r'I send GET with no path')
def step_get_no_path(context):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("GET", query={})
    _run(context)


@when(r'I send POST with path "([^"]+)" and content "([^"]*)"')
def step_post_create(context, path, content):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("POST", body={"action": "create", "path": path, "content": content})
    _run(context)


@when(r'I send POST with no path and content "([^"]*)"')
def step_post_no_path(context, content):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("POST", body={"action": "create", "path": "", "content": content})
    _run(context)


@when(r'I send POST mkdir with path "([^"]+)"')
def step_post_mkdir(context, path):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("POST", body={"action": "mkdir", "path": path})
    _run(context)


@when(r'I send PUT with path "([^"]+)" and content "([^"]*)"')
def step_put(context, path, content):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("PUT", body={"path": path, "content": content})
    _run(context)


@when(r'I send PUT with no path and content "([^"]*)"')
def step_put_no_path(context, content):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("PUT", body={"path": "", "content": content})
    _run(context)


@when(r'I send DELETE with path "([^"]+)"')
def step_delete_path(context, path):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("DELETE", body={"path": path})
    _run(context)


@when(r'I send DELETE with no path')
def step_delete_no_path(context):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("DELETE", body={"path": ""})
    _run(context)


@when(r'I send PATCH with from "([^"]*)" and to "([^"]*)"')
def step_patch_move(context, from_path, to_path):
    if not hasattr(context, "webdav_mock"):
        context.webdav_mock = MagicMock()
    context.request = _make_request("PATCH", body={"from": from_path, "to": to_path})
    _run(context)


# ---------------------------------------------------------------------------
# Then
# ---------------------------------------------------------------------------

@then(r'the response status is (\d+)')
def step_status(context, code):
    assert context.response.status_code == int(code), (
        f"Expected {code}, got {context.response.status_code}: {context.response.body}"
    )


@then(r'the response contains (\d+) entries')
def step_entry_count(context, count):
    body = _body(context)
    assert isinstance(body, list), f"Expected list, got {type(body)}"
    assert len(body) == int(count), f"Expected {count} entries, got {len(body)}"


@then(r'the first entry is a directory named "([^"]+)"')
def step_first_is_dir(context, name):
    entry = _body(context)[0]
    assert entry["is_dir"] is True, f"Expected is_dir=True: {entry}"
    assert entry["name"] == name, f"Expected name '{name}': {entry['name']}"


@then(r'the second entry is a file named "([^"]+)"')
def step_second_is_file(context, name):
    entry = _body(context)[1]
    assert entry["is_dir"] is False, f"Expected is_dir=False: {entry}"
    assert entry["name"] == name, f"Expected name '{name}': {entry['name']}"


@then(r'the response body has field "([^"]+)" equal to "([^"]+)"')
def step_body_field(context, field, value):
    body = _body(context)
    assert field in body, f"Field '{field}' not in body: {body}"
    assert str(body[field]) == value, f"Expected {field}='{value}', got '{body[field]}'"


@then(r'write_file was called with path "([^"]+)" and content "([^"]*)"')
def step_write_called(context, path, content):
    context.webdav_mock.write_file.assert_called_once_with(path, content)


@then(r'make_directory was called with path "([^"]+)"')
def step_mkdir_called(context, path):
    context.webdav_mock.make_directory.assert_called_once_with(path)


@then(r'delete_resource was called with path "([^"]+)"')
def step_delete_called(context, path):
    context.webdav_mock.delete_resource.assert_called_once_with(path)


@then(r'move_resource was called with from "([^"]+)" and to "([^"]+)"')
def step_move_called(context, from_path, to_path):
    context.webdav_mock.move_resource.assert_called_once_with(from_path, to_path)
