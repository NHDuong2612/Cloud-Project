import http.client
from http.server import ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import threading
from unittest.mock import Mock

import pytest


spec = importlib.util.spec_from_file_location("crud_app", Path(__file__).resolve().parents[1] / "apps/crud/server.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


@pytest.fixture
def api():
    database = Mock()
    database.execute.return_value = [{"id": 1, "title": "Learn", "done": False}]
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.handler_for(database))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def request(method, path, payload=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        conn.request(method, path, body=json.dumps(payload) if payload is not None else None, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        body = response.read()
        status = response.status
        conn.close()
        return status, json.loads(body)
    yield request, database
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_crud_http_contract(api):
    request, database = api
    assert request("POST", "/api/tasks", {"title": "Learn"})[0] == 201
    assert request("GET", "/api/tasks")[0] == 200
    assert request("PATCH", "/api/tasks/1", {"done": True})[0] == 200
    assert request("DELETE", "/api/tasks/1")[0] == 200
    database.execute.assert_any_call("create", title="Learn")
    database.execute.assert_any_call("update", task_id=1, done=True)


@pytest.mark.parametrize("method,path,payload", [("POST", "/api/tasks", {"title": ""}), ("POST", "/api/tasks", {"title": "a" * 201}), ("POST", "/api/tasks", {"title": "x", "sql": "evil"}), ("PATCH", "/api/tasks/1", {"done": "true"})])
def test_bad_requests_never_reach_database(api, method, path, payload):
    request, database = api
    assert request(method, path, payload)[0] == 400
    database.execute.assert_not_called()


def test_database_error_is_sanitized(api):
    request, database = api
    database.execute.side_effect = app.DatabaseUnavailable("sensitive database details")
    status, body = request("GET", "/health")
    assert status == 503
    assert body == {"error": "DATABASE_UNAVAILABLE"}


def test_sql_is_parameterized_and_tls_verifies_the_server():
    secret = Mock()
    secret.get_secret_value.return_value = {"SecretString": json.dumps({"username": "demo", "password": "synthetic-test-value"})}
    connection = Mock()
    connection.__enter__ = Mock(return_value=connection)
    connection.__exit__ = Mock(return_value=False)
    connection.execute.return_value.fetchall.return_value = [(1, "anything", False)]
    connect = Mock(return_value=connection)
    database = app.Database(secret, connect, RuntimeError, "db.example", "test-secret-arn", "ca.pem")
    attack = "'); DROP TABLE tasks; --"
    database.execute("create", title=attack)
    sql, parameters = connection.execute.call_args.args
    assert attack not in sql and parameters == (attack,)
    assert connect.call_args.kwargs["sslmode"] == "verify-full"
    assert connect.call_args.kwargs["sslrootcert"] == "ca.pem"
