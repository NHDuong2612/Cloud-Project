"""Check demo workloads and compare a marker before/after restore.

Writing is explicit and intended only for dedicated verification workloads.
No AWS credentials are used; HTTPS certificates are verified by urllib.
"""
import argparse
from hashlib import sha256
import json
import re
import secrets
from time import perf_counter
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirects are not allowed for workload probes")


def request(base, method, path, payload=None, raw=False):
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with build_opener(NoRedirect()).open(req, timeout=10) as response:
        if urlsplit(response.url).netloc != urlsplit(base).netloc or urlsplit(response.url).scheme != urlsplit(base).scheme:
            raise ValueError("Unexpected redirect")
        body = response.read(1_048_577)
        if len(body) > 1_048_576:
            raise ValueError("Response too large")
    return body if raw else json.loads(body)


def probe(url, template, *, marker=None, write=False, allow_http=False, expected_sha256=None, requester=None):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("Use a workload origin without credentials, path or query")
    if parsed.scheme == "http" and not allow_http:
        raise ValueError("HTTP requires explicit --allow-http for a controlled lab or SSM tunnel")
    if template not in {"T03", "T04", "T05", "T06"}:
        raise ValueError("Unsupported workload")
    if template == "T05" and (write or marker):
        raise ValueError("Website probe only reads content")
    if template != "T05":
        marker = marker or ("cloudhub-verification-" + secrets.token_hex(16) if write else None)
        if not marker or not re.fullmatch(r"cloudhub-verification-[a-f0-9]{32}", marker):
            raise ValueError("Supply the marker from the source verification result")
    if expected_sha256 and (template != "T05" or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256)):
        raise ValueError("Website comparison requires a SHA256 digest")
    fetch = requester or (lambda method, path, payload=None, raw=False: request(url.rstrip("/"), method, path, payload, raw))
    started = perf_counter()
    if fetch("GET", "/health").get("status") != "ok":
        raise ValueError("Workload is not healthy")
    result = {"template": template, "health": "ok"}
    if template == "T05":
        digest = sha256(fetch("GET", "/", raw=True)).hexdigest()
        result.update(content_sha256=digest, data_verified=not expected_sha256 or digest == expected_sha256)
    elif template in {"T03", "T04"}:
        if write:
            fetch("POST", "/api/tasks", {"title": marker})
        rows = fetch("GET", "/api/tasks")
        result.update(marker=marker, data_verified=any(x.get("title") == marker for x in rows))
    else:
        if write:
            fetch("POST", "/api/note", {"text": marker})
        result.update(marker=marker, data_verified=fetch("GET", "/api/note").get("text") == marker)
    result["elapsed_ms"] = round((perf_counter() - started) * 1000, 2)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--template", required=True, choices=["T03", "T04", "T05", "T06"])
    parser.add_argument("--marker")
    parser.add_argument("--write-marker", action="store_true", help="Write demo data; T06 replaces the test note")
    parser.add_argument("--allow-http", action="store_true")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    try:
        result = probe(args.url, args.template, marker=args.marker, write=args.write_marker, allow_http=args.allow_http, expected_sha256=args.expected_sha256)
    except Exception as exc:
        print(json.dumps({"result": "FAILED", "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["data_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
