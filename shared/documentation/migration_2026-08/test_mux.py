"""End-to-end check of PlayDeck's new mux path.

1. picker unit checks on synthetic yt-dlp format lists
2. real ffmpeg mux of a video-only + audio-only pair, served through /api/mux,
   then probed to confirm the output really carries both streams
"""
import os, sys, json, subprocess, tempfile

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\PlayDeck")

from api import main as M
from api import library as L

FF = L.tool("ffmpeg")
FP = L.tool("ffprobe")
TMP = tempfile.mkdtemp(prefix="playdeck_mux_")
fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


# ── 1. picker ────────────────────────────────────────────────────
print("\n[1] format picking")

INFO = {"formats": [
    {"format_id": "18",  "url": "http://x/18",  "ext": "mp4",  "height": 360,
     "vcodec": "avc1.42001E", "acodec": "mp4a.40.2", "protocol": "https"},
    {"format_id": "137", "url": "http://x/137", "ext": "mp4",  "height": 1080,
     "vcodec": "avc1.640028", "acodec": "none", "protocol": "https", "tbr": 4000},
    {"format_id": "248", "url": "http://x/248", "ext": "webm", "height": 1080,
     "vcodec": "vp9", "acodec": "none", "protocol": "https", "tbr": 2500},
    {"format_id": "140", "url": "http://x/140", "ext": "m4a",  "height": None,
     "vcodec": "none", "acodec": "mp4a.40.2", "protocol": "https", "abr": 128},
    {"format_id": "251", "url": "http://x/251", "ext": "webm", "height": None,
     "vcodec": "none", "acodec": "opus", "protocol": "https", "abr": 160},
]}

muxed = M._pick_muxed(INFO)
check("muxed pick is the 360p progressive", muxed["format_id"] == "18", muxed["format_id"])
pair = M._pick_pair(INFO)
check("pair found", bool(pair))
check("pair video is 1080p", pair[0]["height"] == 1080, str(pair[0]["height"]))
check("pair audio is audio-only", pair[1]["vcodec"] == "none", pair[1]["format_id"])

# the old bug: a 2000-point mp4 bonus outranked 200px of height
HEIGHT_VS_EXT = {"formats": [
    {"url": "http://x/a", "ext": "mp4",  "height": 720,  "vcodec": "avc1", "acodec": "mp4a"},
    {"url": "http://x/b", "ext": "webm", "height": 1080, "vcodec": "vp9",  "acodec": "opus"},
]}
check("height beats container bonus",
      M._pick_muxed(HEIGHT_VS_EXT)["height"] == 1080,
      str(M._pick_muxed(HEIGHT_VS_EXT)["height"]))

# fragmented DASH has no single URL — must not be offered as a pair
FRAG = {"formats": [
    {"url": "http://x/v", "ext": "mp4", "height": 1080, "vcodec": "avc1", "acodec": "none",
     "protocol": "http_dash_segments", "fragments": [{"url": "http://x/v/1"}]},
    {"url": "http://x/a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a",
     "protocol": "http_dash_segments", "fragments": [{"url": "http://x/a/1"}]},
]}
check("fragmented DASH rejected as a pair", M._pick_pair(FRAG) is None)

# hevc video-only would copy into fMP4 but browsers often can't decode it
HEVC = {"formats": [
    {"url": "http://x/v", "ext": "mp4", "height": 2160, "vcodec": "hev1.2", "acodec": "none"},
    {"url": "http://x/a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a"},
]}
check("hevc video-only rejected", M._pick_pair(HEVC) is None)

# a site with only progressive formats must stay on the cheap path
PROG = {"formats": [
    {"url": "http://x/a", "ext": "mp4", "height": 720,  "vcodec": "avc1", "acodec": "mp4a"},
    {"url": "http://x/b", "ext": "mp4", "height": 1080, "vcodec": "avc1", "acodec": "mp4a"},
]}
check("no pair when everything is muxed", M._pick_pair(PROG) is None)
check("best progressive wins", M._pick_muxed(PROG)["height"] == 1080)

# ── 2. real ffmpeg mux through the endpoint ──────────────────────
print("\n[2] ffmpeg mux through /api/mux")

vpath = os.path.join(TMP, "v.mp4")
apath = os.path.join(TMP, "a.m4a")
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi",
                "-i", "testsrc=size=640x360:rate=25:duration=10",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "25", "-an", vpath],
               check=True)
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=10",
                "-c:a", "aac", "-vn", apath], check=True)
check("test inputs built", os.path.isfile(vpath) and os.path.isfile(apath))

from fastapi.testclient import TestClient
client = TestClient(M.app)

sid = M._cache_mux({"url": vpath, "vcodec": "avc1"},
                   {"url": apath, "acodec": "mp4a"},
                   {"User-Agent": "test"})

out = os.path.join(TMP, "muxed.mp4")
with client.stream("GET", f"/api/mux/{sid}") as r:
    check("mux responds 200", r.status_code == 200, str(r.status_code))
    check("no byte ranges advertised", r.headers.get("accept-ranges") == "none",
          r.headers.get("accept-ranges", "-"))
    check("served as mp4", r.headers.get("content-type", "").startswith("video/mp4"),
          r.headers.get("content-type", "-"))
    with open(out, "wb") as fh:
        for chunk in r.iter_bytes():
            fh.write(chunk)

size = os.path.getsize(out)
check("mux produced bytes", size > 20_000, f"{size} bytes")

probe = subprocess.run([FP, "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,height", "-of", "json", out],
                       capture_output=True, text=True)
streams = json.loads(probe.stdout or "{}").get("streams", [])
kinds = sorted(s["codec_type"] for s in streams)
check("output has video+audio", kinds == ["audio", "video"], str(kinds))
check("video was stream-copied (h264)",
      any(s["codec_type"] == "video" and s["codec_name"] == "h264" for s in streams))
check("audio present as aac",
      any(s["codec_type"] == "audio" and s["codec_name"] == "aac" for s in streams))

# seek-by-restart: ?t= must yield a shorter remainder
out2 = os.path.join(TMP, "muxed_t6.mp4")
with client.stream("GET", f"/api/mux/{sid}?t=6") as r:
    with open(out2, "wb") as fh:
        for chunk in r.iter_bytes():
            fh.write(chunk)
dur = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", out2], capture_output=True, text=True)
try:
    d = float((dur.stdout or "0").strip())
except ValueError:
    d = -1
check("seek to t=6 returns ~4s of a 10s clip", 3.0 < d < 5.5, f"{d:.2f}s")

# non-aac audio must be transcoded rather than copied
opus = os.path.join(TMP, "a.opus")
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=5", "-c:a", "libopus", "-vn", opus],
               check=True)
sid2 = M._cache_mux({"url": vpath, "vcodec": "avc1"},
                    {"url": opus, "acodec": "opus"}, {})
out3 = os.path.join(TMP, "muxed_opus.mp4")
with client.stream("GET", f"/api/mux/{sid2}") as r:
    with open(out3, "wb") as fh:
        for chunk in r.iter_bytes():
            fh.write(chunk)
p3 = subprocess.run([FP, "-v", "error", "-show_entries", "stream=codec_type,codec_name",
                     "-of", "json", out3], capture_output=True, text=True)
s3 = json.loads(p3.stdout or "{}").get("streams", [])
check("opus source transcoded to aac",
      any(x["codec_type"] == "audio" and x["codec_name"] == "aac" for x in s3),
      str([x.get("codec_name") for x in s3]))

# a single-stream id must not answer on the mux route
sid3 = M._cache_stream("http://example.com/x.mp4", {}, False)
check("progressive id rejected by /api/mux",
      client.get(f"/api/mux/{sid3}").status_code == 404)
check("no ffmpeg processes left running",
      all(p.poll() is not None for p in M._MUX_PROCS.values()),
      f"{len(M._MUX_PROCS)} tracked")

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
