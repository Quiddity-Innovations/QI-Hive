# -*- coding: utf-8 -*-
"""
QI MCP Gateway — reusable, CONFIG-DRIVEN MCP front door for any QI app.

Turns an existing QI application's HTTP API into MCP tools (Streamable HTTP)
so Claude — on claude.ai web/mobile, Desktop or Claude Code — can use the app.
Nothing is hardcoded per deployment: everything (on/off, port, bind, auth mode,
which tools are exposed) comes from a JSON config file.

Two ways to consume this module:

  1. STANDALONE GATEWAY (Phase 2 — per-app MCP service):
         python qi_mcp_gateway.py C:\\<App>\\config\\mcp_gateway.json
     (or via a tiny launcher .py for NSSM). Serves /mcp + /health on its own
     port with its own auth tokens.

  2. EMBEDDED REGISTRATION (Phase 1 — tools inside an existing MCP server,
     e.g. the QI Connector):
         from qi_mcp_gateway import ADAPTERS
         ADAPTERS["mapsnap"](mcp, cfg_section)

Config file schema (all keys optional unless marked *):
{
  "enabled": true,                         // master switch
  "name": "MapSnap MCP",                   // MCP server display name
  "project_id": "mapsnap",                // * QI registry id
  "adapter": "mapsnap",                   // adapter to register (see ADAPTERS)
  "target_base": "http://127.0.0.1:9876", // * the app's own API
  "bind": "127.0.0.1",                    // 0.0.0.0 for LAN (e.g. BU server)
  "port": 8651,                            // * gateway port (project's block!)
  "auth": {
    "mode": "both",                       // bearer | capability | both | none
    "secrets_dir": "C:\\<App>\\config\\secrets"   // token files auto-generate here
  },
  "tools": { "<tool>": true/false, ... }, // per-tool exposure flags
  "generic_tools": [                       // declarative tools, no code needed
    {"name": "app_status", "enabled": true, "method": "GET",
     "path": "/api/status", "description": "..." }
  ]
}

Auth model (same as QI Connector):
  /mcp                    -> Authorization: Bearer <mcp_bearer_token.txt>
  /c/<mcp_path_token>/mcp -> capability URL (for clients that can't send headers)
  /health /version /info  -> open;  /.well-known/* -> open 404 (prevents bogus
                             OAuth Dynamic Client Registration by claude.ai)
"""
import json
import logging
import secrets as pysecrets
import sys
from pathlib import Path

import httpx

log = logging.getLogger("qi_mcp_gateway")


def _clip(obj, limit: int = 20000) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=1, default=str)
    return s if len(s) <= limit else s[:limit] + "\n…[truncated]"


def _err(msg: str) -> str:
    return json.dumps({"ok": False, "error": msg})


# ------------------------------------------------------------------ auth ----
def load_or_create_token(secrets_dir: Path, fname: str) -> str:
    secrets_dir.mkdir(parents=True, exist_ok=True)
    f = secrets_dir / fname
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    tok = pysecrets.token_urlsafe(32)
    f.write_text(tok, encoding="utf-8")
    return tok




# ------------------------------------------------------- audit + rate limit ----
class McpAudit:
    """Per-call audit log + global sliding-window rate limit for /mcp traffic.
    Buffers the ASGI receive stream once to extract the JSON-RPC method and
    tool name, logs one line per call, and rejects with 429 when the window
    exceeds the cap. Config: rate_limit_per_min (0 disables the limit)."""

    def __init__(self, logger, rate_per_min: int = 240):
        import collections
        self.log = logger
        self.rate = int(rate_per_min or 0)
        self.hits = collections.deque()

    def allow(self) -> bool:
        if self.rate <= 0:
            return True
        import time
        now = time.monotonic()
        while self.hits and now - self.hits[0] > 60.0:
            self.hits.popleft()
        if len(self.hits) >= self.rate:
            return False
        self.hits.append(now)
        return True

    async def buffered_receive(self, receive):
        """Drain the request body, return (body_bytes, replay_receive)."""
        chunks = []
        while True:
            msg = await receive()
            if msg["type"] != "http.request":
                break
            chunks.append(msg.get("body", b""))
            if not msg.get("more_body"):
                break
        body = b"".join(chunks)
        sent = {"done": False}

        async def replay():
            if not sent["done"]:
                sent["done"] = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}
        return body, replay

    def describe(self, body: bytes) -> str:
        try:
            d = json.loads(body.decode("utf-8", "replace") or "{}")
            method = d.get("method", "?")
            if method == "tools/call":
                params = d.get("params") or {}
                args = params.get("arguments") or {}
                keys = ",".join(list(args.keys())[:6])
                return f"tools/call {params.get('name', '?')}({keys})"
            return method
        except Exception:
            return f"(unparsed {len(body)}B)"


async def _send_429(send):
    body = b'{"error":"rate limit exceeded - slow down"}'
    await send({"type": "http.response.start", "status": 429,
                "headers": [(b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                            (b"retry-after", b"30")]})
    await send({"type": "http.response.body", "body": body})


class AuthGate:
    """ASGI wrapper: bearer on /mcp, optional capability path, open contract
    endpoints, and open-404 /.well-known (see module docstring)."""

    OPEN_PATHS = {"/health", "/version", "/info", "/"}

    def __init__(self, inner, mode: str, bearer_token: str, path_token: str,
                 rate_per_min: int = 240):
        self.inner = inner
        self.mode = mode
        self.bearer = bearer_token
        self.ptok = path_token
        self.audit = McpAudit(log, rate_per_min)

    async def _audited(self, scope, receive, send, via):
        if scope.get("method") == "POST" and scope.get("path", "").startswith("/mcp"):
            if not self.audit.allow():
                log.warning("AUDIT 429 rate-limited (%s)", via)
                return await _send_429(send)
            body, replay = await self.audit.buffered_receive(receive)
            log.info("AUDIT %s %s", via, self.audit.describe(body))
            return await self.inner(scope, replay, send)
        return await self.inner(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.inner(scope, receive, send)
        path = scope.get("path", "")
        if self.mode == "none":
            return await self._audited(scope, receive, send, via="open")
        if self.mode in ("capability", "both") and self.ptok:
            cap = f"/c/{self.ptok}"
            if path.startswith(cap + "/") or path == cap:
                scope = dict(scope)
                scope["path"] = path[len(cap):] or "/"
                scope["raw_path"] = scope["path"].encode()
                return await self._audited(scope, receive, send, via="capability")
        if path in self.OPEN_PATHS or path.startswith("/.well-known"):
            return await self.inner(scope, receive, send)
        if self.mode in ("bearer", "both"):
            auth = ""
            for k, v in scope.get("headers", []):
                if k == b"authorization":
                    auth = v.decode("latin-1")
                    break
            if auth == f"Bearer {self.bearer}":
                return await self._audited(scope, receive, send, via="bearer")
        body = b'{"error":"unauthorized"}'
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


# ------------------------------------------------------- MapSnap adapter ----
def _target_headers(cfg: dict) -> dict:
    """Outbound auth to the target app. target_bearer_file points at a file
    holding a service token the app accepts (e.g. MapSnap service_tokens.json
    entry). Optional — omit for apps with no auth."""
    f = cfg.get("target_bearer_file")
    if f and Path(f).exists():
        return {"Authorization": f"Bearer {Path(f).read_text(encoding='utf-8').strip()}"}
    return {}


def register_mapsnap_tools(mcp, cfg: dict):
    """MapSnap schema-intelligence tools. cfg keys: target_base, tools{},
    target_bearer_file (MapSnap service token)."""
    base = cfg.get("target_base", "http://127.0.0.1:9876").rstrip("/")
    flags = cfg.get("tools", {})
    hdrs = _target_headers(cfg)

    def on(name, default=True):
        return bool(flags.get(name, default))

    if on("profiles"):
        @mcp.tool()
        def mapsnap_profiles(folder: str = "") -> str:
            """List MapSnap database profiles (extracted schemas). With a folder
            name: that profile's metadata (system type, table count, extract
            date). Profiles are e.g. OnBase, Jenzabar EX, or any imported DB."""
            try:
                with httpx.Client(timeout=10.0) as c:
                    if folder:
                        r = c.get(f"{base}/api/schema-meta", params={"folder": folder}, headers=hdrs)
                    else:
                        r = c.get(f"{base}/api/folders", headers=hdrs)
                    r.raise_for_status()
                    return _clip(r.json())
            except Exception as exc:
                return _err(f"MapSnap unreachable: {exc}")

    if on("schema"):
        @mcp.tool()
        def mapsnap_schema(folder: str, table_filter: str = "", max_tables: int = 15) -> str:
            """Table structures from a MapSnap profile: columns, types, and
            foreign-key relationships. Use table_filter (substring, e.g. 'doc')
            to narrow; results are capped at max_tables. Get folder names from
            mapsnap_profiles first."""
            try:
                with httpx.Client(timeout=30.0) as c:
                    r = c.get(f"{base}/api/schema", params={"folder": folder}, headers=hdrs)
                    r.raise_for_status()
                    schema = r.json()
            except Exception as exc:
                return _err(f"MapSnap unreachable or unknown folder '{folder}': {exc}")
            # MapSnap schema.json: {"metadata": {...}, "objects": [{name,
            # object_type, module, columns, foreign_keys_out/in}, ...]}
            tables = schema.get("objects") or schema.get("tables")
            if isinstance(tables, dict):
                tables = [dict(v, name=k) if isinstance(v, dict) else {"name": k, "def": v}
                          for k, v in tables.items()]
            if not isinstance(tables, list):
                return _clip(schema)  # unknown shape — return raw, clipped
            flt = table_filter.lower()
            out = []
            for t in tables:
                name = str(t.get("name") or t.get("table") or "")
                if flt and flt not in name.lower():
                    continue
                out.append({
                    "name": name,
                    "module": t.get("module") or t.get("super_module"),
                    "columns": t.get("columns") or t.get("cols"),
                    "foreign_keys_out": t.get("foreign_keys_out") or t.get("foreign_keys") or t.get("fks"),
                    "foreign_keys_in": t.get("foreign_keys_in"),
                })
                if len(out) >= max(1, min(max_tables, 50)):
                    break
            return _clip({"folder": folder, "matched": len(out),
                          "total_tables": len(tables),
                          "system": (schema.get("metadata") or {}).get("source"),
                          "tables": out})

    if on("ask"):
        @mcp.tool()
        def mapsnap_ask(question: str, folder: str = "", model: str = "") -> str:
            """Ask MapSnap's own local AI about a database profile (schema Q&A,
            NL->SQL, relationships). Streams internally; returns the full answer.
            Uses MapSnap's configured local model unless 'model' is given. Data
            never leaves the MapSnap machine — only this answer text returns."""
            use_model = model
            answer, cached, used = [], False, ""
            for attempt in range(2):
                payload = {"question": question}
                if folder:
                    payload["folder"] = folder
                if use_model:
                    payload["model"] = use_model
                answer, cached, conflict_loaded = [], False, ""
                try:
                    with httpx.Client(timeout=httpx.Timeout(240.0, connect=10.0)) as c:
                        with c.stream("POST", f"{base}/api/chat", json=payload, headers=hdrs) as r:
                            r.raise_for_status()
                            event = ""
                            for line in r.iter_lines():
                                if line.startswith("event:"):
                                    event = line.split(":", 1)[1].strip()
                                elif line.startswith("data:"):
                                    try:
                                        d = json.loads(line.split(":", 1)[1].strip())
                                    except Exception:
                                        continue
                                    if event == "token":
                                        answer.append(d.get("text", ""))
                                    elif event == "cached":
                                        cached = True
                                    elif event == "conflict":
                                        # GPU arbiter: requested model would evict a
                                        # resident one. Don't thrash VRAM — answer
                                        # with the model that's already loaded.
                                        conflict_loaded = d.get("loaded", "")
                                        break
                                    elif event == "error":
                                        return _err(f"MapSnap chat error: {d}")
                                    elif event == "done":
                                        break
                except Exception as exc:
                    return _err(f"MapSnap chat failed: {exc}")
                if conflict_loaded and attempt == 0:
                    use_model, used = conflict_loaded, conflict_loaded
                    continue
                break
            return _clip({"ok": True, "cached": cached,
                          **({"model": used} if used else {}),
                          "answer": "".join(answer).strip()})

    if on("table_data", default=False):  # OFF unless explicitly enabled — row data!
        @mcp.tool()
        def mapsnap_table_data(folder: str, table: str, limit: int = 50) -> str:
            """Sample rows from a table in a MapSnap profile (live read-only
            query via the saved connection). WARNING: returns real row data —
            exposed only where the deployment's egress policy allows it."""
            try:
                with httpx.Client(timeout=60.0) as c:
                    r = c.post(f"{base}/api/table-data", headers=hdrs,
                               json={"folder": folder, "table": table,
                                     "limit": max(1, min(limit, 200))})
                    r.raise_for_status()
                    return _clip(r.json())
            except Exception as exc:
                return _err(f"MapSnap table-data failed: {exc}")


# ---------------------------------------------------- generic HTTP tools ----
def register_generic_tools(mcp, cfg: dict):
    """Declarative tools from config — no code required. Each entry proxies one
    JSON endpoint. params: a dict passed as query (GET) or JSON body (POST)."""
    base = cfg.get("target_base", "").rstrip("/")
    hdrs = _target_headers(cfg)
    for spec in cfg.get("generic_tools", []):
        if not spec.get("enabled", True):
            continue
        name = spec["name"]
        method = spec.get("method", "GET").upper()
        path = spec["path"]
        desc = spec.get("description", f"{method} {path} on {base}")

        def _make(method=method, path=path):
            def _tool(params: dict | None = None) -> str:
                try:
                    with httpx.Client(timeout=30.0) as c:
                        if method == "GET":
                            r = c.get(f"{base}{path}", params=params or {}, headers=hdrs)
                        else:
                            r = c.request(method, f"{base}{path}", json=params or {}, headers=hdrs)
                        r.raise_for_status()
                        try:
                            return _clip(r.json())
                        except Exception:
                            return _clip(r.text)
                except Exception as exc:
                    return _err(f"{method} {path} failed: {exc}")
            return _tool

        fn = _make()
        fn.__name__ = name
        fn.__doc__ = desc
        mcp.tool()(fn)


ADAPTERS = {
    "mapsnap": register_mapsnap_tools,
    # future: "nexus": register_nexus_tools, "autopdf": ..., "gamez": ...
}


# ------------------------------------------------------------- standalone ---
def build_application(cfg: dict):
    """Build the full ASGI app (FastMCP + contract endpoints + AuthGate)."""
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from mcp.server.fastmcp import FastMCP
    try:
        from mcp.server.transport_security import TransportSecuritySettings
        tsec = {"transport_security":
                TransportSecuritySettings(enable_dns_rebinding_protection=False)}
    except Exception:
        tsec = {}

    mcp = FastMCP(cfg.get("name", f"QI {cfg['project_id']} MCP"),
                  stateless_http=True, json_response=True, **tsec)

    adapter = cfg.get("adapter")
    if adapter:
        if adapter not in ADAPTERS:
            raise SystemExit(f"unknown adapter '{adapter}' — known: {list(ADAPTERS)}")
        ADAPTERS[adapter](mcp, cfg)
    register_generic_tools(mcp, cfg)

    @asynccontextmanager
    async def lifespan(_app):
        async with mcp.session_manager.run():
            log.info("qi_mcp_gateway '%s' up on %s:%s",
                     cfg.get("name"), cfg.get("bind"), cfg.get("port"))
            yield

    app = FastAPI(title=cfg.get("name", "QI MCP Gateway"), lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/version")
    def version():
        return {"project": cfg["project_id"], "version": "1.0.0",
                "status": "active", "component": "mcp_gateway"}

    @app.get("/info")
    def info():
        safe = {k: v for k, v in cfg.items() if k != "auth"}
        return {"status": "ok", "data": safe, "error": None,
                "project": cfg["project_id"], "version": "1.0.0"}

    app.mount("/", mcp.streamable_http_app())

    auth = cfg.get("auth", {})
    mode = auth.get("mode", "bearer")
    bearer = path_tok = ""
    if mode != "none":
        sdir = Path(auth.get("secrets_dir") or (Path.cwd() / "secrets"))
        bearer = load_or_create_token(sdir, "mcp_bearer_token.txt")
        path_tok = load_or_create_token(sdir, "mcp_path_token.txt")
    return AuthGate(app, mode, bearer, path_tok,
                    rate_per_min=int(cfg.get('rate_limit_per_min', 240)))


def main(config_path: str):
    import uvicorn
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not cfg.get("enabled", False):
        print(f"[qi_mcp_gateway] disabled in {config_path} — exiting.")
        return
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(build_application(cfg),
                host=cfg.get("bind", "127.0.0.1"), port=int(cfg["port"]),
                log_level="info")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        raise SystemExit("usage: python qi_mcp_gateway.py <config.json>")
    main(sys.argv[1])
