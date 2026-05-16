#!/bin/bash
# Run video-retalking on a LivePortrait or Hallo2 render to fix lip sync
# Usage: bash run_retalking.sh <face_video> <audio_wav> <output_name>
# Example: bash run_retalking.sh tasuke_tokyo_times.mp4 tasuke_tokyo_times.wav tasuke_tokyo_times_synced.mp4
set -e

RETALKING_DIR=~/qi_avatar/video-retalking
PYTHON=/home/hyosuke/miniconda3/envs/retalking/bin/python
OUTPUTS=/mnt/c/QIH/engine/avatar/outputs

FACE_VIDEO=${1:-}
AUDIO_WAV=${2:-}
OUTPUT_NAME=${3:-output_retalked.mp4}

if [ -z "$FACE_VIDEO" ] || [ -z "$AUDIO_WAV" ]; then
    echo "Usage: $0 <face_video.mp4> <audio.wav> [output_name.mp4]"
    echo ""
    echo "Examples:"
    echo "  $0 tasuke_tokyo_times.mp4 tasuke_tokyo_times.wav tasuke_tokyo_times_synced.mp4"
    echo "  $0 tasuke_lp_d13.mp4 tasuke_voice.wav tasuke_retalked.mp4"
    exit 1
fi

FACE_PATH="$OUTPUTS/$FACE_VIDEO"
AUDIO_PATH="$OUTPUTS/$AUDIO_WAV"
OUT_PATH="$OUTPUTS/$OUTPUT_NAME"

if [ ! -f "$FACE_PATH" ]; then
    echo "ERROR: Face video not found: $FACE_PATH"
    exit 1
fi

if [ ! -f "$AUDIO_PATH" ]; then
    echo "ERROR: Audio not found: $AUDIO_PATH"
    exit 1
fi

echo "========================================================"
echo "  Video-ReTalking Lip Sync"
echo "  Face: $FACE_VIDEO"
echo "  Audio: $AUDIO_WAV"
echo "  Output: $OUTPUT_NAME"
echo "========================================================"
echo ""

export PATH=/home/hyosuke/miniconda3/envs/retalking/bin:$PATH
export CUDA_HOME=/home/hyosuke/miniconda3/envs/retalking
export TORCH_CUDA_ARCH_LIST="12.0"

cd "$RETALKING_DIR"
$PYTHON inference.py \
    --face "$FACE_PATH" \
    --audio "$AUDIO_PATH" \
    --outfile "$OUT_PATH" \
    --face_det_batch_size 4 \
    --LNet_batch_size 16

if [ -f "$OUT_PATH" ]; then
    echo ""
    echo "==> Done! Saved: $OUT_PATH"
else
    echo "ERROR: Output not found at $OUT_PATH"
    exit 1
fi
