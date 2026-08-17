"""Mux over real HTTP: exercises ffmpeg's http input path — custom headers,
User-Agent, reconnect flags, and remote seeking by Range — which is what the
live CDN case uses. Files are served by a throwaway local HTTP server.
"""
import os, sys, json, time, threading, subprocess, tempfile, functools, http.server, socketserver

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\PlayDeck")
from api import main as M
from api import library as L

FF, FP = L.tool("ffmpeg"), L.tool("ffprobe")
TMP = tempfile.mkdtemp(prefix="playdeck_http_")
fails = []
seen_headers = {}
SLOW = [False]


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


# 30s so a seek to 20s still leaves a decent tail
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi",
                "-i", "testsrc=size=1280x720:rate=25:duration=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "50", "-an",
                os.path.join(TMP, "v.mp4")], check=True)
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=30", "-c:a", "aac", "-vn",
                os.path.join(TMP, "a.m4a")], check=True)


class Handler(http.server.SimpleHTTPRequestHandler):
    """Range-capable, because seeking a remote file depends on it — and every
    real media CDN answers Range. SimpleHTTPRequestHandler alone does not."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        seen_headers.setdefault(self.path, []).append(dict(self.headers))
        return super().do_GET()

    def copyfile(self, src, dst):
        if not SLOW[0]:
            return super().copyfile(src, dst)
        # Trickle the bytes so the mux is still running when we inspect it.
        while True:
            buf = src.read(32768)
            if not buf:
                return
            dst.write(buf)
            time.sleep(0.15)

    def send_head(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404)
            return None
        size = os.path.getsize(path)
        rng = self.headers.get("Range")
        fh = open(path, "rb")
        if not rng:
            self.send_response(200)
            self.send_header("Content-Length", str(size))
        else:
            start, _, end = rng.replace("bytes=", "").partition("-")
            start, end = int(start or 0), (int(end) if end else size - 1)
            fh.seek(start)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", "video/mp4")
        self.end_headers()
        return fh


socketserver.ThreadingTCPServer.allow_reuse_address = True
socketserver.ThreadingTCPServer.daemon_threads = True
# Threading matters: two muxes overlap in section 4, and ffmpeg opens the video
# and audio tracks as two concurrent connections.
srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0),
                                      functools.partial(Handler, directory=TMP))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"
print(f"serving test media on {base}\n")

from fastapi.testclient import TestClient
client = TestClient(M.app)

headers = {"User-Agent": "PlayDeck/test-agent", "Referer": "https://example.com/watch",
           "Cookie": "session=abc123"}
sid = M._cache_mux({"url": f"{base}/v.mp4", "vcodec": "avc1"},
                   {"url": f"{base}/a.m4a", "acodec": "mp4a"}, headers)

print("[1] mux from http, no seek")
out = os.path.join(TMP, "out.mp4")
got = 0
with client.stream("GET", f"/api/mux/{sid}") as r:
    check("status 200", r.status_code == 200, str(r.status_code))
    with open(out, "wb") as fh:
        for chunk in r.iter_bytes():
            fh.write(chunk); got += len(chunk)
check("bytes streamed", got > 100_000, f"{got} bytes")

probe = json.loads(subprocess.run(
    [FP, "-v", "error", "-show_entries", "stream=codec_type,codec_name,height",
     "-of", "json", out], capture_output=True, text=True).stdout or "{}")
streams = probe.get("streams", [])
check("video+audio present", sorted(s["codec_type"] for s in streams) == ["audio", "video"],
      str([s.get("codec_name") for s in streams]))
check("720p preserved", any(s.get("height") == 720 for s in streams))

print("\n[2] our headers reached the origin")
vh = seen_headers.get("/v.mp4", [{}])[0]
check("User-Agent forwarded", vh.get("User-Agent") == "PlayDeck/test-agent",
      vh.get("User-Agent", "-"))
check("Referer forwarded", vh.get("Referer") == "https://example.com/watch",
      vh.get("Referer", "-"))
check("Cookie forwarded", vh.get("Cookie") == "session=abc123", vh.get("Cookie", "-"))

print("\n[3] seek by restart (?t=20 over http Range)")
out2 = os.path.join(TMP, "out20.mp4")
with client.stream("GET", f"/api/mux/{sid}?t=20") as r:
    with open(out2, "wb") as fh:
        for chunk in r.iter_bytes():
            fh.write(chunk)
def played_seconds(path):
    """fMP4 from a pipe has no duration in its header — measure the last PTS."""
    out = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "packet=pts_time", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    pts = [float(x) for x in out.split() if x and x[0].isdigit()]
    return max(pts) if pts else 0.0


check("seeked output has bytes", os.path.getsize(out2) > 50_000,
      f"{os.path.getsize(out2)} bytes")
d = played_seconds(out2)
check("remainder is ~10s of a 30s clip", 8.0 < d < 12.0, f"{d:.2f}s")
ranged = any("Range" in h for h in seen_headers.get("/v.mp4", []))
check("origin saw a Range request for the seek", ranged)

print("\n[4] a new request supersedes the previous ffmpeg")
# Stand in a process that never ends on its own — a scrub leaves exactly this
# behind — then make the request that should supersede it.
sentinel = subprocess.Popen([FF, "-hide_banner", "-loglevel", "quiet", "-f", "lavfi",
                             "-i", "testsrc=size=64x64:rate=5", "-f", "null", "-"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
M._MUX_PROCS[sid] = sentinel
check("sentinel running before the new request", sentinel.poll() is None)

with client.stream("GET", f"/api/mux/{sid}?t=5") as r3:
    for _ in r3.iter_bytes():
        break
deadline = time.time() + 5
while sentinel.poll() is None and time.time() < deadline:
    time.sleep(0.1)
check("superseded ffmpeg was killed", sentinel.poll() is not None, str(sentinel.poll()))

time.sleep(1.0)
alive = [p for p in M._MUX_PROCS.values() if p.poll() is None]
for p in alive:
    p.kill()
check("no ffmpeg left behind", not alive, f"{len(alive)} alive")

srv.shutdown()
print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
