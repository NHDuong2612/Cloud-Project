import http.client
from http.server import ThreadingHTTPServer
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import threading
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError


spec = importlib.util.spec_from_file_location("container_app", Path(__file__).resolve().parents[1] / "apps/container/server.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
PREFIX = "environments/" + "a" * 32 + "/data/"


def test_stored_note_stream_is_closed_and_scope_cannot_escape_environment():
    client = Mock()
    stream = BytesIO(b'{"text":"saved"}')
    client.get_object.return_value = {"Body": stream}
    notes = app.Notes(client, "bucket", PREFIX)
    assert notes.load() == {"text": "saved"}
    assert stream.closed
    assert client.get_object.call_args.kwargs["Key"] == PREFIX + "note.json"
    with pytest.raises(ValueError):
        app.Notes(client, "bucket", "environments/../../outside/data/")


def test_initialization_never_overwrites_existing_or_concurrently_created_data():
    client = Mock()
    client.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    client.put_object.side_effect = ClientError({"Error": {"Code": "PreconditionFailed"}}, "PutObject")
    app.Notes(client, "bucket", PREFIX).ensure()
    assert client.put_object.call_args.kwargs["IfNoneMatch"] == "*"
    existing = Mock()
    existing.get_object.return_value = {"Body": BytesIO(b'{"text":"keep"}')}
    app.Notes(existing, "bucket", PREFIX).ensure()
    existing.put_object.assert_not_called()


def test_invalid_stored_data_fails_readiness():
    client = Mock()
    client.get_object.return_value = {"Body": BytesIO(b'{"unexpected":true}')}
    with pytest.raises(app.StorageUnavailable):
        app.Notes(client, "bucket", PREFIX).load()


def test_note_http_validation_and_storage_failure():
    notes = Mock()
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.handler_for(notes))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def request(method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        connection.request(method, path, json.dumps(body) if body is not None else None, {"Content-Type": "application/json"})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result
    try:
        assert request("POST", "/api/note", {"text": "x" * 2001})[0] == 400
        notes.save.assert_not_called()
        notes.save.return_value = {"text": "hello"}
        assert request("POST", "/api/note", {"text": "hello"}) == (200, {"text": "hello"})
        notes.load.side_effect = app.StorageUnavailable("do not expose AWS credentials")
        assert request("GET", "/health") == (503, {"error": "STORAGE_UNAVAILABLE"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
