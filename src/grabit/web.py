"""Local web UI: paste a link, watch the progress, get the file.

Runs entirely on 127.0.0.1 and only uses the Python standard library, so
`grab-web` works anywhere grabit itself is installed.
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from grabit.core import GrabOptions, GrabitError, download

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>grabit</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 16px/1.5 -apple-system, system-ui, sans-serif; max-width: 640px;
         margin: 8vh auto; padding: 0 16px; }
  h1 { font-size: 20px; }
  form { display: flex; gap: 8px; }
  input[type=url] { flex: 1; padding: 10px; font-size: 16px; }
  button { padding: 10px 16px; font-size: 16px; cursor: pointer; }
  label { margin-right: 16px; }
  #log { margin-top: 24px; white-space: pre-wrap; }
  progress { width: 100%; height: 8px; }
</style>
<h1>grabit</h1>
<form id="f">
  <input id="url" type="url" placeholder="Paste a link" required autofocus>
  <button>Download</button>
</form>
<p>
  <label><input type="checkbox" id="audio"> Audio only (mp3)</label>
  <label>Max height <input id="height" type="number" min="144" step="1" style="width:6em"></label>
</p>
<div id="log"></div>
<script>
const log = document.getElementById('log');
document.getElementById('f').onsubmit = async (e) => {
  e.preventDefault();
  log.textContent = 'starting...';
  const body = {
    url: document.getElementById('url').value,
    audio: document.getElementById('audio').checked,
    max_height: Number(document.getElementById('height').value) || null,
  };
  const res = await fetch('/api/download', {method: 'POST',
    headers: {'content-type': 'application/json'}, body: JSON.stringify(body)});
  const {id, error} = await res.json();
  if (error) { log.textContent = 'error: ' + error; return; }
  const timer = setInterval(async () => {
    const s = await (await fetch('/api/status/' + id)).json();
    const pct = s.percent == null ? '' : s.percent.toFixed(1) + '% ';
    log.textContent = s.status === 'done'
      ? 'saved: ' + s.files.map(f => f.path).join('\\n')
      : pct + (s.detail || '');
    if (s.status === 'done' || s.status === 'error') clearInterval(timer);
  }, 500);
};
</script>
"""

MAX_BODY = 16 * 1024
LOOPBACK = {"127.0.0.1", "localhost", "::1"}

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def _hostname(value: str) -> str:
    """Host name from a Host header or an Origin URL, without the port."""
    if "//" in value:
        return (urlparse(value).hostname or "").lower()
    if value.startswith("["):
        return value[1:].split("]", 1)[0].lower()
    return value.rsplit(":", 1)[0].lower() if value.count(":") == 1 else value.lower()


def _set(job_id: str, **fields) -> None:
    with _lock:
        _jobs[job_id].update(fields)


class Handler(BaseHTTPRequestHandler):
    output_dir: Path
    allowed_hosts: set[str] = set(LOOPBACK)

    def log_message(self, fmt: str, *args) -> None:  # keep the terminal quiet
        return

    def _trusted(self) -> bool:
        """Reject DNS rebinding (bad Host) and cross-site requests (bad Origin)."""
        if _hostname(self.headers.get("host", "")) not in self.allowed_hosts:
            return False
        origin = self.headers.get("origin")
        return origin is None or _hostname(origin) in self.allowed_hosts

    def _send(self, code: int, payload, content_type: str) -> None:
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("x-content-type-options", "nosniff")
        self.send_header("x-frame-options", "DENY")
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if not self._trusted():
            self._send(403, {"error": "forbidden"}, "application/json")
            return
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            return
        if path.startswith("/api/status/"):
            job = _jobs.get(path.removeprefix("/api/status/"))
            self._send(200 if job else 404, job or {"error": "unknown job"}, "application/json")
            return
        self._send(404, {"error": "not found"}, "application/json")

    def do_POST(self) -> None:  # noqa: N802
        if not self._trusted():
            self._send(403, {"error": "forbidden"}, "application/json")
            return
        if urlparse(self.path).path != "/api/download":
            self._send(404, {"error": "not found"}, "application/json")
            return
        # A JSON content type forces browsers to preflight cross-origin requests.
        if self.headers.get_content_type() != "application/json":
            self._send(415, {"error": "expected application/json"}, "application/json")
            return
        try:
            length = int(self.headers.get("content-length", 0))
        except ValueError:
            length = -1
        if not 0 <= length <= MAX_BODY:
            self._send(413, {"error": "request too large"}, "application/json")
            return
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(400, {"error": "invalid JSON"}, "application/json")
            return
        if not isinstance(data, dict):
            self._send(400, {"error": "expected a JSON object"}, "application/json")
            return

        job_id = uuid.uuid4().hex
        with _lock:
            _jobs[job_id] = {"status": "starting", "percent": None, "detail": "", "files": []}
        self._send(202, {"id": job_id}, "application/json")
        threading.Thread(target=_run, args=(job_id, data), daemon=True).start()


def _run(job_id: str, data: dict) -> None:
    def on_progress(progress) -> None:
        _set(
            job_id,
            status="downloading",
            percent=progress.percent,
            detail=progress.filename or "",
        )

    try:
        url = str(data.get("url", "")).strip()
        if urlparse(url).scheme not in ("http", "https"):
            raise GrabitError("only http(s) links are supported")
        max_height = data.get("max_height") or None
        if max_height is not None and not isinstance(max_height, int):
            raise GrabitError("max_height must be a whole number")
        options = GrabOptions(
            url=url,
            output_dir=Handler.output_dir,
            audio_only=bool(data.get("audio")),
            max_height=max_height,
        )
        results = download(options, on_progress=on_progress)
    except GrabitError as exc:
        _set(job_id, status="error", detail=str(exc))
        return
    _set(
        job_id,
        status="done",
        percent=100,
        files=[{"title": r.title, "path": str(r.filepath)} for r in results],
    )


def serve(host: str = "127.0.0.1", port: int = 8787, output_dir: str = "~/Downloads",
          open_browser: bool = True) -> None:
    Handler.output_dir = Path(output_dir).expanduser()
    Handler.allowed_hosts = set(LOOPBACK) | {host.lower()}
    if host not in LOOPBACK:
        print(
            f"warning: listening on {host}. The web UI has no authentication; anyone "
            "who can reach this address can make this machine download files.",
            file=sys.stderr,
        )
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"
    print(f"grabit web UI at {url}  (saving to {Handler.output_dir}, Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="grab-web", description="Local web UI for grabit.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("-o", "--output", default="~/Downloads")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    serve(args.host, args.port, args.output, open_browser=not args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
