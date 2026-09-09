# AI-GENERATED BEGIN (Claude Code, 2026-09-08)
"""QI Gemini MCP — Pattern-1 stdio server (stdlib only, zero dependencies).

Lets Claude Code call Google's free-tier Gemini API (Google AI Studio key,
NOT Vertex AI / billed) over newline-delimited JSON-RPC 2.0 on stdin/stdout.
Framing mirrors C:\\QIH\\engine\\mcp\\qi_registry_mcp.py exactly so Claude
Code loads it the same way.

Never calls another QI service. Never touches NEXUS. The API key is read
from disk on every call and is NEVER written to stdout, stderr, or the log
file — only used inline in the outbound HTTPS query string.

Data sources:
  C:\\QIH\\secrets\\trinity_gemini.env  — line GEMINI_API_KEY=...
  C:\\QIH\\config\\gemini_mcp.json        — models, long_models, daily_cap, timeout_seconds,
                                          penalty_minutes (old single model/long_model keys
                                          still accepted, treated as one-item lists)
  C:\\QIH\\data\\gemini_mcp\\usage_YYYY-MM-DD.json — daily call counter
  C:\\QIH\\data\\gemini_mcp\\penalty.json — model -> benched-until epoch seconds, survives restart
  C:\\QIH\\LOGS\\gemini_mcp.log           — one line per call, never prompt text or key

Ladder + penalty ("castigo") pattern borrowed from
C:\\APPS\\Baguapp\\vercel\\api\\analisar.js: on 429/503/timeout a model is
benched for penalty_minutes and the next model in the list is tried; a good
response clears its bench.

Registration (Claude Code / claude.json):
  {"command": "<python.exe>", "args": ["C:\\QIH\\engine\\mcp\\qi_gemini_mcp.py"]}
"""
import json
import socket
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Windows detail: MCP mandates UTF-8; Windows consoles default to cp1252, so a
# single non-ASCII byte anywhere in a response would raise mid-write and kill
# the server. Mirrors qi_registry_mcp.py.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", newline="\n")
    except (AttributeError, ValueError):
        pass

SECRETS_ENV = Path(r"C:\QIH\secrets\trinity_gemini.env")
CONFIG_JSON = Path(r"C:\QIH\config\gemini_mcp.json")
DATA_DIR = Path(r"C:\QIH\data\gemini_mcp")
LOG_FILE = Path(r"C:\QIH\LOGS\gemini_mcp.log")
PENALTY_FILE = DATA_DIR / "penalty.json"

DEFAULT_CONFIG = {
    "models": ["gemini-3.6-flash", "gemini-3.5-flash-lite"],
    "long_models": ["gemini-3.6-flash", "gemini-3.5-flash-lite"],
    "daily_cap": 200,
    "timeout_seconds": 60,
    "penalty_minutes": 10,
}

GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
MAX_LONG_CHARS = 800_000

SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL = "2024-11-05"
SERVER_INFO = {"name": "qi-gemini", "version": "1.0.0"}


# ---------------------------------------------------------------- data access
def _load_config() -> dict:
    try:
        cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        cfg = {}
    out = dict(DEFAULT_CONFIG)
    out.update(cfg)

    # backward compat: old single-model keys become one-item lists
    if "model" in cfg and "models" not in cfg:
        out["models"] = [cfg["model"]]
    if "long_model" in cfg and "long_models" not in cfg:
        out["long_models"] = [cfg["long_model"]]
    for key in ("models", "long_models"):
        if isinstance(out.get(key), str):
            out[key] = [out[key]]
        if not out.get(key):
            out[key] = list(DEFAULT_CONFIG[key])
    return out


def _load_key():
    """Returns the API key string, or None if the file/key is missing.

    Never logged, never returned in a tool payload — only used inline in the
    outbound HTTPS request URL.
    """
    try:
        text = SECRETS_ENV.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("GEMINI_API_KEY="):
            val = line.split("=", 1)[1].strip().strip('"').strip("'")
            return val or None
    return None


def _usage_path() -> Path:
    day = datetime.now().strftime("%Y-%m-%d")
    return DATA_DIR / f"usage_{day}.json"


def _read_usage() -> int:
    p = _usage_path()
    try:
        return int(json.loads(p.read_text(encoding="utf-8")).get("count", 0))
    except (OSError, json.JSONDecodeError, ValueError):
        return 0


def _bump_usage() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = _usage_path()
    count = _read_usage() + 1
    try:
        p.write_text(json.dumps({"count": count}), encoding="utf-8")
    except OSError:
        pass
    return count


# ------------------------------------------------------------------- penalty
# "castigo" — a model that just failed with 429/503/timeout is benched for
# penalty_minutes so the next call skips straight to the next rung of the
# ladder. Persisted to disk so a server restart still remembers.
_penalty_until: dict = {}
_penalty_loaded = False
_LAST_ERROR = None  # in-memory only; resets each server start


def _ensure_penalties_loaded() -> None:
    global _penalty_loaded
    if _penalty_loaded:
        return
    try:
        data = json.loads(PENALTY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _penalty_until.update({k: float(v) for k, v in data.items()})
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass
    _penalty_loaded = True


def _save_penalties() -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PENALTY_FILE.write_text(json.dumps(_penalty_until), encoding="utf-8")
    except OSError:
        pass


def _benched_minutes_left(model: str) -> int:
    _ensure_penalties_loaded()
    until = _penalty_until.get(model)
    if not until:
        return 0
    remaining = until - time.time()
    if remaining <= 0:
        del _penalty_until[model]
        _save_penalties()
        return 0
    return max(1, int(remaining // 60) + (1 if remaining % 60 else 0))


def _bench(model: str, minutes: int) -> None:
    _ensure_penalties_loaded()
    _penalty_until[model] = time.time() + minutes * 60
    _save_penalties()


def _clear_bench(model: str) -> None:
    _ensure_penalties_loaded()
    if model in _penalty_until:
        del _penalty_until[model]
        _save_penalties()


def _should_bench(status_code, err_text: str) -> bool:
    if status_code in (429, 503):
        return True
    return bool(err_text) and "timeout" in err_text.lower()


def _record_last_error(msg: str) -> None:
    global _LAST_ERROR
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _LAST_ERROR = f"{ts} {msg}"


def _log_call(tool: str, model: str, prompt_chars: int, ok: bool, latency_ms: int) -> None:
    """Append one diagnostic line. NEVER the prompt text or the key."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status = "ok" if ok else "err"
        line = f"{ts} tool={tool} model={model} prompt_chars={prompt_chars} status={status} latency_ms={latency_ms}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


# ------------------------------------------------------------------- calling
def _call_gemini(model: str, contents: list, system: str = None, tools: list = None,
                  timeout: float = 60.0):
    """Returns (ok: bool, text_or_error: str, raw: dict|None, status_code: int|None)."""
    key = _load_key()
    if not key:
        return False, "trinity_gemini.env missing", None, None

    body = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools

    url = GENERATE_URL.format(model=model, key=key)
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            err_text = exc.read().decode("utf-8", errors="replace")
        except Exception:
            err_text = str(exc)
        return False, err_text, None, exc.code
    except socket.timeout:
        return False, f"timeout after {timeout}s", None, None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            return False, f"timeout after {timeout}s", None, None
        return False, f"network error: {exc.reason}", None, None
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}", None, None

    try:
        candidates = raw.get("candidates") or []
        parts = candidates[0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            return False, f"no text in response: {json.dumps(raw)[:500]}", raw, 200
        return True, text, raw, 200
    except (IndexError, KeyError, TypeError):
        return False, f"unexpected response shape: {json.dumps(raw)[:500]}", raw, 200


def _generate(prompt: str, system: str = None, model: str = None, tool_name: str = "gemini_generate",
              extra_tools: list = None, ladder_key: str = "models") -> dict:
    """Walks the model ladder, skipping benched models, benching on
    429/503/timeout, and returning the first success. Every attempt (not just
    the winner) counts against the daily cap."""
    cfg = _load_config()
    if _load_key() is None:
        return {"error": "trinity_gemini.env missing", "attempts": []}

    ladder = list(cfg[ladder_key])
    if model:
        ladder = [model] + [m for m in ladder if m != model]

    attempts = []
    last_error = None
    prompt_chars = len(prompt or "")

    for candidate in ladder:
        left = _benched_minutes_left(candidate)
        if left > 0:
            attempts.append(f"{candidate}: benched ({left} min left)")
            continue

        count = _read_usage()
        if count >= cfg["daily_cap"]:
            return {"error": f"daily_cap reached: {count}/{cfg['daily_cap']} calls used today",
                    "attempts": attempts}

        started = time.monotonic()
        ok, text_or_err, _raw, status_code = _call_gemini(
            candidate,
            contents=[{"parts": [{"text": prompt}]}],
            system=system,
            tools=extra_tools,
            timeout=cfg["timeout_seconds"],
        )
        latency_ms = int((time.monotonic() - started) * 1000)
        _bump_usage()
        _log_call(tool_name, candidate, prompt_chars, ok, latency_ms)

        if ok:
            _clear_bench(candidate)
            return {"text": text_or_err, "model": candidate, "attempts": attempts}

        last_error = text_or_err
        if _should_bench(status_code, text_or_err):
            _bench(candidate, cfg["penalty_minutes"])
            note = f"{candidate}: {status_code or 'timeout'} (benched {cfg['penalty_minutes']} min)"
        else:
            note = f"{candidate}: {text_or_err[:200]}"
        attempts.append(note)
        _record_last_error(note)

    return {"error": last_error or "all models failed", "attempts": attempts}


# --------------------------------------------------------------------- tools
def tool_gemini_generate(args: dict) -> dict:
    prompt = args.get("prompt") or ""
    if not prompt:
        return {"error": "prompt is required"}
    return _generate(prompt, system=args.get("system"), model=args.get("model"),
                      tool_name="gemini_generate")


def tool_gemini_read_long(args: dict) -> dict:
    path = args.get("path") or ""
    question = args.get("question") or ""
    if not path or not question:
        return {"error": "path and question are required"}
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"error": f"cannot read file: {exc}"}
    if len(text) > MAX_LONG_CHARS:
        text = text[:MAX_LONG_CHARS]
    prompt = f"Document:\n\n{text}\n\nQuestion: {question}"
    return _generate(prompt, model=args.get("model"), tool_name="gemini_read_long",
                      ladder_key="long_models")


def tool_gemini_ground_search(args: dict) -> dict:
    query = args.get("query") or ""
    if not query:
        return {"error": "query is required"}
    return _generate(
        query,
        model=args.get("model"),
        tool_name="gemini_ground_search",
        extra_tools=[{"google_search": {}}],
    )


def tool_gemini_status(args: dict) -> dict:
    cfg = _load_config()
    _ensure_penalties_loaded()
    benched = {}
    for m in dict.fromkeys(cfg["models"] + cfg["long_models"]):
        left = _benched_minutes_left(m)
        if left > 0:
            benched[m] = left
    return {
        "key_present": _load_key() is not None,
        "calls_today": _read_usage(),
        "daily_cap": cfg["daily_cap"],
        "models": cfg["models"],
        "long_models": cfg["long_models"],
        "benched": benched,
        "last_error": _LAST_ERROR,
    }


TOOLS = {
    "gemini_generate": (
        tool_gemini_generate,
        "Call Gemini (free-tier Google AI Studio key) with a prompt. Walks the "
        "configured model ladder on 429/503/timeout, benching the failed model "
        "for a few minutes. Optional 'system' instruction and 'model' override "
        "(tried first, then the ladder continues).",
        {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "system": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["prompt"],
        },
    ),
    "gemini_read_long": (
        tool_gemini_read_long,
        "Read a local UTF-8 text/markdown/log file (capped at 800k chars) and "
        "ask Gemini a question over its contents. Uses the long_models ladder; "
        "optional 'model' override tried first.",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "question": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["path", "question"],
        },
    ),
    "gemini_ground_search": (
        tool_gemini_ground_search,
        "Call Gemini with Google Search grounding enabled for up-to-date, "
        "web-sourced answers. Optional 'model' override tried first.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["query"],
        },
    ),
    "gemini_status": (
        tool_gemini_status,
        "Report whether the free-tier key is present, calls made today, the "
        "daily cap, the model ladders, any benched models, and the last error. "
        "Never returns the key itself.",
        {"type": "object", "properties": {}},
    ),
}


# ------------------------------------------------------------------ protocol
def _result(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle(msg: dict):
    method = msg.get("method")
    msg_id = msg.get("id")

    if method == "initialize":
        client_proto = (msg.get("params") or {}).get("protocolVersion")
        proto = client_proto if client_proto in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
        return _result(
            msg_id,
            {
                "protocolVersion": proto,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            },
        )

    if method == "tools/list":
        tools = [
            {"name": name, "description": desc, "inputSchema": schema}
            for name, (_fn, desc, schema) in TOOLS.items()
        ]
        return _result(msg_id, {"tools": tools})

    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name not in TOOLS:
            return _error(msg_id, -32602, f"unknown tool: {name}")
        try:
            payload = TOOLS[name][0](params.get("arguments") or {})
            text = json.dumps(payload, ensure_ascii=False, indent=1)
            return _result(msg_id, {"content": [{"type": "text", "text": text}]})
        except Exception as exc:  # a tool bug must never kill the server
            return _result(
                msg_id,
                {
                    "content": [{"type": "text", "text": f"tool error: {exc}"}],
                    "isError": True,
                },
            )

    if method == "ping":
        return _result(msg_id, {})

    if msg_id is None:
        return None  # notification (e.g. notifications/initialized) — no reply

    return _error(msg_id, -32601, f"method not found: {method}")


def _log(text: str) -> None:
    """Diagnostics to stderr only. Never write diagnostics to stdout — that
    channel carries JSON-RPC frames and any stray text corrupts the protocol.
    Mirrors qi_registry_mcp.py."""
    try:
        print(f"[qi-gemini] {text}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _selftest() -> dict:
    cfg = _load_config()
    status = tool_gemini_status({})
    out = {
        "selftest": True,
        "status": status,
        "models_ladder": cfg["models"],
        "long_models_ladder": cfg["long_models"],
        "penalty_minutes": cfg["penalty_minutes"],
        "benched": status["benched"],
    }
    if status["key_present"]:
        result = _generate("Reply with just the word: ok", tool_name="selftest")
        out["generate_probe"] = result
    else:
        out["generate_probe"] = "skipped: trinity_gemini.env missing"
    return out


def main():
    if "--selftest" in sys.argv:
        print(json.dumps(_selftest(), ensure_ascii=False, indent=2))
        sys.exit(0)

    _log(f"started: python={sys.executable}")
    handled = 0
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                _log(f"skipped unparseable line ({len(line)} chars)")
                continue
            try:
                reply = handle(msg)
            except Exception as exc:
                _log(f"handle() raised on method={msg.get('method')!r}: "
                     f"{type(exc).__name__}: {exc}")
                if msg.get("id") is not None:
                    reply = _error(msg.get("id"), -32603, f"internal error: {exc}")
                else:
                    continue
            if reply is not None:
                try:
                    sys.stdout.write(json.dumps(reply, ensure_ascii=False, default=str) + "\n")
                    sys.stdout.flush()
                except Exception as exc:
                    _log(f"FATAL: cannot write to stdout ({type(exc).__name__}: {exc}) - "
                         f"client is gone, exiting")
                    return
            handled += 1
    except KeyboardInterrupt:
        _log("interrupted")
    except Exception as exc:
        _log(f"FATAL: read loop crashed: {type(exc).__name__}: {exc}")
        raise
    finally:
        _log(f"stdin closed after {handled} message(s) - exiting")


if __name__ == "__main__":
    main()
# AI-GENERATED END
