def information(request: Request):
        g = graphmap.build_graph()
        return render(request, "information.html", "information", "BU Hive Information",
                      categories=g["categories"], generated_at=g["generated_at"],
                      node_count=len(g["nodes"]), edge_count=len(g["edges"]))

    @app.get("/api/graph")
    def api_graph():
        return JSONResponse(graphmap.build_graph())

    # ---- Voice: same-origin proxy to the shared Claude Voice service ------
    # Keeps the browser same-origin (satisfies our CSP + reuses the login/CSRF
    # gate) while the actual speak/transcribe work happens in ClaudeVoice's
    # loopback service. Any BU web tool can adopt this same 3-route pattern.
    _voice = s.raw.get("voice", {}) or {}
    VOICE_URL = str(_voice.get("service_url", "http://127.0.0.1:8735")).rstrip("/")
    VOICE_ENABLED = bool(_voice.get("enabled", True))

    @app.get("/api/voice/health")
    async def voice_health(request: Request):
        # Lets the UI decide whether to show mic / speak controls at all.
        if not auth.current_user(request):
            return JSONResponse({"available": False}, status_code=401)
        if not VOICE_ENABLED:
            return JSONResponse({"available": False, "reason": "disabled"})
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                r = await c.get(VOICE_URL + "/health")
            info = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            return JSONResponse({"available": r.status_code == 200, **info})
        except httpx.HTTPError:
            return JSONResponse({"available": False, "reason": "unreachable"})

    @app.post("/api/voice/speak")
    async def voice_speak(request: Request):
        auth.require(request, "member")
        if not VOICE_ENABLED:
            return JSONResponse({"error": "voice disabled"}, status_code=503)
        try:
            payload = await request.json()
        except (ValueError, TypeError):
            payload = {}
        text = (payload.get("text") or "").strip()
        if not text:
            return JSONResponse({"error": "empty text"}, status_code=400)
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(VOICE_URL + "/speak",
                                 json={"text": text, "wait": bool(payload.get("wait"))})
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.HTTPError:
            return JSONResponse({"error": "voice service unreachable"}, status_code=503)

    @app.post("/api/voice/transcribe")
    async def voice_transcribe(request: Request, audio: UploadFile = File(...)):
        auth.require(request, "member")
        if not VOICE_ENABLED:
            return JSONResponse({"error": "voice disabled"}, status_code=503)
        data = await audio.read()
        if not data:
            return JSONResponse({"error": "empty audio"}, status_code=400)
        try:
            async with httpx.AsyncClient(timeout=120.0) as c:
                r = await c.post(VOICE_URL + "/transcribe",
                                 files={"audio": (audio.filename or "clip.webm", data,
                                                  audio.content_type or "audio/webm")})
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.HTTPError:
            return JSONResponse({"error": "voice service unreachable"}, status_code=503)

    # ---- Graph editor: custom nodes/edges + file browser (admin) ---------
    def _browse_roots() -> list[Path]:
        roots = [s.home] + s.path_list("library_roots") + s.path_list("log_roots")
        for p in registry.projects():
            if p.get("path"):
                roots.append(Path(p["path"]))
        out, seen = [], set()
        for r in roots:
            try:
                rr = r.resolve()
            except OSError:
                continue
            if rr.exists() and str(rr) not in seen:
                seen.add(str(rr)); out.append(rr)
        return out

    def _within_roots(target: Path, roots: list[Path]) -> bool:
        import os as _os
        t = str(target)
        return any(t == str(r) or t.startswith(str(r) + _os.sep) for r in roots)

    @app.get("/api/graph/browse")
    def graph_browse(request: Request, path: str = ""):
        if not auth.is_admin(auth.current_user(request)):
            return JSONResponse({"error": "admin only"}, status_code=403)
        roots = _browse_roots()
        if not path:
            return JSONResponse({"path": "", "parent": None, "atRoot": True,
                                 "dirs": [{"name": str(r), "path": str(r)} for r in roots],
                                 "files": []})
        target = Path(path).resolve()
        if not _within_roots(target, roots) or not target.exists():
            return JSONResponse({"error": "path not allowed"}, status_code=403)
        dirs, files = [], []
        if target.is_dir():
            try:
                for e in sorted(target.iterdir(), key=lambda x: x.name.lower()):
                    try:
                        (dirs if e.is_dir() else files).append({"name": e.name, "path": str(e)})
                    except OSError:
                        continue
                    if len(dirs) + len(files) >= 500:
                        break
            except OSError:
                pass
        at_root = any(str(target) == str(r) for r in roots)
        parent = "" if at_root else str(target.parent)
        return JSONResponse({"path": str(target), "parent": parent, "atRoot": at_root,
                             "dirs": dirs, "files": files})

    @app.get("/api/graph/custom")
    def graph_custom(request: Request):
        if not auth.is_admin(auth.current_user(request)):
            return JSONResponse({"error": "admin only"}, status_code=403)
        g = graphmap.build_graph()
        nodes = [{"id": n["id"], "label": n[