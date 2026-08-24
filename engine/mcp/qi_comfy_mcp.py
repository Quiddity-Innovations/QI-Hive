# AI-GENERATED BEGIN (Claude Code, 2026-08-08)
"""QI Comfy MCP — Pattern-1 stdio server (stdlib only, zero dependencies).

Drives a local ComfyUI instance over its HTTP API so ComfyUI can be operated
by conversation: list what models are installed, run a pre-assembled workflow
with a few parameters swapped, and collect the output files.

Deliberately talks to ComfyUI's *API* and never imports or patches ComfyUI
itself. ComfyUI updates (and the portable build replacing itself wholesale)
therefore cannot break this server.

Data sources:
  http://127.0.0.1:8188      — ComfyUI HTTP API (override with COMFY_URL)
  D:\\AI\\workflows           — saved API-format workflows (override COMFY_WORKFLOWS)

Workflows must be exported from the ComfyUI UI with "Save (API Format)" —
the editor's normal save format describes the canvas, not an executable graph,
and cannot be queued.

Registration (Claude Code / claude_desktop_config.json):
  {"command": "<python.exe>", "args": ["C:\\QIH\\engine\\mcp\\qi_comfy_mcp.py"]}
"""
import itertools
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

# Windows detail 1: MCP mandates UTF-8; Windows consoles default to cp1252, so a
# single non-ASCII byte (a model filename with an accent, a prompt with an
# em-dash) would raise mid-write and kill the server.
for _stream in (sys.stdin, sys.stdout):
    try:
        _stream.reconfigure(encoding="utf-8", newline="\n")
    except (AttributeError, ValueError):
        pass

# Windows detail 2: the client does not launch this script from its own folder,
# so never rely on cwd — resolve every path absolutely.
# 8740, not ComfyUI's default 8188: the QI install runs on a non-default port
# so it can never collide with another ComfyUI someone starts by hand.
COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8740").rstrip("/")
WORKFLOW_DIR = Path(os.environ.get("COMFY_WORKFLOWS", r"D:\AI\workflows"))
COMFY_ROOT = Path(os.environ.get("COMFY_ROOT",
                                 r"D:\AI\ComfyUI_windows_portable\ComfyUI"))

SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_PROTOCOL = "2024-11-05"
SERVER_INFO = {"name": "qi-comfy", "version": "1.0.0"}

CLIENT_ID = uuid.uuid4().hex        # ComfyUI groups a session's jobs by this
DEFAULT_WAIT = 300.0                # generation is slow; 5 min is a sane ceiling


# ------------------------------------------------------------- http plumbing
def _get(path: str, timeout: float = 30.0):
    url = f"{COMFY_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        body = r.read()
    ctype = "application/json"
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"_raw_bytes": len(body), "_content_type": ctype}


def _post(path: str, payload: dict, timeout: float = 30.0):
    req = urllib.request.Request(
        f"{COMFY_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _post_multipart(path: str, fields: dict, file_field: str,
                    filename: str, data: bytes, timeout: float = 300.0):
    """POST multipart/form-data. Hand-rolled because ComfyUI's upload endpoint
    is the one place its API is not JSON, and pulling in `requests` for a single
    call would end this server's zero-dependency guarantee."""
    boundary = "----QIComfy" + uuid.uuid4().hex
    safe = filename.replace("\\", "_").replace('"', "'").replace("\r", "").replace("\n", "")
    body = bytearray()
    for key, val in fields.items():
        body += f"--{boundary}\r\n".encode("utf-8")
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
        body += f"{val}\r\n".encode("utf-8")
    body += f"--{boundary}\r\n".encode("utf-8")
    body += (f'Content-Disposition: form-data; name="{file_field}"; '
             f'filename="{safe}"\r\n').encode("utf-8")
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += data
    body += f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{COMFY_URL}{path}",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _vram(stats: dict) -> list:
    """[{name, free_gb, total_gb}] out of a /system_stats payload."""
    out = []
    for d in (stats or {}).get("devices", []) or []:
        out.append({"name": d.get("name"),
                    "free_gb": round((d.get("vram_free") or 0) / 1e9, 1),
                    "total_gb": round((d.get("vram_total") or 0) / 1e9, 1)})
    return out


def _busy() -> dict:
    """Queue depth, or {} if it cannot be read. Never raises."""
    try:
        q = _get("/queue", timeout=8.0)
        return {"running": len(q.get("queue_running") or []),
                "pending": len(q.get("queue_pending") or [])}
    except Exception:
        return {}


def _reachable() -> tuple:
    """(ok, detail) — every tool leads with this so the failure is legible."""
    try:
        stats = _get("/system_stats", timeout=8.0)
        return True, stats
    except urllib.error.URLError as exc:
        return False, (f"ComfyUI is not answering on {COMFY_URL} ({exc.reason}). "
                       f"Start it, or set COMFY_URL if it runs on another port.")
    except Exception as exc:
        return False, f"ComfyUI check failed: {exc}"


# --------------------------------------------------------------- workflow io
def _workflow_path(name: str) -> Path:
    """Resolve a workflow name to a file, refusing anything outside the dir."""
    stem = (name or "").strip()
    if not stem:
        raise ValueError("workflow name is empty")
    if not stem.lower().endswith(".json"):
        stem += ".json"
    full = (WORKFLOW_DIR / stem).resolve()
    if not str(full).startswith(str(WORKFLOW_DIR.resolve())):
        raise ValueError("workflow name escapes the workflow directory")
    if not full.is_file():
        raise ValueError(f"no such workflow: {full.name}")
    return full


def _aliases(path: Path) -> dict:
    """Optional <workflow>.params.json mapping friendly name -> [node, input]."""
    side = path.with_suffix("").with_suffix(".params.json")
    if not side.is_file():
        side = path.parent / (path.stem + ".params.json")
    if side.is_file():
        try:
            return json.loads(side.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _targets(graph: dict) -> dict:
    """Every settable input, as 'node.input' and 'Title.input' where titled."""
    out = {}
    for nid, node in graph.items():
        if not isinstance(node, dict):
            continue
        title = ((node.get("_meta") or {}).get("title") or "").strip()
        for key, val in (node.get("inputs") or {}).items():
            if isinstance(val, list):
                continue          # a wired link, not a literal — not settable
            out[f"{nid}.{key}"] = val
            if title:
                out.setdefault(f"{title}.{key}", val)
    return out


def _apply(graph: dict, params: dict, alias: dict) -> list:
    """Patch literal inputs. Returns a log of what actually changed."""
    changed = []
    for key, value in (params or {}).items():
        node_id = input_name = None

        if key in alias:                                  # friendly alias
            node_id, input_name = alias[key][0], alias[key][1]
        elif "." in key:
            left, input_name = key.rsplit(".", 1)
            if left in graph:                             # direct node id
                node_id = left
            else:                                         # match on node title
                for nid, node in graph.items():
                    meta = (node.get("_meta") or {}) if isinstance(node, dict) else {}
                    if (meta.get("title") or "").strip() == left:
                        node_id = nid
                        break

        if node_id is None or input_name is None:
            raise ValueError(
                f"cannot place parameter '{key}'. Use 'node_id.input', "
                f"'Node Title.input', or an alias from the workflow's "
                f".params.json. Call comfy_workflows for what this one accepts."
            )
        node = graph.get(node_id)
        if not isinstance(node, dict) or input_name not in (node.get("inputs") or {}):
            raise ValueError(f"node {node_id} has no input '{input_name}'")
        if isinstance(node["inputs"][input_name], list):
            raise ValueError(
                f"{node_id}.{input_name} is wired to another node; "
                f"it cannot be set to a literal"
            )
        changed.append({"node": node_id, "input": input_name,
                        "from": node["inputs"][input_name], "to": value})
        node["inputs"][input_name] = value
    return changed


def _outputs(history_entry: dict) -> list:
    """Flatten a history record into downloadable file references."""
    files = []
    for node_id, out in (history_entry.get("outputs") or {}).items():
        for kind in ("images", "gifs", "videos", "audio", "files"):
            for item in (out.get(kind) or []):
                if not isinstance(item, dict) or "filename" not in item:
                    continue
                q = urllib.parse.urlencode({
                    "filename": item.get("filename", ""),
                    "subfolder": item.get("subfolder", ""),
                    "type": item.get("type", "output"),
                })
                files.append({
                    "node": node_id,
                    "kind": kind,
                    "filename": item.get("filename"),
                    "subfolder": item.get("subfolder", ""),
                    "url": f"{COMFY_URL}/view?{q}",
                })
    return files


# ------------------------------------------------------------------- tools
def tool_comfy_status(args: dict) -> dict:
    ok, detail = _reachable()
    if not ok:
        return {"reachable": False, "url": COMFY_URL, "error": detail}
    sysinfo = (detail or {}).get("system", {})
    devices = []
    for d in (detail or {}).get("devices", []):
        devices.append({
            "name": d.get("name"),
            "vram_total_gb": round((d.get("vram_total") or 0) / 1e9, 1),
            "vram_free_gb": round((d.get("vram_free") or 0) / 1e9, 1),
        })
    queue = {}
    try:
        q = _get("/queue", timeout=8.0)
        queue = {"running": len(q.get("queue_running") or []),
                 "pending": len(q.get("queue_pending") or [])}
    except Exception as exc:
        queue = {"error": str(exc)}
    return {
        "reachable": True,
        "url": COMFY_URL,
        "comfyui_version": sysinfo.get("comfyui_version"),
        "python": sysinfo.get("python_version", "").split()[0],
        "pytorch": sysinfo.get("pytorch_version"),
        "ram_free_gb": round((sysinfo.get("ram_free") or 0) / 1e9, 1),
        "devices": devices,
        "queue": queue,
        "workflow_dir": str(WORKFLOW_DIR),
        "workflow_dir_exists": WORKFLOW_DIR.is_dir(),
    }


def tool_comfy_models(args: dict) -> dict:
    """What is actually installed, read from the live node schemas.

    ComfyUI advertises installed files as the options of each loader's combo
    input, so this reflects the real folders — including anything dropped in
    while ComfyUI was running (it rescans on request).
    """
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    try:
        info = _get("/object_info", timeout=60.0)
    except Exception as exc:
        return {"error": f"could not read node info: {exc}"}

    wanted = {
        "checkpoints": ("CheckpointLoaderSimple", "ckpt_name"),
        "upscale_models": ("UpscaleModelLoader", "model_name"),
        "loras": ("LoraLoader", "lora_name"),
        "vae": ("VAELoader", "vae_name"),
        "controlnet": ("ControlNetLoader", "control_net_name"),
        "diffusion_models": ("UNETLoader", "unet_name"),
        "clip_vision": ("CLIPVisionLoader", "clip_name"),
        "frame_interpolation": ("FrameInterpolationModelLoader", "model_name"),
    }
    found, missing = {}, []
    for label, (node, field) in wanted.items():
        try:
            spec = info[node]["input"]["required"][field]
        except (KeyError, IndexError, TypeError):
            found[label] = {"available": None, "note": f"{node} not installed"}
            continue
        # Two shapes in the wild: the classic [[...names...], {...}] and the V3
        # schema's ["COMBO", {"options": [...names...]}]. Reading [0] blindly
        # yields the literal string "COMBO" and silently reports nothing.
        opts = []
        try:
            head = spec[0]
            if isinstance(head, list):
                opts = head
            elif isinstance(spec[1], dict):
                opts = spec[1].get("options") or []
        except (IndexError, TypeError):
            opts = []
        opts = [o for o in opts if isinstance(o, str)]
        found[label] = {"count": len(opts), "available": opts[:60]}
        if not opts:
            missing.append(label)
    filt = (args or {}).get("filter")
    if filt:
        low = str(filt).lower()
        found = {k: v for k, v in found.items() if low in k.lower()}
    return {"models": found, "empty_categories": missing, "node_count": len(info)}


def tool_comfy_node_info(args: dict) -> dict:
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    name = (args or {}).get("node")
    try:
        info = _get("/object_info", timeout=60.0)
    except Exception as exc:
        return {"error": f"could not read node info: {exc}"}
    if not name:
        return {"error": "give a node name", "hint": sorted(info)[:40]}
    if name not in info:
        low = name.lower()
        near = [k for k in info if low in k.lower()][:25]
        return {"error": f"no node named {name}", "similar": near}
    node = info[name]
    return {"node": name, "category": node.get("category"),
            "input": node.get("input"), "output": node.get("output"),
            "output_name": node.get("output_name")}


def tool_comfy_workflows(args: dict) -> dict:
    if not WORKFLOW_DIR.is_dir():
        return {"error": f"no workflow directory at {WORKFLOW_DIR}",
                "hint": "create it, or set COMFY_WORKFLOWS", "workflows": []}
    items = []
    for path in sorted(WORKFLOW_DIR.glob("*.json")):
        if path.name.endswith(".params.json"):
            continue
        entry = {"name": path.stem, "file": str(path)}
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            entry["error"] = f"unreadable: {exc}"
            items.append(entry)
            continue
        if not isinstance(graph, dict) or "nodes" in graph:
            entry["error"] = ("this looks like an editor save, not an API "
                              "export — re-save it with Save (API Format)")
            items.append(entry)
            continue
        alias = _aliases(path)
        entry["nodes"] = len(graph)
        entry["aliases"] = alias or None
        if (args or {}).get("detail"):
            entry["settable"] = _targets(graph)
        else:
            entry["settable_count"] = len(_targets(graph))
        items.append(entry)
    return {"dir": str(WORKFLOW_DIR), "count": len(items), "workflows": items}


def _combo_options(spec) -> list:
    """Pull the choices out of an input schema, in either shape ComfyUI uses."""
    try:
        head = spec[0]
    except (IndexError, TypeError):
        return []
    if isinstance(head, list):
        return [o for o in head if isinstance(o, str)]
    if head == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict):
        return [o for o in (spec[1].get("options") or []) if isinstance(o, str)]
    return []


def _node_source_map() -> dict:
    """Best-effort node -> repo map from ComfyUI-Manager's cached catalogue.

    Only a convenience: when it isn't there, missing nodes are still reported,
    just without a suggested source.
    """
    try:
        cands = list((COMFY_ROOT / "user").rglob("*extension-node-map.json"))
    except OSError:
        return {}
    for path in cands:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        out = {}
        for repo, payload in raw.items():
            names = payload[0] if isinstance(payload, list) and payload else []
            for n in names if isinstance(names, list) else []:
                out.setdefault(n, repo)
        if out:
            return out
    return {}


def tool_comfy_workflow_check(args: dict) -> dict:
    """Tell me what a workflow needs that this install hasn't got.

    Answers the "I downloaded a workflow, make it work" question: which node
    types are missing (and which repo supplies them), and which model files it
    references that aren't on disk.
    """
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    args = args or {}
    name = args.get("workflow", "")
    try:
        path = _workflow_path(name)
        graph = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}
    if not isinstance(graph, dict) or "nodes" in graph:
        return {"error": "that file is an editor save, not an API export. "
                         "Re-save it from ComfyUI with Save (API Format) — the "
                         "editor format cannot be queued.",
                "workflow": path.stem}
    try:
        info = _get("/object_info", timeout=60.0)
    except Exception as exc:
        return {"error": f"could not read node info: {exc}"}

    sources = _node_source_map()
    missing_nodes, missing_models, bad_values = [], [], []
    missing_inputs = []
    used = set()

    for nid, node in graph.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type")
        if not ct:
            continue
        used.add(ct)
        if ct not in info:
            entry = {"node_id": nid, "class_type": ct}
            if ct in sources:
                entry["provided_by"] = sources[ct]
            missing_nodes.append(entry)
            continue
        required = (info[ct].get("input") or {}).get("required") or {}
        schema = {}
        schema.update(required)
        schema.update((info[ct].get("input") or {}).get("optional") or {})

        # A node can reference only installed things and still be rejected, if
        # the graph simply omits a required field — workflows exported from an
        # older ComfyUI lose fields that were added since. ComfyUI does not
        # fill these in, so the omission has to be caught here.
        supplied = set((node.get("inputs") or {}).keys())
        for field, spec in required.items():
            if field in supplied:
                continue
            dflt = None
            if isinstance(spec, list) and len(spec) > 1 and isinstance(spec[1], dict):
                dflt = spec[1].get("default")
            missing_inputs.append({"node_id": nid, "class_type": ct,
                                   "input": field, "suggested_default": dflt})

        for field, value in (node.get("inputs") or {}).items():
            if isinstance(value, list) or not isinstance(value, str):
                continue          # wired link, or not a selectable name
            opts = _combo_options(schema.get(field))
            if not opts:
                # No choices at all: either a free-text field (fine) or a model
                # folder that is completely empty (not fine). Only the latter
                # has a combo declared for it.
                spec = schema.get(field)
                declared_combo = isinstance(spec, list) and (
                    spec and (spec[0] == "COMBO" or isinstance(spec[0], list)))
                if declared_combo and value:
                    missing_models.append({"node_id": nid, "class_type": ct,
                                           "input": field, "wants": value,
                                           "note": "no files installed for this input"})
                continue
            if value not in opts:
                rec = {"node_id": nid, "class_type": ct, "input": field,
                       "wants": value, "installed": opts[:8]}
                # A short list of non-filename choices is an enum, not a model.
                looks_like_file = any("." in o for o in opts[:8])
                (missing_models if looks_like_file else bad_values).append(rec)

    ready = not (missing_nodes or missing_models or bad_values or missing_inputs)
    out = {
        "workflow": path.stem,
        "ready_to_run": ready,
        "nodes_used": len(used),
        "missing_nodes": missing_nodes,
        "missing_models": missing_models,
        "missing_required_inputs": missing_inputs,
        "invalid_values": bad_values,
    }
    if ready:
        out["summary"] = "everything this workflow needs is installed"
    else:
        bits = []
        if missing_nodes:
            bits.append(f"{len(missing_nodes)} node type(s) not installed")
        if missing_models:
            bits.append(f"{len(missing_models)} model file(s) missing")
        if missing_inputs:
            bits.append(f"{len(missing_inputs)} required input(s) absent from the graph")
        if bad_values:
            bits.append(f"{len(bad_values)} input value(s) not valid here")
        out["summary"] = "; ".join(bits)
        if not sources and missing_nodes:
            out["note"] = ("ComfyUI-Manager's catalogue was not found, so no "
                           "source repo could be suggested for missing nodes")
    return out


def tool_comfy_run(args: dict) -> dict:
    """Queue a workflow, optionally waiting for it, and report the outputs."""
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    args = args or {}
    try:
        path = _workflow_path(args.get("workflow", ""))
        graph = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(graph, dict) or "nodes" in graph:
            return {"error": "that file is an editor save, not an API export. "
                             "Re-save it from ComfyUI with Save (API Format)."}
        changed = _apply(graph, args.get("params") or {}, _aliases(path))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}

    try:
        queued = _post("/prompt", {"prompt": graph, "client_id": CLIENT_ID}, timeout=60.0)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:800]
        return {"error": f"ComfyUI rejected the graph ({exc.code})", "detail": body,
                "hint": "a required model may be missing — try comfy_models"}
    except Exception as exc:
        return {"error": f"queue failed: {exc}"}

    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        return {"error": "ComfyUI returned no prompt_id", "response": queued}
    result = {"prompt_id": prompt_id, "workflow": path.stem, "applied": changed}

    if not args.get("wait", True):
        result["status"] = "queued"
        return result

    timeout = float(args.get("timeout") or DEFAULT_WAIT)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            hist = _get(f"/history/{prompt_id}", timeout=15.0)
        except Exception:
            hist = {}
        entry = (hist or {}).get(prompt_id)
        if entry:
            status = (entry.get("status") or {})
            files = _outputs(entry)
            result["status"] = status.get("status_str") or "done"
            result["outputs"] = files
            result["output_count"] = len(files)
            if not files:
                result["note"] = ("finished with no saved files — the workflow "
                                  "may lack a Save/Combine node")
            return result
        time.sleep(1.5)

    result["status"] = "still running"
    result["note"] = (f"no result within {timeout:.0f}s. It may still finish — "
                      f"call comfy_result with this prompt_id.")
    return result


def tool_comfy_result(args: dict) -> dict:
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    prompt_id = (args or {}).get("prompt_id")
    if not prompt_id:
        return {"error": "give a prompt_id"}
    try:
        hist = _get(f"/history/{prompt_id}", timeout=20.0)
    except Exception as exc:
        return {"error": f"history lookup failed: {exc}"}
    entry = (hist or {}).get(prompt_id)
    if not entry:
        return {"prompt_id": prompt_id, "status": "not finished (or unknown id)"}
    files = _outputs(entry)
    return {"prompt_id": prompt_id,
            "status": (entry.get("status") or {}).get("status_str", "done"),
            "output_count": len(files), "outputs": files}


def tool_comfy_cancel(args: dict) -> dict:
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    done = []
    try:
        _post("/interrupt", {}, timeout=10.0)
        done.append("interrupted the running job")
    except Exception as exc:
        done.append(f"interrupt failed: {exc}")
    if (args or {}).get("clear_queue"):
        try:
            _post("/queue", {"clear": True}, timeout=10.0)
            done.append("cleared the pending queue")
        except Exception as exc:
            done.append(f"queue clear failed: {exc}")
    return {"actions": done}


# Upload / free / vary were added 2026-08-23 after evaluating Comfy-Org's own
# comfy-mcp (beta, ~40 tools, shells out to comfy-cli). That server was not
# adopted — it cannot address this portable install, and its lifecycle tools
# (restart/update/install_node) are unsafe on a card with four tenants. These
# three are the capabilities it had that this one genuinely lacked.

MAX_UPLOAD_BYTES = 256 * 1024 * 1024


def tool_comfy_upload(args: dict) -> dict:
    """Stage a local file into ComfyUI's input folder so a graph can read it.

    This is what makes image-to-video and reference images reachable from a
    conversation: LoadImage can only see files ComfyUI already holds, and the
    name this returns is the value to set on that node.
    """
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    args = args or {}
    raw = (args.get("path") or "").strip().strip('"')
    if not raw:
        return {"error": "give a 'path' to a local file"}
    src = Path(raw).expanduser()
    if not src.is_file():
        return {"error": f"no such file: {src}"}
    size = src.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        return {"error": f"{src.name} is {size / 1e6:.0f} MB; the cap is "
                         f"{MAX_UPLOAD_BYTES / 1e6:.0f} MB. Copy large files "
                         f"straight into ComfyUI's input folder instead."}

    name = (args.get("name") or src.name).strip()
    name = Path(name).name                      # never let a path escape via name
    subfolder = (args.get("subfolder") or "").strip().strip("/\\")
    if ".." in subfolder:
        return {"error": "subfolder may not contain '..'"}
    dest_type = (args.get("type") or "input").strip().lower()
    if dest_type not in ("input", "temp"):
        return {"error": "type must be 'input' or 'temp' - "
                         "'output' is where renders land, not where they are read"}

    fields = {"type": dest_type,
              "overwrite": "true" if args.get("overwrite") else "false"}
    if subfolder:
        fields["subfolder"] = subfolder

    try:
        resp = _post_multipart("/upload/image", fields, "image", name,
                               src.read_bytes())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:600]
        return {"error": f"ComfyUI rejected the upload ({exc.code})", "detail": body}
    except Exception as exc:
        return {"error": f"upload failed: {exc}"}

    # ComfyUI renames rather than clobbers unless overwrite was set, so the name
    # it returns is the only one worth quoting back.
    stored = resp.get("name") or name
    got_sub = resp.get("subfolder") or ""
    ref = f"{got_sub}/{stored}" if got_sub else stored
    out = {"uploaded": str(src),
           "bytes": size,
           "name": stored,
           "subfolder": got_sub,
           "type": resp.get("type", dest_type),
           "reference": ref,
           "use_as": f"params {{'<LoadImage node>.image': '{ref}'}}"}
    if stored != name:
        out["note"] = (f"stored as {stored!r}, not {name!r} - a file of that name "
                       f"already existed. Pass overwrite=true to replace it.")
    if src.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        out["hint"] = ("not an image extension - LoadImage will not list it. "
                       "Video and audio loaders (VHS_LoadVideo, LoadAudio) read "
                       "the same folder and will.")
    return out


def tool_comfy_free(args: dict) -> dict:
    """Ask ComfyUI to unload idle models and release VRAM.

    Cannot stop a running job - the card is not freed until that job ends. The
    queue is reported alongside so the number means something.
    """
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    args = args or {}
    before = _vram(detail)
    queue = _busy()

    payload = {"unload_models": args.get("unload_models", True) is not False,
               "free_memory": args.get("free_memory", True) is not False}
    try:
        _post("/free", payload, timeout=30.0)
    except Exception as exc:
        return {"error": f"/free failed: {exc}", "vram": before}

    time.sleep(1.5)                       # unload is not instant
    try:
        after = _vram(_get("/system_stats", timeout=10.0))
    except Exception:
        after = []

    freed = None
    if before and after and len(before) == len(after):
        freed = round(sum(a["free_gb"] for a in after)
                      - sum(b["free_gb"] for b in before), 1)

    out = {"requested": payload, "vram_before": before, "vram_after": after,
           "freed_gb": freed, "queue": queue}
    if queue.get("running"):
        out["warning"] = ("a job is still running - /free cannot interrupt it, "
                          "so its VRAM stays held until it finishes. "
                          "Use comfy_cancel to stop it.")
    elif freed is not None and freed <= 0:
        out["note"] = ("nothing was released - either no models were loaded, or "
                       "another process on this card holds the memory. Free VRAM "
                       "is a poor health signal here; check utilisation too.")
    return out


MAX_VARIANTS = 12


def tool_comfy_vary(args: dict) -> dict:
    """Fan one workflow into a batch of variants over parameter value lists.

    Every combination of the 'vary' arrays is queued as its own run. Defaults to
    not waiting: a dozen video renders is an overnight job, not a tool call.
    """
    ok, detail = _reachable()
    if not ok:
        return {"error": detail}
    args = args or {}
    vary = args.get("vary") or {}
    if not isinstance(vary, dict) or not vary:
        return {"error": "give 'vary' as {param: [value, ...]}, "
                         "e.g. {'seed': [1, 2, 3]}"}
    keys = list(vary)
    lists = []
    for k in keys:
        v = vary[k]
        if not isinstance(v, list) or not v:
            return {"error": f"vary[{k!r}] must be a non-empty array"}
        lists.append(v)

    combos = list(itertools.product(*lists))
    cap = int(args.get("max_runs") or MAX_VARIANTS)
    if len(combos) > cap:
        return {"error": f"that is {len(combos)} runs ({' x '.join(str(len(l)) for l in lists)}); "
                         f"the cap is {cap}. Narrow the arrays, or raise max_runs "
                         f"deliberately.",
                "combinations": len(combos)}

    try:
        path = _workflow_path(args.get("workflow", ""))
        base = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(base, dict) or "nodes" in base:
            return {"error": "that file is an editor save, not an API export. "
                             "Re-save it from ComfyUI with Save (API Format)."}
        alias = _aliases(path)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}

    fixed = args.get("params") or {}

    # Dry-run the first combination before queueing anything. A typo'd parameter
    # that fails on run 7 of 12 leaves six half-wanted jobs on the card.
    first = dict(fixed)
    first.update(dict(zip(keys, combos[0])))
    try:
        _apply(json.loads(json.dumps(base)), first, alias)
    except ValueError as exc:
        return {"error": f"parameters rejected, nothing queued: {exc}"}

    runs = []
    for combo in combos:
        values = dict(fixed)
        values.update(dict(zip(keys, combo)))
        graph = json.loads(json.dumps(base))
        try:
            _apply(graph, values, alias)
            queued = _post("/prompt", {"prompt": graph, "client_id": CLIENT_ID},
                           timeout=60.0)
            pid = queued.get("prompt_id")
            runs.append({"variant": dict(zip(keys, combo)),
                         "prompt_id": pid} if pid else
                        {"variant": dict(zip(keys, combo)),
                         "error": "no prompt_id", "response": queued})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:400]
            runs.append({"variant": dict(zip(keys, combo)),
                         "error": f"rejected ({exc.code})", "detail": body})
        except Exception as exc:
            runs.append({"variant": dict(zip(keys, combo)), "error": str(exc)})

    result = {"workflow": path.stem, "queued": sum(1 for r in runs if r.get("prompt_id")),
              "failed": sum(1 for r in runs if r.get("error")), "runs": runs}

    if not args.get("wait"):
        result["status"] = "queued"
        result["next"] = "call comfy_result with any prompt_id to collect outputs"
        return result

    timeout = float(args.get("timeout") or DEFAULT_WAIT)
    deadline = time.time() + timeout
    pending = {r["prompt_id"]: r for r in runs if r.get("prompt_id")}
    while pending and time.time() < deadline:
        for pid in list(pending):
            try:
                entry = (_get(f"/history/{pid}", timeout=15.0) or {}).get(pid)
            except Exception:
                entry = None
            if entry:
                files = _outputs(entry)
                pending[pid]["status"] = (entry.get("status") or {}).get("status_str", "done")
                pending[pid]["outputs"] = files
                pending[pid]["output_count"] = len(files)
                del pending[pid]
        if pending:
            time.sleep(2.0)

    for r in pending.values():
        r["status"] = "still running"
    result["status"] = "done" if not pending else f"{len(pending)} still running"
    return result


TOOLS = {
    "comfy_status": (
        tool_comfy_status,
        "Is ComfyUI up? Returns version, GPU and free VRAM, queue depth, and "
        "where workflows are read from. Call this first when anything looks off.",
        {"type": "object", "properties": {}},
    ),
    "comfy_models": (
        tool_comfy_models,
        "What models are actually installed, by category (checkpoints, "
        "upscale_models, loras, vae, controlnet, diffusion_models, "
        "frame_interpolation). Also reports which categories are empty.",
        {"type": "object",
         "properties": {"filter": {"type": "string",
                                   "description": "substring over category names"}}},
    ),
    "comfy_node_info": (
        tool_comfy_node_info,
        "Inspect one node type's inputs and outputs — use when building or "
        "repairing a workflow. Omit 'node' to get a sample of node names.",
        {"type": "object", "properties": {"node": {"type": "string"}}},
    ),
    "comfy_workflows": (
        tool_comfy_workflows,
        "List saved API-format workflows, their aliases and how many inputs "
        "can be set. Pass detail=true to see every settable input and value.",
        {"type": "object", "properties": {"detail": {"type": "boolean"}}},
    ),
    "comfy_workflow_check": (
        tool_comfy_workflow_check,
        "Check whether a workflow can actually run here: reports node types "
        "that are not installed (with the repo that provides them, when known) "
        "and model files it references that are not on disk. Use this first "
        "whenever a new workflow is added.",
        {"type": "object",
         "properties": {"workflow": {"type": "string", "description": "workflow name"}},
         "required": ["workflow"]},
    ),
    "comfy_run": (
        tool_comfy_run,
        "Run a workflow with optional parameter overrides and return the output "
        "files. Params are keyed 'node_id.input', 'Node Title.input', or an "
        "alias. Set wait=false to queue without blocking.",
        {"type": "object",
         "properties": {
             "workflow": {"type": "string", "description": "workflow name"},
             "params": {"type": "object",
                        "description": "overrides, e.g. {'6.text': 'a red car'}"},
             "wait": {"type": "boolean", "description": "block for the result (default true)"},
             "timeout": {"type": "number", "description": "seconds to wait (default 300)"},
         },
         "required": ["workflow"]},
    ),
    "comfy_result": (
        tool_comfy_result,
        "Fetch the outputs of a previously queued run by prompt_id.",
        {"type": "object", "properties": {"prompt_id": {"type": "string"}},
         "required": ["prompt_id"]},
    ),
    "comfy_cancel": (
        tool_comfy_cancel,
        "Interrupt the running job. Pass clear_queue=true to also drop pending "
        "jobs.",
        {"type": "object", "properties": {"clear_queue": {"type": "boolean"}}},
    ),
    "comfy_upload": (
        tool_comfy_upload,
        "Stage a local file into ComfyUI's input folder so a workflow can read "
        "it - reference images, image-to-video sources, audio. Returns the name "
        "to set on the LoadImage/loader node. Nothing else can get a file in.",
        {"type": "object",
         "properties": {
             "path": {"type": "string", "description": "local file to upload"},
             "name": {"type": "string", "description": "store it under a different name"},
             "subfolder": {"type": "string", "description": "subfolder of input/"},
             "type": {"type": "string", "description": "'input' (default) or 'temp'"},
             "overwrite": {"type": "boolean",
                           "description": "replace an existing file of that name"},
         },
         "required": ["path"]},
    ),
    "comfy_free": (
        tool_comfy_free,
        "Release VRAM: unload idle models and free cached memory. Reports VRAM "
        "before and after plus the queue - it CANNOT interrupt a running job, "
        "so a busy card will not free. Use before handing the GPU to another app.",
        {"type": "object",
         "properties": {
             "unload_models": {"type": "boolean", "description": "default true"},
             "free_memory": {"type": "boolean", "description": "default true"},
         }},
    ),
    "comfy_vary": (
        tool_comfy_vary,
        "Queue one workflow once per combination of the given parameter values "
        "- seed sweeps, prompt A/B, cfg ladders. Capped at 12 runs. Defaults to "
        "queueing without waiting; collect each with comfy_result.",
        {"type": "object",
         "properties": {
             "workflow": {"type": "string", "description": "workflow name"},
             "vary": {"type": "object",
                      "description": "param -> array of values, e.g. {'seed': [1,2,3]}"},
             "params": {"type": "object",
                        "description": "fixed overrides applied to every variant"},
             "wait": {"type": "boolean", "description": "block for all results (default false)"},
             "timeout": {"type": "number", "description": "seconds to wait (default 300)"},
             "max_runs": {"type": "integer", "description": "raise the 12-run cap"},
         },
         "required": ["workflow", "vary"]},
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


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
# AI-GENERATED END
