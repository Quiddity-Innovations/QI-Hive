import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:9011"

feature = {
    "source_project": "QI_Hive",
    "name": "Avatar & Voice Layer — Phase N",
    "description": (
        "Each Hive agent (architect, builder, inspector, ops, scout, scribe, tester) "
        "plus Claude Code and Claude Work gets a unique avatar and voice. "
        "Rendered in a Hive Dashboard 'War Room' page. "
        "Stack: edge-tts or Kokoro TTS (local/free) for voice synthesis, "
        "SadTalker or LivePortrait (local) for avatar animation from still images, "
        "Ready Player Me for avatar design. Each agent has a personality signature "
        "expressed through voice tone and speed. Claude Code gets its own avatar. "
        "Goal: 4-way voice conversation interface between Claude Work, Claude Code, "
        "QI Hive agents, and Renne via chat/Telegram/LINE."
    ),
    "domain": "ui/voice/avatar"
}

decision = {
    "project_id": "QI_Hive",
    "title": "Claude Work / QI Hive 4-way integration architecture",
    "rationale": (
        "QI Brain acts as the central message bus between Claude Work (session-based), "
        "Claude Code (session-based), QI Hive agents (always-on), and Renne "
        "(via chat/Telegram/LINE/dispatch). "
        "Phase 1: shared dispatch format + /api/dispatch endpoint on QI Brain. "
        "Phase 2: secured Cloudflare tunnel so Claude Work can POST directly without Renne as relay. "
        "Awaiting Claude Work answers to 6 capability questions before building the endpoint."
    ),
    "impact_scope": "ecosystem",
    "tags": ["claude-work", "integration", "architecture", "4-way-comms"]
}

r1 = requests.post(f"{BASE}/api/log_feature", json=feature, timeout=5)
print(f"Feature log: {r1.status_code} — {r1.text[:120]}")

r2 = requests.post(f"{BASE}/api/log_decision", json=decision, timeout=5)
print(f"Decision log: {r2.status_code} — {r2.text[:120]}")
