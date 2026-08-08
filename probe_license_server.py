# -*- coding: utf-8 -*-
"""Tiny local runner for the OnBase licensing probes.

Serves probe_license.html and streams probe output back to the browser.
A browser cannot execute Python on its own, so the HTML page needs this
backend to sit behind it.

Bound to 127.0.0.1 only. Port 8653 is inside the MapSnap family block
(8650-8659) per C:\\QIH\\ecosystem\\qi_registry.json; 8650/8651/8652 were
already taken by cognibase and the MapSnap MCP services.

    python C:\\QIH\\probe_license_server.py

Then open http://127.0.0.1:8653
"""
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE = Path(__file__).resolve().parent
PORT = 8653

# Whitelist. The browser sends a key, never a path or a command, so no input
# from the page can ever become something this process executes.
SCRIPTS = {
    "1": ("probe_license.py", "SQL Probe 1 - row counts, table dumps, indexes, types"),
    "2": ("probe_license2.py", "SQL Probe 2 - systemtableex, live state, registeredusers"),
    "3": ("probe_license_api.py", "API probe - OnBase 13 guest Unity service, or BU preflight"),
}

# Environment keys the API probe may be pointed at. onbase13 is the local VM
# (live, no gate). The BU keys remain wired for the preflight/lock display but
# probe_license_api.py refuses to contact them regardless of what is sent here.
API_ENVS = {"onbase13", "test", "dev", "ut3", "prod"}

# host[,port] - letters, digits, dots, hyphens. Rejects anything that could
# carry a separator into the ODBC connection string.
HOST_RE = re.compile(r"^[A-Za-z0-9.\-]{1,64}(,\d{1,5})?$")

DEFAULT_HOST = "192.168.251.128,1433"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("  [%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route in ("/", "/index.html", "/probe_license.html"):
            page = HERE / "probe_license.html"
            if not page.exists():
                return self._send(500, "probe_license.html not found next to this script.")
            return self._send(200, page.read_bytes(), "text/html; charset=utf-8")

        if route == "/scripts":
            rows = ["%s|%s|%s" % (k, v[0], v[1]) for k, v in sorted(SCRIPTS.items())]
            return self._send(200, "\n".join(rows))

        if route == "/run":
            return self._run(parse_qs(parsed.query))

        return self._send(404, "not found")

    def _run(self, qs):
        key = (qs.get("script") or [""])[0]
        if key not in SCRIPTS:
            return self._send(400, "unknown script key")

        host = (qs.get("host") or [DEFAULT_HOST])[0].strip() or DEFAULT_HOST
        if not HOST_RE.match(host):
            return self._send(400, "invalid host - expected ip-or-name[,port]")

        name, _label = SCRIPTS[key]
        target = HERE / name
        if not target.exists():
            return self._send(500, "%s is missing from %s" % (name, HERE))

        env = dict(os.environ)
        env["ONBASE_HOST"] = host
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        if key == "3":
            envkey = (qs.get("env") or ["test"])[0].strip().lower()
            if envkey not in API_ENVS:
                return self._send(400, "unknown environment key")
            env["ONBASE_ENV"] = envkey
            # Never set from here. Opting in to an outbound OnBase session is a
            # deliberate act at a shell, not something a web button can do.
            env.pop("ONBASE_API_PROBE_ENABLE", None)

        # Chunked so output appears in the browser while the probe is still
        # running - probe 1 issues a lot of round-trips and is not instant.
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        def chunk(text):
            data = text.encode("utf-8", "replace")
            self.wfile.write(b"%X\r\n" % len(data) + data + b"\r\n")
            self.wfile.flush()

        try:
            proc = subprocess.Popen(
                [sys.executable, str(target)],
                cwd=str(HERE), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in iter(proc.stdout.readline, b""):
                chunk(line.decode("utf-8", "replace"))
            proc.stdout.close()
            rc = proc.wait()
            chunk("\n[exit code %d]\n" % rc)
        except Exception as exc:
            try:
                chunk("\n[runner error] %s\n" % exc)
            except Exception:
                pass
        finally:
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except Exception:
                pass


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = "http://127.0.0.1:%d" % PORT
    print("OnBase licensing probe runner")
    print("  serving  %s" % HERE)
    print("  listening %s   (Ctrl+C to stop)" % url)
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
        srv.shutdown()


if __name__ == "__main__":
    main()
