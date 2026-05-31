"""
Background HTTP file server for fast streaming downloads.
Avoids the Streamlit base64/WebSocket bottleneck for large files.
"""
import os
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

_TOKEN = secrets.token_urlsafe(32)
_ROOT = ""
_PORT = 8502
_started = False
_lock = threading.Lock()


def _safe_realpath(path: str) -> str | None:
    """Return realpath if it's under _ROOT, else None."""
    real = os.path.realpath(path)
    root = os.path.realpath(_ROOT)
    if real == root or real.startswith(root + os.sep):
        return real
    return None


_MIME = {
    ".zip": "application/zip",
    ".pdf": "application/pdf",
    ".md":  "text/markdown",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".txt": "text/plain",
    ".bed": "text/plain",
    ".vcf": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".html": "text/html",
    ".bam": "application/octet-stream",
    ".bai": "application/octet-stream",
    ".gz":  "application/gzip",
    ".fastq": "text/plain",
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/ping":
            self._send(200, b"ok")
            return
        if parsed.path != "/dl":
            self._send(404, b"Not Found")
            return

        qs = urllib.parse.parse_qs(parsed.query)
        if qs.get("t", [""])[0] != _TOKEN:
            self._send(403, b"Forbidden")
            return

        path = urllib.parse.unquote(qs.get("p", [""])[0])
        safe = _safe_realpath(path)
        if not safe or not os.path.isfile(safe):
            self._send(404, b"Not Found")
            return

        size = os.path.getsize(safe)
        ext  = os.path.splitext(safe)[1].lower()
        mime = _MIME.get(ext, "application/octet-stream")
        name = os.path.basename(safe)

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(safe, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break

    def _send(self, code: int, body: bytes):
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def start_file_server(root: str, port: int = 8502) -> bool:
    """Start background streaming file server. Safe to call multiple times."""
    global _ROOT, _PORT, _started
    with _lock:
        if _started:
            return True
        _ROOT = root
        for p in range(port, port + 10):
            try:
                srv = ThreadingHTTPServer(("0.0.0.0", p), _Handler)
                t = threading.Thread(target=srv.serve_forever, daemon=True)
                t.start()
                _PORT = p
                _started = True
                return True
            except OSError:
                continue
        return False


def get_token() -> str:
    return _TOKEN


def get_port() -> int:
    return _PORT


def is_running() -> bool:
    return _started


def make_download_html(file_path: str, label: str = "⬇") -> str:
    """Return a self-contained HTML snippet with a streaming download link."""
    encoded = urllib.parse.quote(file_path)
    port = _PORT
    token = _TOKEN
    return f"""<!DOCTYPE html><html><head><style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:transparent;font-family:"Source Sans Pro","Noto Sans",sans-serif;}}
a{{display:inline-flex;align-items:center;justify-content:center;
   width:100%;height:38px;
   background:transparent;color:inherit;
   border:1px solid rgba(49,51,63,0.2);border-radius:0.5rem;
   text-decoration:none;font-size:14px;font-weight:400;
   cursor:pointer;transition:border-color .15s,background .15s;
   padding:0 12px;}}
a:hover{{border-color:rgba(49,51,63,0.5);color:inherit;}}
a:active{{background:rgba(49,51,63,0.05);}}
@media(prefers-color-scheme:dark){{
  a{{border-color:rgba(250,250,250,0.2);}}
  a:hover{{border-color:rgba(250,250,250,0.6);}}
  a:active{{background:rgba(250,250,250,0.05);}}
}}
</style></head><body>
<a id="a" target="_blank">{label}</a>
<script>
(function(){{
  try{{var h=window.top.location.hostname||'localhost';
       var pr=window.top.location.protocol||'http:';}}
  catch(e){{var h='localhost';var pr='http:';}}
  document.getElementById('a').href=pr+'//'+h+':{port}/dl?t={token}&p={encoded}';
}})();
</script>
</body></html>"""
