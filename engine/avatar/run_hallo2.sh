#!/bin/bash
# QI Hallo2 — direct inference wrapper (called by avatar_pipeline.py or manually)
# Usage: bash run_hallo2.sh <agent_id> [audio_wsl_path]
# Example: bash run_hallo2.sh tasuke /mnt/c/QIH/engine/avatar/outputs/tasuke_voice.wav

set -e

AGENT=${1:-tasuke}
AUDIO=${2:-/mnt/c/QIH/engine/avatar/outputs/${AGENT}_voice.wav}

HALLO_DIR=~/qi_avatar/hallo2
PYTHON=~/miniconda3/envs/hallo/bin/python
CONFIG=configs/inference/long.yaml
OUTPUT_BASE=~/qi_avatar/hallo2/output_long/debug

case "$AGENT" in
  tasuke) PHOTO=/mnt/c/QIH/engine/avatar/inputs/tasuke.jpg ;;
  maia)   PHOTO=/mnt/c/QIH/engine/avatar/inputs/maia.png ;;
  naya)   PHOTO=/mnt/c/QIH/engine/avatar/inputs/naya.png ;;
  kaze)   PHOTO=/mnt/c/QIH/engine/avatar/inputs/kaze.jpg ;;
  *)
    echo "Unknown agent: $AGENT"
    echo "Available: tasuke maia naya kaze"
    exit 1
    ;;
esac

echo "==> Hallo2 inference: $AGENT"
echo "    Photo : $PHOTO"
echo "    Audio : $AUDIO"
echo ""

cd "$HALLO_DIR"
$PYTHON scripts/inference_long.py \
  --config "$CONFIG" \
  --source_image "$PHOTO" \
  --driving_audio "$AUDIO" \
  --pose_weight 1.0 \
  --face_weight 1.0 \
  --lip_weight 1.0 \
  --face_expand_ratio 1.2

STEM=$(basename "$PHOTO" | sed 's/\.[^.]*$//')
RESULT="$OUTPUT_BASE/$STEM/merge_video.mp4"
DEST="/mnt/c/QIH/engine/avatar/outputs/${AGENT}_avatar.mp4"

if [ -f "$RESULT" ]; then
  cp "$RESULT" "$DEST"
  echo ""
  echo "==> Saved: C:\\QIH\\engine\\avatar\\outputs\\${AGENT}_avatar.mp4"
else
  echo "ERROR: merge_video.mp4 not found at $RESULT"
  exit 1
fi
