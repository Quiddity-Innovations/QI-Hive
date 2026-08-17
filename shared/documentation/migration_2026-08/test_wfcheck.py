"""Exercise comfy_workflow_check against healthy and deliberately broken graphs."""
import json, os, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding="utf-8")
SERVER = r"C:\QIH\engine\mcp\qi_comfy_mcp.py"
fails = []


def check(name, cond, detail=""):
    print(("  PASS  " if cond else "  FAIL  ") + name + (f"  [{detail}]" if detail else ""))
    if not cond:
        fails.append(name)


def call(tool, args=None, env=None):
    e = dict(os.environ)
    e["COMFY_URL"] = "http://127.0.0.1:8189"
    e.update(env or {})
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": tool, "arguments": args or {}}}]
    p = subprocess.run([sys.executable, SERVER],
                       input="".join(json.dumps(m) + "\n" for m in msgs),
                       capture_output=True, text=True, encoding="utf-8", timeout=300, env=e)
    for line in p.stdout.splitlines():
        try:
            m = json.loads(line)
            if m.get("id") == 2:
                return json.loads(m["result"]["content"][0]["text"])
        except Exception:
            pass
    return {}


print("[1] the real workflows are ready")
for wf in ("video_upscale", "video_enhance"):
    r = call("comfy_workflow_check", {"workflow": wf},
             {"COMFY_WORKFLOWS": r"D:\AI\workflows"})
    check(f"{wf} ready_to_run", r.get("ready_to_run") is True,
          r.get("summary") or str(r)[:120])
    check(f"{wf} counted its nodes", (r.get("nodes_used") or 0) >= 4,
          str(r.get("nodes_used")))

print("\n[2] broken graphs are diagnosed")
tmp = tempfile.mkdtemp(prefix="wfchk_")
envt = {"COMFY_WORKFLOWS": tmp}

# a node type nobody has installed
json.dump({
    "1": {"class_type": "SomeExoticNodeThatDoesNotExist",
          "inputs": {"x": 1}, "_meta": {"title": "Exotic"}},
    "2": {"class_type": "UpscaleModelLoader",
          "inputs": {"model_name": "4x-UltraSharp.safetensors"}},
}, open(os.path.join(tmp, "missing_node.json"), "w"))

# a model filename that is not on disk
json.dump({
    "1": {"class_type": "UpscaleModelLoader",
          "inputs": {"model_name": "4x-NotInstalled-Fantasy.pth"}},
}, open(os.path.join(tmp, "missing_model.json"), "w"))

# a legal node with an illegal enum value
json.dump({
    "1": {"class_type": "ImageScale",
          "inputs": {"image": ["9", 0], "upscale_method": "telepathy",
                     "width": 512, "height": 512, "crop": "disabled"}},
}, open(os.path.join(tmp, "bad_enum.json"), "w"))

# the editor format, which cannot be queued
json.dump({"nodes": [], "links": []}, open(os.path.join(tmp, "editor.json"), "w"))

r = call("comfy_workflow_check", {"workflow": "missing_node"}, envt)
check("missing node detected", len(r.get("missing_nodes") or []) == 1,
      str(r.get("missing_nodes"))[:100])
check("missing node not ready", r.get("ready_to_run") is False)
check("names the offending class",
      (r.get("missing_nodes") or [{}])[0].get("class_type") == "SomeExoticNodeThatDoesNotExist")

r = call("comfy_workflow_check", {"workflow": "missing_model"}, envt)
check("missing model detected", len(r.get("missing_models") or []) == 1,
      str(r.get("missing_models"))[:140])
check("reports what it wants",
      (r.get("missing_models") or [{}])[0].get("wants") == "4x-NotInstalled-Fantasy.pth")
check("shows what is installed instead",
      "4x-UltraSharp.safetensors" in ((r.get("missing_models") or [{}])[0].get("installed") or []))

# A graph can reference only installed things and still be rejected for simply
# omitting a required field — workflows exported from an older ComfyUI lose
# fields added since. This was a real false "ready to run".
json.dump({
    "1": {"class_type": "RIFE VFI",
          "inputs": {"frames": ["9", 0], "ckpt_name": "rife47.pth", "multiplier": 2}},
}, open(os.path.join(tmp, "omits_required.json"), "w"))

r = call("comfy_workflow_check", {"workflow": "omits_required"}, envt)
absent = sorted(x["input"] for x in (r.get("missing_required_inputs") or []))
check("omitted required inputs detected", len(absent) >= 5, str(absent))
check("omission means not ready", r.get("ready_to_run") is False, r.get("summary", ""))
check("names dtype among them", "dtype" in absent, str(absent))
check("offers the default to use",
      any(x.get("suggested_default") is not None
          for x in (r.get("missing_required_inputs") or [])))

r = call("comfy_workflow_check", {"workflow": "bad_enum"}, envt)
check("bad enum flagged separately", len(r.get("invalid_values") or []) == 1,
      str(r.get("invalid_values"))[:120])
check("bad enum is not called a missing model", not r.get("missing_models"))

r = call("comfy_workflow_check", {"workflow": "editor"}, envt)
check("editor save rejected with guidance", "API Format" in (r.get("error") or ""),
      str(r.get("error"))[:90])

r = call("comfy_workflow_check", {"workflow": "nope_not_here"}, envt)
check("unknown workflow reported", "no such workflow" in (r.get("error") or ""),
      str(r.get("error"))[:80])

print("\n[3] tool is advertised")
msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}]
p = subprocess.run([sys.executable, SERVER],
                   input="".join(json.dumps(m) + "\n" for m in msgs),
                   capture_output=True, text=True, encoding="utf-8", timeout=120)
names = []
for line in p.stdout.splitlines():
    try:
        m = json.loads(line)
        if m.get("id") == 2:
            names = sorted(t["name"] for t in m["result"]["tools"])
    except Exception:
        pass
check("8 tools now", len(names) == 8, str(names))
check("comfy_workflow_check listed", "comfy_workflow_check" in names)

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
