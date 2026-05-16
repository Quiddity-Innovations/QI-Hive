#!/bin/bash
# Render Tasuke Hattori delivering the Tokyo Times article (~4 min audio)
# Uses Hallo2 inference_long with HQ weights
set -e

HALLO_DIR=~/qi_avatar/hallo2
PYTHON=~/miniconda3/envs/hallo/bin/python
OUTPUTS=/mnt/c/QIH/engine/avatar/outputs

PHOTO=/mnt/c/QIH/engine/avatar/inputs/tasuke_1024.jpg
AUDIO=$OUTPUTS/tasuke_tokyo_times.wav

echo "========================================================"
echo "  Tasuke Hattori — Tokyo Times Article Render"
echo "  Audio: $(wsl -d Ubuntu-24.04 bash -c 'ffprobe -v quiet -show_entries format=duration -of csv=p=0 /mnt/c/QIH/engine/avatar/outputs/tasuke_tokyo_times.wav 2>/dev/null || echo unknown')s"
echo "  Photo: 1024px HQ source"
echo "========================================================"
echo ""

# Verify audio exists
if [ ! -f "$AUDIO" ]; then
    echo "ERROR: Audio not found at $AUDIO"
    echo "Run: python gen_tokyo_times_tts.py first"
    exit 1
fi

cd "$HALLO_DIR"

echo "==> Starting Hallo2 HQ inference (this will take 20-40 minutes)..."
$PYTHON scripts/inference_long.py \
    --config configs/inference/long.yaml \
    --source_image "$PHOTO" \
    --driving_audio "$AUDIO" \
    --pose_weight 0.8 \
    --face_weight 1.2 \
    --lip_weight 1.5 \
    --face_expand_ratio 1.0

# Output dir uses image stem
STEM=$(basename "$PHOTO" | sed 's/\.[^.]*$//')
RESULT=~/qi_avatar/hallo2/output_long/debug/${STEM}/merge_video.mp4

echo ""
if [ -f "$RESULT" ]; then
    cp "$RESULT" "$OUTPUTS/tasuke_tokyo_times.mp4"
    echo "==> Done! Saved: $OUTPUTS/tasuke_tokyo_times.mp4"
    echo ""
    # Get duration
    ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUTS/tasuke_tokyo_times.mp4" 2>/dev/null | \
        awk '{printf "    Duration: %.1f seconds (%.1f minutes)\n", $1, $1/60}'
else
    echo "ERROR: Result not found at $RESULT"
    echo "Check: ls ~/qi_avatar/hallo2/output_long/debug/"
    exit 1
fi
