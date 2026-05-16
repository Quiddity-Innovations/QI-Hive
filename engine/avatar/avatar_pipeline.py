# -*- coding: utf-8 -*-
"""
QI Avatar Pipeline
Orchestrates: Kokoro TTS -> Hallo2 talking-head -> MP4 output
Usage: python avatar_pipeline.py <agent_id> <"text" or @script.txt>
"""
import sys
import os
import json
import subprocess
import time
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent
AGENTS_FILE = BASE_DIR / "agents.json"
INPUTS_DIR = BASE_DIR / "inputs"
OUTPUTS_DIR = BASE_DIR / "outputs"
VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"


def load_config():
    with open(AGENTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_text(text_arg):
    if text_arg.startswith("@"):
        path = Path(text_arg[1:])
        return path.read_text(encoding="utf-8").strip()
    return text_arg.strip()


def step_tts(agent, text, cfg):
    """Generate voice WAV with Kokoro-82M."""
    print(f"\n[1/3] TTS: {agent['name']} ({agent['voice']}) ...", flush=True)

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    kokoro_cfg = cfg["kokoro"]
    pipeline = KPipeline(lang_code=kokoro_cfg["lang_code"])

    samples = []
    for _, _, audio in pipeline(
        text,
        voice=agent["voice"],
        speed=agent["voice_speed"],
        split_pattern=r"\n+",
    ):
        samples.append(audio)

    if not samples:
        raise RuntimeError("Kokoro produced no audio output.")

    combined = np.concatenate(samples)
    wav_path = OUTPUTS_DIR / f"{agent['id']}_voice.wav"
    sf.write(str(wav_path), combined, kokoro_cfg["sample_rate"])
    duration = len(combined) / kokoro_cfg["sample_rate"]
    print(f"    -> {wav_path.name}  ({duration:.1f}s)", flush=True)
    return wav_path, duration


def step_hallo2(agent, wav_path, cfg):
    """Run Hallo2 inference via WSL2."""
    print(f"\n[2/3] Hallo2: rendering talking-head ...", flush=True)

    h = cfg["hallo2"]
    photo_path = BASE_DIR / agent["photo"]
    if not photo_path.exists():
        raise FileNotFoundError(f"Agent photo not found: {photo_path}")

    # Convert Windows paths to WSL2 /mnt/c/... paths
    def to_wsl(p):
        p = str(p).replace("\\", "/")
        if p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}/{p[3:]}"
        return p

    wsl_photo = to_wsl(photo_path)
    wsl_audio = to_wsl(wav_path)
    wsl_output_base = h["output_base"]
    agent_id = agent["id"]

    cmd = (
        f"cd {h['repo_path']} && "
        f"{h['conda_env']}/bin/python scripts/inference_long.py "
        f"--config {h['config']} "
        f"--source_image {wsl_photo} "
        f"--driving_audio {wsl_audio} "
        f"--pose_weight {h['pose_weight']} "
        f"--face_weight {h['face_weight']} "
        f"--lip_weight {h['lip_weight']} "
        f"--face_expand_ratio {h['face_expand_ratio']}"
    )

    result = subprocess.run(
        ["wsl", "-d", h["wsl_distro"], "bash", "-c", cmd],
        capture_output=False,  # let output stream live
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Hallo2 inference failed (exit {result.returncode})")

    # Determine where Hallo2 put the output (uses image stem as subdir)
    image_stem = photo_path.stem
    merge_path = f"{wsl_output_base}/{image_stem}/merge_video.mp4"

    out_path = OUTPUTS_DIR / f"{agent_id}_avatar.mp4"
    wsl_out = to_wsl(out_path)

    copy_cmd = f"cp {merge_path} {wsl_out} && echo OK"
    copy_result = subprocess.run(
        ["wsl", "-d", h["wsl_distro"], "bash", "-c", copy_cmd],
        capture_output=True,
        text=True,
    )
    if "OK" not in copy_result.stdout:
        raise RuntimeError(
            f"Could not copy result from WSL2.\n"
            f"Expected: {merge_path}\n"
            f"stderr: {copy_result.stderr}"
        )

    print(f"    -> {out_path.name}", flush=True)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="QI Avatar Pipeline")
    parser.add_argument("agent", help="Agent ID (tasuke, maia, naya, kaze)")
    parser.add_argument(
        "text",
        help='Script text or @path/to/script.txt',
    )
    parser.add_argument(
        "--no-tts", action="store_true",
        help="Skip TTS step (use existing <agent>_voice.wav)"
    )
    args = parser.parse_args()

    cfg = load_config()
    agents = cfg["agents"]

    if args.agent not in agents:
        print(f"ERROR: Unknown agent '{args.agent}'. Available: {list(agents.keys())}")
        sys.exit(1)

    agent = agents[args.agent]
    agent["id"] = args.agent  # inject id for downstream use

    OUTPUTS_DIR.mkdir(exist_ok=True)

    t_start = time.time()

    if args.no_tts:
        wav_path = OUTPUTS_DIR / f"{args.agent}_voice.wav"
        if not wav_path.exists():
            print(f"ERROR: --no-tts specified but {wav_path} not found.")
            sys.exit(1)
        print(f"\n[1/3] TTS: skipped (using {wav_path.name})", flush=True)
    else:
        text = get_text(args.text)
        wav_path, _ = step_tts(agent, text, cfg)

    mp4_path = step_hallo2(agent, wav_path, cfg)

    elapsed = time.time() - t_start
    print(f"\n[3/3] Done in {elapsed:.0f}s")
    print(f"      Output: {mp4_path}")


if __name__ == "__main__":
    main()
