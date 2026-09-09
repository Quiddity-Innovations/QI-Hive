# AI-GENERATED BEGIN (Claude Code, 2026-09-08)
"""QI Trinity Check — verifies the three-leg AI arrangement is healthy.

Trinity = Claude (spearhead) + ChatGPT via `codex mcp-server` (WSL, ChatGPT Plus
login) + Gemini via C:\\QIH\\engine\\mcp\\qi_gemini_mcp.py (free-tier AI Studio key).

Run by a human or by Claude on demand.  NEVER schedule this unattended — the
standing rule is "nothing unattended calls an assistant" (plan §3).  Without
--ping it makes no assistant calls at all (Gemini ListModels does not count
against generate quota; Codex is only inspected locally).

Usage:
  python C:\\QIH\\engine\\tools\\qi_trinity_check.py            # inspection only
  python C:\\QIH\\engine\\tools\\qi_trinity_check.py --ping     # + one cheap call per leg, logged to Agent HR
  python C:\\QIH\\engine\\tools\\qi_trinity_check.py --json     # machine-readable to stdout

Exit code: 0 all pass · 1 any FAIL · 2 could not run.
Report:   C:\\QIH\\data\\trinity\\check_YYYY-MM-DD_HHMM.json
Log:      C:\\QIH\\LOGS\\trinity_check.log  (one line per run, never a key, never prompt text)

What it catches (each was a real failure on 2026-09-08):
  * Codex CLI older than npm latest → old CLIs cannot decode /models and fall
    back to a model the ChatGPT plan rejects.
  * A running `codex mcp-server` whose binary was replaced after it started
    (Claude Code keeps the stale process until restart).
  * Codex not logged in / auth file missing.
  * Gemini key file missing, config model not visible to the key, daily cap near.
  * MCP entries missing from Claude Code's config.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SECRETS_ENV = Path(r"C:\QIH\secrets\trinity_gemini.env")
GEMINI_CFG = Path(r"C:\QIH\config\gemini_mcp.json")
GEMINI_USAGE_DIR = Path(r"C:\QIH\data\gemini_mcp")
GEMINI_MCP = Path(r"C:\QIH\engine\mcp\qi_gemini_mcp.py")
CLAUDE_JSON = Path(r"C:\Users\renne\.claude.json")
REPORT_DIR = Path(r"C:\QIH\data\trinity")
LOG_FILE = Path(r"C:\QIH\LOGS\trinity_check.log")
DAILY_DIR = Path(r"C:\QIH\LOGS\trinity_daily")
AGENT_HR = Path(r"C:\QIH\engine\hive\agents\agent_hr.py")
WSL = ["wsl.exe", "-d", "Ubuntu-24.04", "-u", "hyosuke", "--"]
CODEX_BIN = "/home/hyosuke/.npm-global/bin/codex"
COMPANION_WSL = "/mnt/c/QIH/engine/tools/qi_trinity_check_codex.sh"
CODEX_CHEAP_MODEL = "gpt-5.6-luna"   # ping model: cheapest listed; protects the Plus quota
CAP_WARN_FRACTION = 0.8

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def wsl(cmd: str, timeout=60) -> tuple[int, str]:
    """Run a bash -lc command in WSL; returns (rc, combined output) with the ps noise stripped."""
    try:
        p = subprocess.run(WSL + ["bash", "-lc", cmd], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        out = "\n".join(l for l in out.splitlines() if "screen size is bogus" not in l and "bubblewrap" not in l)
        return p.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except FileNotFoundError as e:
        return 127, str(e)


def gemini_key() -> str | None:
    if not SECRETS_ENV.exists():
        return None
    for line in SECRETS_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("GEMINI_API_KEY="):
            v = line.split("=", 1)[1].strip()
            return v or None
    return None


class Checks:
    def __init__(self):
        self.rows = []      # (leg, check, status, detail)
        self.hr_runs = []   # runs to record in Agent HR when --ping

    def add(self, leg, check, status, detail=""):
        self.rows.append({"leg": leg, "check": check, "status": status, "detail": detail})

    # ── Claude Code MCP wiring ─────────────────────────────────────────
    def check_mcp_config(self):
        try:
            d = json.loads(CLAUDE_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            self.add("wiring", "claude.json readable", FAIL, str(e))
            return
        m = d.get("mcpServers", {})
        for name, must in (("codex", "mcp-server"), ("qi-gemini", "qi_gemini_mcp.py")):
            entry = m.get(name)
            if not entry:
                self.add("wiring", f"MCP entry '{name}'", FAIL, "missing from claude.json mcpServers")
                continue
            blob = json.dumps(entry)
            self.add("wiring", f"MCP entry '{name}'", PASS if must in blob else FAIL, blob[:160])

    # ── Gemini leg ─────────────────────────────────────────────────────
    def check_gemini(self, ping: bool):
        key = gemini_key()
        self.add("gemini", "key file present", PASS if key else FAIL, str(SECRETS_ENV))
        self.add("gemini", "MCP server file", PASS if GEMINI_MCP.exists() else FAIL, str(GEMINI_MCP))
        try:
            cfg = json.loads(GEMINI_CFG.read_text(encoding="utf-8"))
        except Exception as e:
            cfg = {}
            self.add("gemini", "config readable", FAIL, str(e))
        model = cfg.get("model", "?")
        cap = int(cfg.get("daily_cap", 0) or 0)
        # daily usage (mirrors qi_gemini_mcp.py's counter file)
        used = 0
        uf = GEMINI_USAGE_DIR / f"usage_{datetime.now():%Y-%m-%d}.json"
        if uf.exists():
            try:
                u = json.loads(uf.read_text(encoding="utf-8"))
                used = int(u.get("count", u.get("calls", 0)) if isinstance(u, dict) else u)
            except Exception:
                pass
        st = PASS
        if cap and used >= cap:
            st = FAIL
        elif cap and used >= cap * CAP_WARN_FRACTION:
            st = WARN
        self.add("gemini", "daily quota", st, f"{used}/{cap} calls today, model={model}")
        if not key:
            return
        # ListModels is free of generate quota; proves key validity + model visibility
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?pageSize=100&key={key}"
            t0 = time.time()
            data = json.load(urllib.request.urlopen(url, timeout=30))
            names = {m["name"].replace("models/", "") for m in data.get("models", [])
                     if "generateContent" in m.get("supportedGenerationMethods", [])}
            ms = int((time.time() - t0) * 1000)
            self.add("gemini", "key accepted by API (ListModels)", PASS, f"{len(names)} generate models, {ms} ms")
            for k in ("model", "long_model"):
                want = cfg.get(k)
                if want:
                    self.add("gemini", f"config {k} visible to key", PASS if want in names else FAIL, want)
        except Exception as e:
            self.add("gemini", "key accepted by API (ListModels)", FAIL, str(e)[:200])
            return
        if ping:
            body = {"contents": [{"parts": [{"text": "Reply with exactly: TRINITY-OK"}]}]}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            t0 = time.time()
            try:
                r = json.load(urllib.request.urlopen(req, timeout=60))
                text = r["candidates"][0]["content"]["parts"][0]["text"].strip()
                ms = int((time.time() - t0) * 1000)
                ok = "TRINITY-OK" in text
                self.add("gemini", "ping generate", PASS if ok else FAIL, f"{text[:60]!r} {ms} ms")
                self.hr_runs.append({"agent": "gemini", "model": model, "task_desc": "trinity ping",
                                     "duration_ms": ms, "outcome": "pass" if ok else "fail",
                                     "tokens": r.get("usageMetadata", {}).get("totalTokenCount")})
            except Exception as e:
                self.add("gemini", "ping generate", FAIL, str(e)[:200])

    # ── Codex leg ──────────────────────────────────────────────────────
    def check_codex(self, ping: bool):
        rc, ver = wsl(f"{CODEX_BIN} --version")
        m = re.search(r"(\d+\.\d+\.\d+)", ver)
        installed = m.group(1) if m else None
        self.add("codex", "CLI present in WSL", PASS if installed else FAIL, ver[:120])
        if not installed:
            return
        rc, latest = wsl("npm view @openai/codex version 2>/dev/null | tail -1", timeout=90)
        lm = re.search(r"(\d+\.\d+\.\d+)", latest or "")
        latest_v = lm.group(1) if lm else None
        if latest_v:
            behind = tuple(map(int, installed.split("."))) < tuple(map(int, latest_v.split(".")))
            self.add("codex", "CLI up to date", WARN if behind else PASS,
                     f"installed {installed}, npm latest {latest_v}" + (" — upgrade: npm i -g @openai/codex@latest" if behind else ""))
        else:
            self.add("codex", "CLI up to date", WARN, f"installed {installed}; npm registry unreachable")
        # Everything else comes from the companion script (inline $(...) gets mangled through wsl.exe)
        rc, raw = wsl(f"sed 's/\\r$//' '{COMPANION_WSL}' | bash", timeout=60)
        info = {}
        for line in raw.splitlines():
            if line.startswith("{"):
                try:
                    info = json.loads(line)
                except json.JSONDecodeError:
                    pass
        if not info:
            self.add("codex", "companion probe", FAIL, raw[:160])
            return
        login = info.get("login", "")
        self.add("codex", "logged in (ChatGPT plan)", PASS if "Logged in" in login else FAIL, login[:120])
        total, stale = info.get("mcp_native_procs", 0), info.get("mcp_stale_procs", 0)
        self.add("codex", "MCP server processes", WARN if stale else PASS,
                 f"{total} native codex mcp-server running, {stale} on a deleted (pre-upgrade) binary"
                 + (" — restart Claude Code to respawn" if stale else ""))
        listed = [s for s in info.get("listed", "").split(",") if s]
        self.add("codex", "models visible to plan", PASS if listed else WARN, ", ".join(listed)[:200])
        cfg_model, cfg_sb = info.get("config_model"), info.get("config_sandbox")
        if not cfg_model:
            self.add("codex", "config.toml default model", WARN, "no ~/.codex/config.toml → CLI default is gpt-6-astra (most quota-expensive)")
        else:
            ok = (not listed) or cfg_model in listed
            self.add("codex", "config.toml default model", PASS if ok else FAIL,
                     f"{cfg_model}, sandbox={cfg_sb or 'unset'}" + ("" if ok else " — slug no longer offered; edit config.toml"))
        if listed and CODEX_CHEAP_MODEL not in listed:
            self.add("codex", "ping model still offered", WARN, f"{CODEX_CHEAP_MODEL} not in list; edit CODEX_CHEAP_MODEL")
        if ping:
            prompt = "Reply with exactly: TRINITY-OK. Do not run any commands."
            t0 = time.time()
            rc, out = wsl(f"cd /tmp && {CODEX_BIN} exec --skip-git-repo-check --model {CODEX_CHEAP_MODEL} "
                          f"--sandbox read-only --json '{prompt}'", timeout=240)
            ms = int((time.time() - t0) * 1000)
            msgs = [json.loads(l) for l in out.splitlines() if l.startswith("{")]
            texts = [m["item"]["text"] for m in msgs if m.get("type") == "item.completed"
                     and m.get("item", {}).get("type") == "agent_message"]
            cmds = sum(1 for m in msgs if m.get("item", {}).get("type") == "command_execution")
            usage = next((m.get("usage") for m in msgs if m.get("type") == "turn.completed"), None) or {}
            ok = rc == 0 and any("TRINITY-OK" in t for t in texts) and cmds == 0
            err = next((m for m in msgs if m.get("type") == "error"), None)
            detail = f"model={CODEX_CHEAP_MODEL} {ms} ms, commands={cmds}, reply={texts[-1][:40]!r}" if texts else out[-200:]
            if err:
                detail = json.dumps(err)[:200]
            self.add("codex", "ping exec (no commands allowed)", PASS if ok else FAIL, detail)
            self.hr_runs.append({"agent": "codex", "model": CODEX_CHEAP_MODEL, "task_desc": "trinity ping",
                                 "duration_ms": ms, "outcome": "pass" if ok else "fail",
                                 "tokens": (usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0) or None,
                                 "tool_uses": cmds})

    # ── Agent HR ───────────────────────────────────────────────────────
    def record_hr(self, session_id: str):
        if not self.hr_runs:
            return
        try:
            sys.path.insert(0, str(AGENT_HR.parent))
            import agent_hr  # noqa
            conn = agent_hr.get_conn()
            agent_hr.ensure_schema(conn)
            n = 0
            for r in self.hr_runs:
                run = {"agent": r["agent"], "project": "trinity", "task_desc": r["task_desc"],
                       "started_at": datetime.now().isoformat(timespec="seconds"),
                       "duration_ms": r.get("duration_ms"), "tokens": r.get("tokens"),
                       "tool_uses": r.get("tool_uses", 0), "outcome": r["outcome"],
                       "session_id": session_id, "model": r.get("model")}
                added, _ = agent_hr.record_run(conn, run, "qi_trinity_check")
                n += int(added)
            conn.commit()
            self.add("hr", "runs recorded in Agent HR", PASS, f"{n} rows → :8600/agents")
        except Exception as e:
            self.add("hr", "runs recorded in Agent HR", WARN, str(e)[:160])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ping", action="store_true", help="make one cheap call per assistant and log to Agent HR")
    ap.add_argument("--json", action="store_true", help="print JSON report to stdout")
    ap.add_argument("--session", default=f"trinity-check-{datetime.now():%Y%m%d-%H%M}")
    a = ap.parse_args()

    c = Checks()
    c.check_mcp_config()
    c.check_gemini(a.ping)
    c.check_codex(a.ping)
    if a.ping:
        c.record_hr(a.session)

    worst = FAIL if any(r["status"] == FAIL for r in c.rows) else WARN if any(r["status"] == WARN for r in c.rows) else PASS
    report = {"ts": datetime.now().isoformat(timespec="seconds"), "ping": a.ping, "overall": worst, "checks": c.rows}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    rp = REPORT_DIR / f"check_{datetime.now():%Y-%m-%d_%H%M}.json"
    rp.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    line = (f"{report['ts']} overall={worst} ping={a.ping} "
            f"pass={sum(r['status']==PASS for r in c.rows)} warn={sum(r['status']==WARN for r in c.rows)} "
            f"fail={sum(r['status']==FAIL for r in c.rows)} report={rp.name}\n")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line)
    # Dated copy for QI_TaskHealth (manifest target uses {date:%Y%m%d}). A rolling log
    # would let yesterday's PASS satisfy today's marker check; a per-day file cannot.
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    with (DAILY_DIR / f"trinity_check_{datetime.now():%Y%m%d}.log").open("a", encoding="utf-8") as f:
        f.write(line)

    if a.json:
        print(json.dumps(report, indent=1, ensure_ascii=False))
    else:
        icon = {PASS: "✅", WARN: "⚠️", FAIL: "❌"}
        print(f"QI Trinity Check — {report['ts']} — overall {icon[worst]} {worst}")
        w = max(len(r["check"]) for r in c.rows)
        for r in c.rows:
            print(f"  {icon[r['status']]} [{r['leg']:<6}] {r['check']:<{w}}  {r['detail']}")
        print(f"report: {rp}")
    sys.exit(0 if worst != FAIL else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never die silently
        print(f"trinity check could not run: {e}", file=sys.stderr)
        sys.exit(2)
# AI-GENERATED END
