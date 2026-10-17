"""Small CRUD demo for a dedicated CloudHub RDS environment."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading
import time


class DatabaseUnavailable(RuntimeError):
    pass


class Database:
    def __init__(self, secrets, connect, db_error, host, secret_arn, ca_file):
        self.secrets, self.connect, self.db_error = secrets, connect, db_error
        self.host, self.secret_arn, self.ca_file = host, secret_arn, ca_file
        self.cache, self.cache_until = None, 0
        self.lock = threading.Lock()

    def connection(self):
        with self.lock:
            if not self.cache or time.monotonic() >= self.cache_until:
                self.cache = json.loads(self.secrets.get_secret_value(SecretId=self.secret_arn)["SecretString"])
                self.cache_until = time.monotonic() + 60
            credentials = self.cache
        return self.connect(host=self.host, dbname="cloudhub", user=credentials["username"], password=credentials["password"], sslmode="verify-full", sslrootcert=self.ca_file, connect_timeout=5)

    def execute(self, operation, task_id=None, title=None, done=None):
        try:
            with self.connection() as connection:
                if operation == "initialize":
                    connection.execute("CREATE TABLE IF NOT EXISTS tasks (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, title varchar(200) NOT NULL, done boolean NOT NULL DEFAULT false)")
                    return None
                if operation == "health":
                    connection.execute("CREATE TEMP TABLE cloudhub_probe (value integer) ON COMMIT DROP")
                    connection.execute("INSERT INTO cloudhub_probe VALUES (1)")
                    if connection.execute("SELECT value FROM cloudhub_probe").fetchone()[0] != 1:
                        raise DatabaseUnavailable("DATABASE_UNAVAILABLE")
                    return {"status": "ok", "database": "read-write"}
                if operation == "list":
                    rows = connection.execute("SELECT id,title,done FROM tasks ORDER BY id LIMIT 200").fetchall()
                elif operation == "create":
                    rows = connection.execute("INSERT INTO tasks(title) VALUES (%s) RETURNING id,title,done", (title,)).fetchall()
                elif operation == "update":
                    rows = connection.execute("UPDATE tasks SET done=%s WHERE id=%s RETURNING id,title,done", (done, task_id)).fetchall()
                elif operation == "delete":
                    rows = connection.execute("DELETE FROM tasks WHERE id=%s RETURNING id,title,done", (task_id,)).fetchall()
                else:
                    raise ValueError("Unknown database operation")
                return [{"id": row[0], "title": row[1], "done": row[2]} for row in rows]
        except self.db_error:
            with self.lock:
                self.cache_until = 0
            raise DatabaseUnavailable("DATABASE_UNAVAILABLE") from None


def handler_for(database):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Do not write request bodies, credentials or query errors to logs.
            return

        def respond(self, code, payload, content_type="application/json"):
            body = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096 or self.headers.get_content_type() != "application/json":
                raise ValueError("Invalid request body")
            result = json.loads(self.rfile.read(length))
            if not isinstance(result, dict):
                raise ValueError("Body must be an object")
            return result

        def dispatch(self):
            path = self.path.split("?", 1)[0]
            try:
                if self.command == "GET" and path in {"/", "/app.js", "/style.css"}:
                    name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[path]
                    mime = {"/": "text/html; charset=utf-8", "/app.js": "text/javascript", "/style.css": "text/css"}[path]
                    return self.respond(200, Path(__file__).with_name(name).read_text(encoding="utf-8"), mime)
                if self.command == "GET" and path == "/health":
                    return self.respond(200, database.execute("health"))
                if self.command == "GET" and path == "/api/tasks":
                    return self.respond(200, database.execute("list"))
                if self.command == "POST" and path == "/api/tasks":
                    data = self.body()
                    title = data.get("title")
                    if set(data) != {"title"} or not isinstance(title, str) or not 1 <= len(title.strip()) <= 200:
                        raise ValueError("Invalid title")
                    return self.respond(201, database.execute("create", title=title.strip())[0])
                match = re.fullmatch(r"/api/tasks/([1-9][0-9]{0,17})", path)
                if match and self.command in {"PATCH", "DELETE"}:
                    task_id = int(match[1])
                    if self.command == "PATCH":
                        data = self.body()
                        if set(data) != {"done"} or type(data["done"]) is not bool:
                            raise ValueError("Invalid done flag")
                        result = database.execute("update", task_id=task_id, done=data["done"])
                    else:
                        result = database.execute("delete", task_id=task_id)
                    return self.respond(200 if result else 404, result[0] if result else {"error": "NOT_FOUND"})
                return self.respond(404, {"error": "NOT_FOUND"})
            except (ValueError, UnicodeError):
                return self.respond(400, {"error": "INVALID_REQUEST"})
            except DatabaseUnavailable:
                return self.respond(503, {"error": "DATABASE_UNAVAILABLE"})

        do_GET = do_POST = do_PATCH = do_DELETE = dispatch

    return Handler


def main():
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
    import psycopg
    database = Database(boto3.client("secretsmanager", config=Config(retries={"mode": "standard", "total_max_attempts": 3}, connect_timeout=3, read_timeout=5)), psycopg.connect, (psycopg.Error, ClientError, BotoCoreError), os.environ["DB_HOST"], os.environ["DB_SECRET_ARN"], os.environ["DB_CA_FILE"])
    try:
        database.execute("initialize")
    except DatabaseUnavailable:
        # systemd retries without a traceback that might contain a connection string.
        return 1
    server = ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), handler_for(database))
    server.daemon_threads = True
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
