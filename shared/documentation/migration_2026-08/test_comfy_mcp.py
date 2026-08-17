"""Exercise qi_comfy_mcp: protocol handshake over stdio, then the tools."""
import json, subprocess, sys, os, tempfile

sys.stdout.reconfigure(encoding="utf-8")
SERVER = r"C:\QIH\engine\mcp\qi_comfy_mcp.py"
PY = sys.executable
fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


def rpc(messages, env=None):
    """Feed newline-delimited JSON-RPC in, collect the replies."""
    e = dict(os.environ)
    e.update(env or {})
    payload = "".join(json.dumps(m) + "\n" for m in messages)
    p = subprocess.run([PY, SERVER], input=payload, capture_output=True,
                       text=True, encoding="utf-8", timeout=180, env=e)
    out = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out, p.stderr


print("[1] protocol")
replies, err = rpc([
    {"jsonrpc": "2.0", "id": 1, "method": "initialize",
     "params": {"protocolVersion": "2025-06-18"}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 3, "method": "ping"},
])
byid = {r.get("id"): r for r in replies}
check("initialize answered", 1 in byid, str(list(byid)))
check("echoes client protocol",
      byid.get(1, {}).get("result", {}).get("protocolVersion") == "2025-06-18")
check("server identifies as qi-comfy",
      byid.get(1, {}).get("result", {}).get("serverInfo", {}).get("name") == "qi-comfy")
tools = byid.get(2, {}).get("result", {}).get("tools", [])
names = sorted(t["name"] for t in tools)
check("all 8 tools listed", len(tools) == 8, str(names))
check("every tool has a schema", all(t.get("inputSchema") for t in tools))
check("notification got no reply", None not in byid)
check("ping answered", 3 in byid)
check("nothing on stderr", not err.strip(), err.strip()[:120])

print("\n[2] tools against the live ComfyUI")


def call(tool, args=None, env=None):
    r, _ = rpc([
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": tool, "arguments": args or {}}},
    ], env=env)
    for m in r:
        if m.get("id") == 2:
            return json.loads(m["result"]["content"][0]["text"])
    return {}


st = call("comfy_status")
check("status reports reachable", st.get("reachable") is True, str(st)[:120])
check("reports comfyui version", bool(st.get("comfyui_version")), str(st.get("comfyui_version")))
check("sees the GPU", bool(st.get("devices")), str(st.get("devices"))[:90])

mods = call("comfy_models")
check("model scan succeeded", "models" in mods, str(mods)[:120])
ck = mods.get("models", {}).get("checkpoints", {})
check("finds checkpoints", (ck.get("count") or 0) > 0, f"{ck.get('count')} found")
check("flags empty categories", isinstance(mods.get("empty_categories"), list),
      str(mods.get("empty_categories")))

ni = call("comfy_node_info", {"node": "UpscaleModelLoader"})
check("node introspection works", ni.get("node") == "UpscaleModelLoader", str(ni)[:100])
ni2 = call("comfy_node_info", {"node": "NoSuchNodeXYZ"})
check("unknown node handled cleanly", "error" in ni2, str(ni2)[:80])

print("\n[3] workflow handling")
tmp = tempfile.mkdtemp(prefix="wf_")
# an API-format graph with a title and a wired input
json.dump({
    "3": {"class_type": "KSampler",
          "inputs": {"seed": 1, "steps": 20, "model": ["4", 0]},
          "_meta": {"title": "Sampler"}},
    "6": {"class_type": "CLIPTextEncode",
          "inputs": {"text": "old prompt", "clip": ["4", 1]},
          "_meta": {"title": "Positive Prompt"}},
}, open(os.path.join(tmp, "demo.json"), "w"))
json.dump({"prompt": ["6", "text"]}, open(os.path.join(tmp, "demo.params.json"), "w"))
# an editor save, which must be rejected rather than queued
json.dump({"nodes": [], "links": []}, open(os.path.join(tmp, "editor_save.json"), "w"))
envwf = {"COMFY_WORKFLOWS": tmp}

wfs = call("comfy_workflows", {"detail": True}, env=envwf)
check("lists workflows", wfs.get("count") == 2, str(wfs.get("count")))
demo = next((w for w in wfs.get("workflows", []) if w["name"] == "demo"), {})
check("reads aliases", (demo.get("aliases") or {}).get("prompt") == ["6", "text"],
      str(demo.get("aliases")))
check("wired inputs are not settable", "3.model" not in (demo.get("settable") or {}),
      str(sorted(demo.get("settable") or {})))
check("title addressing offered", "Positive Prompt.text" in (demo.get("settable") or {}))
ed = next((w for w in wfs.get("workflows", []) if w["name"] == "editor_save"), {})
check("editor save is called out", "API Format" in (ed.get("error") or ""), str(ed)[:90])

print("\n[4] parameter placement (dry, via run against a bad graph)")
bad = call("comfy_run", {"workflow": "demo", "params": {"nope.zzz": 1}}, env=envwf)
check("bad param rejected with guidance", "cannot place parameter" in (bad.get("error") or ""),
      str(bad.get("error"))[:90])
wired = call("comfy_run", {"workflow": "demo", "params": {"3.model": "x"}}, env=envwf)
check("wired input refused", "wired" in (wired.get("error") or ""), str(wired.get("error"))[:80])
missing = call("comfy_run", {"workflow": "does_not_exist"}, env=envwf)
check("missing workflow reported", "no such workflow" in (missing.get("error") or ""),
      str(missing.get("error"))[:80])
esc = call("comfy_run", {"workflow": "../../etc/passwd"}, env=envwf)
check("path escape refused", "error" in esc, str(esc.get("error"))[:80])

print("\n[5] offline behaviour")
off = call("comfy_status", env={"COMFY_URL": "http://127.0.0.1:9"})
check("offline is explained, not crashed", off.get("reachable") is False
      and "not answering" in (off.get("error") or ""), str(off.get("error"))[:100])

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
