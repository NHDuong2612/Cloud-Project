"""Fargate sample: all persistent data lives in the registered S3 prefix."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path


class StorageUnavailable(RuntimeError):
    pass


class Notes:
    def __init__(self, client, bucket, prefix):
        if not re.fullmatch(r"environments/[a-f0-9]{32}/data/", prefix):
            raise ValueError("Invalid registered data prefix")
        self.client, self.bucket, self.key = client, bucket, prefix + "note.json"

    def load(self):
        from botocore.exceptions import BotoCoreError, ClientError
        try:
            with self.client.get_object(Bucket=self.bucket, Key=self.key)["Body"] as stream:
                data = json.loads(stream.read())
            if not isinstance(data, dict) or set(data) != {"text"} or not isinstance(data["text"], str) or len(data["text"]) > 2000:
                raise ValueError("Invalid stored data")
            return data
        except (ClientError, BotoCoreError, ValueError):
            raise StorageUnavailable("STORAGE_UNAVAILABLE") from None

    def save(self, text):
        from botocore.exceptions import BotoCoreError, ClientError
        try:
            self.client.put_object(Bucket=self.bucket, Key=self.key, Body=json.dumps({"text": text}).encode(), ContentType="application/json", ServerSideEncryption="AES256")
        except (ClientError, BotoCoreError):
            raise StorageUnavailable("STORAGE_UNAVAILABLE") from None
        return {"text": text}

    def ensure(self):
        from botocore.exceptions import BotoCoreError, ClientError
        # Missing objects return 403 without ListBucket. A conditional write
        # initializes safely without widening the per-environment task role.
        for attempt in range(3):
            try:
                self.client.put_object(Bucket=self.bucket, Key=self.key, Body=b'{"text":""}', ContentType="application/json", ServerSideEncryption="AES256", IfNoneMatch="*")
                return
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code == "PreconditionFailed":
                    return  # Preserve existing or restored data.
                if code == "ConditionalRequestConflict" and attempt < 2:
                    continue
                raise StorageUnavailable("STORAGE_UNAVAILABLE") from None
            except BotoCoreError:
                raise StorageUnavailable("STORAGE_UNAVAILABLE") from None


def handler_for(notes):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def reply(self, status, value, mime="application/json"):
            data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                if self.path == "/health":
                    notes.load()
                    return self.reply(200, {"status": "ok"})
                if self.path == "/api/note":
                    return self.reply(200, notes.load())
                files = {"/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
                if self.path in files:
                    name, mime = files[self.path]
                    return self.reply(200, Path(__file__).with_name(name).read_text(encoding="utf-8"), mime)
                return self.reply(404, {"error": "NOT_FOUND"})
            except StorageUnavailable:
                return self.reply(503, {"error": "STORAGE_UNAVAILABLE"})

        def do_POST(self):
            if self.path != "/api/note":
                return self.reply(404, {"error": "NOT_FOUND"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192 or self.headers.get_content_type() != "application/json":
                    raise ValueError("Invalid request")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or set(body) != {"text"} or not isinstance(body["text"], str) or len(body["text"]) > 2000:
                    raise ValueError("Invalid note")
                return self.reply(200, notes.save(body["text"]))
            except (ValueError, UnicodeError):
                return self.reply(400, {"error": "INVALID_NOTE"})
            except StorageUnavailable:
                return self.reply(503, {"error": "STORAGE_UNAVAILABLE"})

    return Handler


def main():
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError
    notes = Notes(boto3.client("s3", config=Config(retries={"mode": "standard", "total_max_attempts": 3}, connect_timeout=3, read_timeout=5)), os.environ["DATA_BUCKET"], os.environ["DATA_PREFIX"])
    try:
        notes.ensure()
    except (StorageUnavailable, BotoCoreError):
        return 1
    server = ThreadingHTTPServer(("0.0.0.0", 8080), handler_for(notes))
    server.daemon_threads = True
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
