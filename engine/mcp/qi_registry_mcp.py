# AI-GENERATED BEGIN (Claude Code, 2026-08-06)
"""QI Registry MCP — Pattern-1 stdio server (stdlib only, zero dependencies).

Exposes the QI ecosystem registry + service health to any local MCP client
(Claude Desktop, Claude Code) over newline-delimited JSON-RPC 2.0 on
stdin/stdout. Every tool is a pure read, and the backing files are read
directly from disk on each call — so the tools keep answering even when the
Brain API, Dashboard, and tunnels are all down. That resilience is the whole
point of this server; never make it call another QI service's HTTP API.

Data sources (read-only):
  C:\\QIH\\ecosystem\\qi_registry.json        — projects, ports, port strategy
  C:\\QIH\\ecosystem\\QI_Service_Registry.md  — NSSM service table (best-effort parse)

Health checks are a bare TCP connect + close. No HTTP request, no payload.

Registration (Claude Desktop / claude_desktop_config.json):
  {"command": "<python.exe>", "args": ["C:\\QIH\\engine\\mcp\\qi_registry_mcp.py"]}
"""
import json
import re
import socket
import sys
from pathlib import Path

# Windows detail 1: MCP mandates UTF-8; Windows consoles default to cp1252, so a
# single non-ASCII byte (an em-dash in a project name — this registry has many)
# would raise mid-write and kill the server.
# stderr is in this list too (added 2026-08-09 with the _log() diagnostics
# below): it defaults to cp1252 on Windows, so a single em-dash in a log line
# is written as byte 0x97 and every UTF-8 reader of the log — including
# Claude Desktop's capture — fails to decode it.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", newline="\n")
    except (AttributeError, ValueError):
        pass

# Windows detail 2: Desktop does not launch this script from its own folder, so
# never rely on cwd — resolve every path absolutely.
ECOSYSTEM = Path(r"C:\QIH\ecosystem")
REGISTRY_JSON = ECOSYSTEM / "qi_registry.json"
SERVICE_REGISTRY_MD = ECOSYSTEM / "QI_Service_Registry.md"

SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL = "2024-11-05"
SERVER_INFO = {"name": "qi-registry", "version": "1.0.0"}


# ---------------------------------------------------------------- data access
def _load_registry() -> dict:
    return json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))


def _projects() -> list:
    return _load_registry().get("projects", [])


def _project_summary(p: dict) -> dict:
    ports = {
        role: spec.get("current")
        for role, spec in (p.get("ports") or {}).items()
        if isinstance(spec, dict)
    }
    return {
        "id": p.get("id"),
        "name": p.get("name"),
        "status": p.get("status"),
        "path": p.get("path"),
        "ports": ports,
        "family_tier": p.get("family_tier"),
        "description": (p.get("description") or "")[:200],
    }


def _port_listening(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _tcp_port(spec: dict):
    """Return the numeric port from a registry port spec, or None.

    The registry also records non-TCP transports (e.g. current: "stdio") —
    those must never reach sort() or socket() as strings.
    """
    cur = spec.get("current")
    return cur if isinstance(cur, int) else None


# --------------------------------------------------------------------- tools
def tool_qi_projects(args: dict) -> dict:
    query = (args.get("filter") or "").lower()
    status = (args.get("status") or "").lower()
    out = []
    for p in _projects():
        if status and status not in (p.get("status") or "").lower():
            continue
        if query:
            hay = " ".join(
                str(p.get(k) or "") for k in ("id", "name", "description", "path")
            ).lower()
            if query not in hay:
                continue
        out.append(_project_summary(p))
    return {"count": len(out), "projects": out}


def tool_qi_project(args: dict) -> dict:
    pid = (args.get("id") or "").lower().strip()
    for p in _projects():
        if (p.get("id") or "").lower() == pid:
            return p
    known = [p.get("id") for p in _projects()]
    return {"error": f"no project with id '{pid}'", "known_ids": known}


def tool_qi_ports(args: dict) -> dict:
    reg = _load_registry()
    rows = []
    for p in reg.get("projects", []):
        for role, spec in (p.get("ports") or {}).items():
            if isinstance(spec, dict) and _tcp_port(spec) is not None:
                rows.append(
                    {
                        "project": p.get("id"),
                        "role": role,
                        "port": _tcp_port(spec),
                        "block": spec.get("block"),
                        "notes": spec.get("notes"),
                    }
                )
    rows.sort(key=lambda r: r["port"])
    return {"ports": rows, "port_strategy": reg.get("port_strategy", {})}


def tool_qi_health(args: dict) -> dict:
    pid = (args.get("id") or "").lower().strip()
    results = []
    for p in _projects():
        if pid and (p.get("id") or "").lower() != pid:
            continue
        for role, spec in (p.get("ports") or {}).items():
            if isinstance(spec, dict) and _tcp_port(spec) is not None:
                port = _tcp_port(spec)
                results.append(
                    {
                        "project": p.get("id"),
                        "role": role,
                        "port": port,
                        "listening": _port_listening(port),
                    }
                )
    up = sum(1 for r in results if r["listening"])
    return {"checked": len(results), "listening": up, "results": results}


def tool_qi_services(args: dict) -> dict:
    """Best-effort parse of the QI_Service_Registry.md markdown tables.

    Collects any table row whose first cell starts with QI_. Falls back to an
    empty list (never an exception) if the file moves or the format changes.
    """
    rows = []
    try:
        text = SERVICE_REGISTRY_MD.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            m = re.search(r"QI_[A-Za-z0-9_]+", line)
            if m:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                rows.append({"service": m.group(0), "details": cells})
    except OSError as exc:
        return {"error": f"service registry unreadable: {exc}", "services": []}
    # de-dupe (the doc mentions some services in several tables)
    seen, unique = set(), []
    for r in rows:
        if r["service"] not in seen:
            seen.add(r["service"])
            unique.append(r)
    return {"count": len(unique), "services": unique, "source": str(SERVICE_REGISTRY_MD)}


TOOLS = {
    "qi_projects": (
        tool_qi_projects,
        "List QI ecosystem projects from the registry (works even when all QI "
        "services are down). Optional substring 'filter' over id/name/description/"
        "path and 'status' substring filter.",
        {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "description": "substring match"},
                "status": {"type": "string", "description": "status substring"},
            },
        },
    ),
    "qi_project": (
        tool_qi_project,
        "Fetch one QI project's full registry record by id (e.g. 'mapsnap').",
        {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    ),
    "qi_ports": (
        tool_qi_ports,
        "Flattened port table for the whole QI ecosystem plus the port-block "
        "allocation strategy. Use before assigning any new port.",
        {"type": "object", "properties": {}},
    ),
    "qi_health": (
        tool_qi_health,
        "TCP-connect health check of registered ports (no HTTP, no payload). "
        "Optionally limit to one project id.",
        {"type": "object", "properties": {"id": {"type": "string"}}},
    ),
    "qi_services": (
        tool_qi_services,
        "List QI_* Windows services parsed from QI_Service_Registry.md "
        "(name + table row details).",
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
    """
    Diagnostics go to stderr, which Claude Desktop captures into
    %APPDATA%\\Claude\\logs\\mcp-server-qi-registry.log.

    Added 2026-08-09 after a silent disconnect: the server had run cleanly for
    five hours, then stdin closed and the process exited with no output at all,
    leaving Desktop's generic "Server disconnected" toast as the only evidence.
    Desktop's own log even prompts for this ("add output to stderr ... and it
    will appear in this log").

    Never write diagnostics to stdout — that channel carries JSON-RPC frames and
    any stray text corrupts the protocol.
    """
    try:
        print(f"[qi-registry] {text}", file=sys.stderr, flush=True)
    except Exception:
        pass


def main():
    # Log lines stay ASCII-only: belt and braces alongside the stderr
    # reconfigure above, so diagnostics survive even if reconfigure() failed.
    _log(f"started: python={sys.executable} registry={REGISTRY_JSON}")
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
                # handle() already guards tool bodies; this catches protocol-level
                # bugs so one bad frame can't take the whole server down.
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
        # A clean exit here means stdin reached EOF: the client closed the pipe.
        # Normal on shutdown, and also what a dropped transport looks like.
        # Claude Desktop does NOT relaunch a stdio server — fully quit and
        # reopen Desktop to respawn it.
        _log(f"stdin closed after {handled} message(s) - exiting")


if __name__ == "__main__":
    main()
# AI-GENERATED END
