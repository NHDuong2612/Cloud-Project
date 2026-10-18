from hashlib import sha256
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


spec = importlib.util.spec_from_file_location("workload_probe", Path("scripts/workload_probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
MARKER = "cloudhub-verification-" + "a" * 32


def test_crud_marker_can_be_compared_without_writing_to_restore():
    fetch = Mock(side_effect=[{"status": "ok"}, {"id": 1}, [{"title": MARKER}]])
    assert probe.probe("https://lab.example.com", "T03", marker=MARKER, write=True, requester=fetch)["data_verified"]
    fetch.assert_any_call("POST", "/api/tasks", {"title": MARKER})
    fetch = Mock(side_effect=[{"status": "ok"}, [{"title": MARKER}]])
    assert probe.probe("https://restored.example.com", "T03", marker=MARKER, requester=fetch)["data_verified"]
    assert all(x.args[0] == "GET" for x in fetch.call_args_list)


def test_container_restore_mismatch_fails_without_overwriting_note():
    fetch = Mock(side_effect=[{"status": "ok"}, {"text": "other"}])
    assert not probe.probe("https://lab.example.com", "T06", marker=MARKER, requester=fetch)["data_verified"]
    assert all(x.args[0] == "GET" for x in fetch.call_args_list)


def test_website_content_is_compared_by_digest():
    fetch = Mock(side_effect=[{"status": "ok"}, b"restored website"])
    assert probe.probe("http://localhost:8080", "T05", allow_http=True, expected_sha256=sha256(b"restored website").hexdigest(), requester=fetch)["data_verified"]


@pytest.mark.parametrize("url", ["ftp://host", "https://user:password@host", "http://host", "https://host/?token=secret", "https://host/api"])
def test_unsafe_or_ambiguous_origin_is_rejected_before_request(url):
    fetch = Mock()
    with pytest.raises(ValueError):
        probe.probe(url, "T03", marker=MARKER, requester=fetch)
    fetch.assert_not_called()


def test_read_only_probe_cannot_initialize_missing_marker():
    with pytest.raises(ValueError):
        probe.probe("https://host", "T06", requester=Mock())


def test_http_transport_does_not_follow_redirects():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            requests.append(self.path)
            self.send_response(302)
            self.send_header("Location", "/unexpected")
            self.end_headers()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(ValueError, match="Redirects"):
            probe.request(f"http://127.0.0.1:{server.server_port}", "GET", "/health")
        assert requests == ["/health"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
