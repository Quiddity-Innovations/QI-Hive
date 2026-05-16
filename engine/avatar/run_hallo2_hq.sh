#!/bin/bash
# Hallo2 high-quality render — 1024px source, tuned weights for better lip sync
set -e

AGENT=${1:-tasuke}
HALLO_DIR=~/qi_avatar/hallo2
PYTHON=~/miniconda3/envs/hallo/bin/python
OUTPUTS=/mnt/c/QIH/engine/avatar/outputs

case "$AGENT" in
  tasuke)
    PHOTO=/mnt/c/QIH/engine/avatar/inputs/tasuke_1024.jpg
    AUDIO=$OUTPUTS/tasuke_voice.wav
    ;;
  maia)
    PHOTO=/mnt/c/QIH/engine/avatar/inputs/maia_1024.png
    AUDIO=$OUTPUTS/maia_voice.wav
    ;;
  *)
    echo "Usage: $0 [tasuke|maia]"
    exit 1
    ;;
esac

echo "==> Hallo2 HQ render: $AGENT"
echo "    Photo : $PHOTO (1024px)"
echo "    Audio : $AUDIO"
echo ""

cd "$HALLO_DIR"
$PYTHON scripts/inference_long.py \
  --config configs/inference/long.yaml \
  --source_image "$PHOTO" \
  --driving_audio "$AUDIO" \
  --pose_weight 0.8 \
  --face_weight 1.2 \
  --lip_weight 1.5 \
  --face_expand_ratio 1.0

# Hallo2 uses image stem as output subfolder
STEM=$(basename "$PHOTO" | sed 's/\.[^.]*$//')
RESULT=~/qi_avatar/hallo2/output_long/debug/${STEM}/merge_video.mp4

if [ -f "$RESULT" ]; then
  cp "$RESULT" "$OUTPUTS/${AGENT}_hallo2_hq.mp4"
  echo "==> Saved: ${AGENT}_hallo2_hq.mp4"
else
  echo "ERROR: Result not found at $RESULT"
  exit 1
fi
