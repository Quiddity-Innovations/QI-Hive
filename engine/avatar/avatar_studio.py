# -*- coding: utf-8 -*-
"""
QI Avatar Studio — Gradio UI
Full pipeline: Script → Kokoro TTS → LivePortrait/Hallo2 → MP4 output
Port: 7862
"""
import sys
import os
import json
import subprocess
import tempfile
import shutil
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
AGENTS_FILE = BASE_DIR / "agents.json"
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
LP_PYTHON = "/home/hyosuke/miniconda3/envs/liveportrait/bin/python"
LP_DIR = "/home/hyosuke/qi_avatar/liveportrait"
WSL_DISTRO = "Ubuntu-24.04"
HALLO_PYTHON = "/home/hyosuke/miniconda3/envs/hallo/bin/python"
HALLO_DIR = "/home/hyosuke/qi_avatar/hallo2"

# Driving video library — curated from testing
DRIVING_VIDEOS = {
    "d13 — natural talking (recommended)": "assets/examples/driving/d13.mp4",
    "d11 — natural talking (9s)": "assets/examples/driving/d11.mp4",
    "d14 — expressive talking (17s)": "assets/examples/driving/d14.mp4",
    "d18 — calm talking (7s)": "assets/examples/driving/d18.mp4",
    "d20 — subtle talking (7s)": "assets/examples/driving/d20.mp4",
    "d10 — animated/energetic (14s)": "assets/examples/driving/d10.mp4",
    "d0 — short neutral (3s)": "assets/examples/driving/d0.mp4",
}

def load_agents():
    with open(AGENTS_FILE, encoding="utf-8") as f:
        return json.load(f)["agents"]

def to_wsl_path(p):
    p = str(p).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        drive = p[0].lower()
        p = f"/mnt/{drive}/{p[3:]}"
    return p

def agent_photo_path(agent_id):
    agents = load_agents()
    if agent_id not in agents:
        return None
    return str(BASE_DIR / agents[agent_id]["photo"])

def generate_voice(agent_id, script_text, speed_override):
    """Run Kokoro TTS, return path to WAV file."""
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    agents = load_agents()
    agent = agents[agent_id]
    voice = agent["voice"]
    speed = float(speed_override) if speed_override else agent["voice_speed"]
    lang = agent.get("language", "a")[0]  # 'a' for American English

    pipeline = KPipeline(lang_code=lang)
    samples = []
    for _, _, audio in pipeline(script_text, voice=voice, speed=speed, split_pattern=r"\n+"):
        samples.append(audio)

    if not samples:
        raise RuntimeError("Kokoro produced no audio.")

    combined = np.concatenate(samples)
    wav_path = OUTPUTS_DIR / f"{agent_id}_studio_voice.wav"
    sf.write(str(wav_path), combined, 24000)
    duration = len(combined) / 24000
    return str(wav_path), duration

def run_liveportrait(source_image_path, driving_video_path, wav_path, agent_id,
                     crop_scale, vx_ratio, vy_ratio,
                     flag_relative, flag_pasteback, flag_stitching,
                     animation_region, driving_option, driving_multiplier,
                     flag_crop_driving):
    """Run LivePortrait in WSL2, return path to output MP4."""

    wsl_source = to_wsl_path(source_image_path)
    wsl_driving = driving_video_path  # already a WSL path (LP assets)
    wsl_out_dir = f"/tmp/qi_studio_{agent_id}_{int(time.time())}"

    # Build boolean flags (tyro style: --flag or --no-flag)
    def bool_flag(name, val):
        return f"--{name}" if val else f"--no-{name}"

    cmd = (
        f"cd {LP_DIR} && "
        f"{LP_PYTHON} inference.py "
        f"-s {wsl_source} "
        f"-d {wsl_driving} "
        f"--output-dir {wsl_out_dir} "
        f"--animation_region {animation_region} "
        f"--driving_option {driving_option!r} "
        f"--driving_multiplier {driving_multiplier:.2f} "
        f"--scale {crop_scale:.2f} "
        f"--vx_ratio {vx_ratio:.2f} "
        f"--vy_ratio {vy_ratio:.3f} "
        f"{bool_flag('flag_relative_motion', flag_relative)} "
        f"{bool_flag('flag_pasteback', flag_pasteback)} "
        f"{bool_flag('flag_stitching', flag_stitching)} "
        f"{bool_flag('flag_crop_driving_video', flag_crop_driving)}"
    )

    result = subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", cmd],
        capture_output=True, text=True
    )

    # Find the output mp4 (not concat)
    find_cmd = f"find {wsl_out_dir} -name '*.mp4' ! -name '*concat*' | head -1"
    find_result = subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", find_cmd],
        capture_output=True, text=True
    )

    wsl_mp4 = find_result.stdout.strip()
    if not wsl_mp4:
        raise RuntimeError(
            f"LivePortrait produced no output.\nstdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
        )

    # Copy to Windows and merge with audio
    out_mp4 = OUTPUTS_DIR / f"{agent_id}_studio_noaudio.mp4"
    final_mp4 = OUTPUTS_DIR / f"{agent_id}_studio_final.mp4"
    wsl_out_win = to_wsl_path(out_mp4)

    subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", f"cp {wsl_mp4} {wsl_out_win}"],
        check=True
    )

    # Merge LP video + Kokoro audio with ffmpeg in WSL
    wsl_wav = to_wsl_path(wav_path)
    wsl_final = to_wsl_path(final_mp4)
    merge_cmd = (
        f"ffmpeg -y "
        f"-i {wsl_out_win} "
        f"-i {wsl_wav} "
        f"-c:v copy -c:a aac -shortest "
        f"{wsl_final}"
    )
    subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", merge_cmd],
        capture_output=True
    )

    # Cleanup temp dir
    subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", f"rm -rf {wsl_out_dir}"],
        capture_output=True
    )

    if final_mp4.exists():
        out_mp4.unlink(missing_ok=True)
        return str(final_mp4)
    elif out_mp4.exists():
        return str(out_mp4)
    else:
        raise RuntimeError("Output MP4 not found after copy.")


def run_hallo2(source_image_path, wav_path, agent_id,
               pose_weight, face_weight, lip_weight, face_expand_ratio):
    """Run Hallo2 audio-driven talking head in WSL2, return path to output MP4."""

    wsl_source = to_wsl_path(source_image_path)
    wsl_audio = to_wsl_path(wav_path)
    stem = Path(source_image_path).stem

    cmd = (
        f"cd {HALLO_DIR} && "
        f"{HALLO_PYTHON} scripts/inference_long.py "
        f"--config configs/inference/long.yaml "
        f"--source_image {wsl_source} "
        f"--driving_audio {wsl_audio} "
        f"--pose_weight {pose_weight:.2f} "
        f"--face_weight {face_weight:.2f} "
        f"--lip_weight {lip_weight:.2f} "
        f"--face_expand_ratio {face_expand_ratio:.2f}"
    )

    result = subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", cmd],
        capture_output=True, text=True, timeout=3600
    )

    result_path = f"~/qi_avatar/hallo2/output_long/debug/{stem}/merge_video.mp4"
    final_mp4 = OUTPUTS_DIR / f"{agent_id}_hallo2_studio.mp4"
    wsl_final = to_wsl_path(final_mp4)

    copy_cmd = f"cp {result_path} {wsl_final} && echo OK"
    copy_result = subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", copy_cmd],
        capture_output=True, text=True
    )

    if "OK" not in copy_result.stdout or not final_mp4.exists():
        raise RuntimeError(
            f"Hallo2 output not found.\nstdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
        )

    return str(final_mp4)


def run_retalking(face_mp4_path, wav_path, agent_id):
    """Apply video-retalking lip sync on top of a rendered video."""

    wsl_face = to_wsl_path(face_mp4_path)
    wsl_audio = to_wsl_path(wav_path)
    out_mp4 = OUTPUTS_DIR / f"{agent_id}_retalked.mp4"
    wsl_out = to_wsl_path(out_mp4)

    cmd = (
        f"export PATH=/home/hyosuke/miniconda3/envs/retalking/bin:$PATH && "
        f"export CUDA_HOME=/home/hyosuke/miniconda3/envs/retalking && "
        f"cd ~/qi_avatar/video-retalking && "
        f"/home/hyosuke/miniconda3/envs/retalking/bin/python inference.py "
        f"--face {wsl_face} "
        f"--audio {wsl_audio} "
        f"--outfile {wsl_out}"
    )

    result = subprocess.run(
        ["wsl", "-d", WSL_DISTRO, "bash", "-c", cmd],
        capture_output=True, text=True, timeout=3600
    )

    if not out_mp4.exists():
        raise RuntimeError(
            f"video-retalking failed.\nstdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
        )

    return str(out_mp4)


def pipeline_generate(
    agent_id, custom_photo, script_text, voice_speed,
    render_engine,
    driving_choice, custom_driving,
    crop_scale, vx_ratio, vy_ratio,
    flag_relative, flag_pasteback, flag_stitching,
    animation_region, driving_option, driving_multiplier,
    flag_crop_driving,
    hallo_pose_weight, hallo_face_weight, hallo_lip_weight, hallo_expand_ratio,
    apply_retalking,
    progress=None
):
    """Full pipeline: TTS → LivePortrait or Hallo2 → optional retalking → final MP4."""
    OUTPUTS_DIR.mkdir(exist_ok=True)
    log = []

    def status(msg):
        log.append(msg)
        return "\n".join(log)

    if not script_text or not script_text.strip():
        return None, None, "⚠️ Please enter a script."

    # Resolve source image
    if custom_photo:
        source_image = custom_photo
    else:
        source_image = agent_photo_path(agent_id)
        if not source_image or not Path(source_image).exists():
            return None, None, f"⚠️ No photo found for agent '{agent_id}'. Please upload one."

    # Resolve driving video (LivePortrait only)
    if custom_driving:
        wsl_driving = to_wsl_path(custom_driving)
    else:
        wsl_driving = f"{LP_DIR}/{DRIVING_VIDEOS[driving_choice]}"

    total_steps = 2 + (1 if apply_retalking else 0)
    yield None, None, status(f"🎙️ Step 1/{total_steps} — Generating voice with Kokoro...")

    try:
        wav_path, duration = generate_voice(agent_id, script_text.strip(), voice_speed)
        yield str(wav_path), None, status(f"✅ Voice ready — {duration:.1f}s  →  {Path(wav_path).name}")
    except Exception as e:
        yield None, None, status(f"❌ TTS failed: {e}")
        return

    engine_label = "Hallo2 (audio-driven)" if render_engine == "Hallo2" else "LivePortrait"
    yield str(wav_path), None, status(
        f"🎬 Step 2/{total_steps} — {engine_label} rendering...\n"
        f"   Source: {Path(source_image).name}\n"
        + (
            f"   Driver: {driving_choice if not custom_driving else Path(custom_driving).name}\n"
            f"   Region: {animation_region}  |  Multiplier: {driving_multiplier}"
            if render_engine == "LivePortrait"
            else f"   Pose: {hallo_pose_weight}  Face: {hallo_face_weight}  Lip: {hallo_lip_weight}"
        )
    )

    mp4_path = None
    try:
        if render_engine == "Hallo2":
            mp4_path = run_hallo2(
                source_image, wav_path, agent_id,
                hallo_pose_weight, hallo_face_weight, hallo_lip_weight, hallo_expand_ratio
            )
        else:
            mp4_path = run_liveportrait(
                source_image, wsl_driving, wav_path, agent_id,
                crop_scale, vx_ratio, vy_ratio,
                flag_relative, flag_pasteback, flag_stitching,
                animation_region, driving_option, driving_multiplier,
                flag_crop_driving
            )
        yield str(wav_path), mp4_path, status(f"✅ {engine_label} done  →  {Path(mp4_path).name}")
    except Exception as e:
        yield str(wav_path), None, status(f"❌ {engine_label} failed:\n{e}")
        return

    if apply_retalking and mp4_path:
        yield str(wav_path), mp4_path, status(
            f"👄 Step 3/{total_steps} — video-retalking lip sync...\n"
            f"   Input: {Path(mp4_path).name}"
        )
        try:
            retalked = run_retalking(mp4_path, wav_path, agent_id)
            yield str(wav_path), retalked, status(
                f"✅ Done!  →  {Path(retalked).name}\n"
                f"   Saved to: C:\\QIH\\engine\\avatar\\outputs\\"
            )
        except Exception as e:
            yield str(wav_path), mp4_path, status(
                f"⚠️ Retalking failed (showing original render):\n{e}"
            )
    else:
        yield str(wav_path), mp4_path, status(
            f"✅ Done!  →  {Path(mp4_path).name}\n"
            f"   Saved to: C:\\QIH\\engine\\avatar\\outputs\\"
        )


# ── Gradio UI ────────────────────────────────────────────────────────────────

import gradio as gr

agents = load_agents()
agent_choices = list(agents.keys())
agent_labels = {aid: f"{a['name']} ({a['role']})" for aid, a in agents.items()}

def load_agent_defaults(agent_id):
    """Return photo path and voice speed for selected agent."""
    a = agents.get(agent_id, {})
    photo = str(BASE_DIR / a.get("photo", ""))
    photo = photo if Path(photo).exists() else None
    return photo, a.get("voice_speed", 1.0), a.get("description", "")

with gr.Blocks(title="QI Avatar Studio") as demo:

    gr.HTML("""
        <div class="studio-header">
            <h1>🎭 QI Avatar Studio</h1>
            <p style="color:#666; margin:0">Script → Voice → Talking Avatar</p>
        </div>
    """)

    with gr.Row():
        # ── LEFT COLUMN: Agent + Script ─────────────────────────────────────
        with gr.Column(scale=1):

            gr.Markdown("### 👤 Step 1 — Agent & Portrait")
            with gr.Group():
                agent_select = gr.Dropdown(
                    choices=agent_choices,
                    value="tasuke",
                    label="Agent",
                    info="Preloaded agents from agents.json"
                )
                agent_desc = gr.Textbox(
                    label="Description",
                    value=agents["tasuke"]["description"],
                    interactive=False, lines=1
                )
                with gr.Row():
                    source_image = gr.Image(
                        label="Portrait (auto-loaded or upload your own)",
                        type="filepath",
                        value=agent_photo_path("tasuke"),
                        height=220
                    )

            gr.Markdown("### 🎙️ Step 2 — Script & Voice")
            with gr.Group():
                script_text = gr.Textbox(
                    label="Script (what the avatar will say)",
                    placeholder="Type the script here...",
                    lines=5,
                    max_lines=12
                )
                with gr.Row():
                    voice_speed = gr.Slider(
                        minimum=0.7, maximum=1.3, value=0.95, step=0.05,
                        label="Voice Speed"
                    )
                preview_voice_btn = gr.Button("🔊 Preview Voice Only", variant="secondary", size="sm")

        # ── RIGHT COLUMN: Motion Settings ───────────────────────────────────
        with gr.Column(scale=1):

            gr.Markdown("### 🎬 Step 3 — Render Engine & Motion")
            with gr.Group():
                render_engine = gr.Radio(
                    choices=["LivePortrait", "Hallo2"],
                    value="LivePortrait",
                    label="Render Engine",
                    info="LivePortrait: fast, great quality. Hallo2: audio-driven lip sync, slower (~30 min)."
                )

            with gr.Group(visible=True) as lp_group:
                driving_choice = gr.Dropdown(
                    choices=list(DRIVING_VIDEOS.keys()),
                    value="d13 — natural talking (recommended)",
                    label="Driving Video (LivePortrait)",
                    info="Controls head pose, expressions and mouth motion pattern"
                )
                custom_driving = gr.Video(
                    label="Or upload your own driving video (optional)",
                    height=140
                )

            with gr.Group(visible=False) as hallo_group:
                with gr.Row():
                    hallo_pose_weight = gr.Slider(0.1, 2.0, value=0.8, step=0.1, label="Pose weight")
                    hallo_face_weight = gr.Slider(0.1, 2.0, value=1.2, step=0.1, label="Face weight")
                    hallo_lip_weight = gr.Slider(0.1, 2.0, value=1.5, step=0.1, label="Lip weight")
                hallo_expand_ratio = gr.Slider(0.8, 1.5, value=1.0, step=0.05, label="Face expand ratio")

            with gr.Accordion("⚙️ Advanced Animation Options (LivePortrait)", open=False):
                with gr.Row():
                    flag_relative = gr.Checkbox(value=True, label="Relative motion")
                    flag_pasteback = gr.Checkbox(value=True, label="Paste-back")
                    flag_stitching = gr.Checkbox(value=True, label="Stitching")
                    flag_crop_driving = gr.Checkbox(value=False, label="Crop driving")

                with gr.Row():
                    animation_region = gr.Radio(
                        choices=["all", "exp", "pose", "lip", "eyes"],
                        value="all", label="Animation region",
                        info="'all' = full face. 'lip' = mouth only. 'exp' = expressions only."
                    )
                with gr.Row():
                    driving_option = gr.Radio(
                        choices=["expression-friendly", "pose-friendly"],
                        value="expression-friendly", label="Driving mode"
                    )
                with gr.Row():
                    driving_multiplier = gr.Slider(
                        minimum=0.5, maximum=2.0, value=1.0, step=0.05,
                        label="Motion intensity",
                        info="Higher = more exaggerated motion. Lower = more subtle."
                    )

            with gr.Accordion("✂️ Crop Settings", open=False):
                with gr.Row():
                    crop_scale = gr.Number(value=2.3, label="Source crop scale", minimum=1.8, maximum=3.2, step=0.05)
                    vx_ratio = gr.Number(value=0.0, label="Crop X offset", minimum=-0.5, maximum=0.5, step=0.01)
                    vy_ratio = gr.Number(value=-0.125, label="Crop Y offset", minimum=-0.5, maximum=0.5, step=0.01)

            gr.Markdown("### ▶️ Step 4 — Generate")
            apply_retalking = gr.Checkbox(
                value=False,
                label="👄 Post-process with video-retalking (fixes lip sync — requires checkpoints)",
                info="Run video-retalking on top of the render for audio-matched lip sync. Needs checkpoints in ~/qi_avatar/video-retalking/checkpoints/"
            )
            generate_btn = gr.Button("🎬 Generate Avatar", variant="primary", size="lg")
            clear_btn = gr.ClearButton(
                components=None, value="🧹 Clear Outputs", size="sm"
            )

    # ── OUTPUT ROW ──────────────────────────────────────────────────────────
    gr.Markdown("---")
    gr.Markdown("### 🎧 Output")
    with gr.Row():
        with gr.Column(scale=1):
            audio_out = gr.Audio(
                label="Generated Voice",
                type="filepath",
                interactive=False
            )
        with gr.Column(scale=2):
            video_out = gr.Video(
                label="Final Avatar Video",
                autoplay=True,
                elem_classes=["output-video"],
                height=320
            )
    status_box = gr.Textbox(
        label="Pipeline Log",
        lines=6,
        interactive=False
    )

    # ── DRIVING VIDEO EXAMPLES ───────────────────────────────────────────────
    gr.Markdown("---")
    gr.Markdown("### 🎞️ Driving Video Reference Gallery")
    gr.Markdown("*These are the motion drivers. Click to preview. Use 'd13' or 'd11' for natural talking.*")
    with gr.Row():
        for label, rel_path in list(DRIVING_VIDEOS.items())[:4]:
            wsl_path = f"{LP_DIR}/{rel_path}"
            # Convert WSL path to Windows for display
            win_path = wsl_path.replace("/mnt/c/", "C:/").replace("/home/hyosuke", "//wsl.localhost/Ubuntu-24.04/home/hyosuke")
            gr.Video(
                value=None,
                label=label.split(" — ")[0],
                height=140,
                interactive=False
            )

    # ── WIRING ──────────────────────────────────────────────────────────────

    # Toggle engine-specific settings visibility
    def toggle_engine(engine):
        return gr.update(visible=engine == "LivePortrait"), gr.update(visible=engine == "Hallo2")

    render_engine.change(
        fn=toggle_engine,
        inputs=[render_engine],
        outputs=[lp_group, hallo_group]
    )

    # Auto-load agent photo + defaults when agent changes
    agent_select.change(
        fn=load_agent_defaults,
        inputs=[agent_select],
        outputs=[source_image, voice_speed, agent_desc]
    )

    # Preview voice only
    def preview_voice(agent_id, script, speed):
        if not script or not script.strip():
            return None, "⚠️ Enter some script text first."
        try:
            wav, dur = generate_voice(agent_id, script.strip(), speed)
            return wav, f"✅ Preview ready — {dur:.1f}s"
        except Exception as e:
            return None, f"❌ {e}"

    preview_voice_btn.click(
        fn=preview_voice,
        inputs=[agent_select, script_text, voice_speed],
        outputs=[audio_out, status_box]
    )

    # Full pipeline
    generate_btn.click(
        fn=pipeline_generate,
        inputs=[
            agent_select, source_image, script_text, voice_speed,
            render_engine,
            driving_choice, custom_driving,
            crop_scale, vx_ratio, vy_ratio,
            flag_relative, flag_pasteback, flag_stitching,
            animation_region, driving_option, driving_multiplier,
            flag_crop_driving,
            hallo_pose_weight, hallo_face_weight, hallo_lip_weight, hallo_expand_ratio,
            apply_retalking
        ],
        outputs=[audio_out, video_out, status_box]
    )

    # Clear outputs
    clear_btn.add([audio_out, video_out, status_box])


if __name__ == "__main__":
    OUTPUTS_DIR.mkdir(exist_ok=True)
    print("Starting QI Avatar Studio on http://localhost:7862")
    demo.queue(max_size=2).launch(
        server_name="0.0.0.0",
        server_port=7862,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(font=[gr.themes.GoogleFont("Inter")]),
    )
