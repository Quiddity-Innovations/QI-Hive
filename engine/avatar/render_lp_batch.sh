#!/bin/bash
# Render Tasuke with multiple driving videos to find best natural talking motion
set -e

LP=/home/hyosuke/qi_avatar/liveportrait
PYTHON=/home/hyosuke/miniconda3/envs/liveportrait/bin/python
SOURCE=/mnt/c/QIH/engine/avatar/inputs/tasuke.jpg
OUT=/tmp/lp_batch
mkdir -p $OUT

cd $LP

# talking.pkl — motion template specifically labelled "talking"
echo "==> talking.pkl..."
$PYTHON inference.py \
  -s $SOURCE \
  -d assets/examples/driving/talking.pkl \
  --output-dir $OUT 2>&1 | grep "Animated video:" | head -1

# d11 — 9s
echo "==> d11 (9s)..."
$PYTHON inference.py \
  -s $SOURCE \
  -d assets/examples/driving/d11.mp4 \
  --output-dir $OUT 2>&1 | grep "Animated video:" | head -1

# d14 — 17s
echo "==> d14 (17s)..."
$PYTHON inference.py \
  -s $SOURCE \
  -d assets/examples/driving/d14.mp4 \
  --output-dir $OUT 2>&1 | grep "Animated video:" | head -1

# d18 — 7s
echo "==> d18 (7s)..."
$PYTHON inference.py \
  -s $SOURCE \
  -d assets/examples/driving/d18.mp4 \
  --output-dir $OUT 2>&1 | grep "Animated video:" | head -1

# d20 — 7s
echo "==> d20 (7s)..."
$PYTHON inference.py \
  -s $SOURCE \
  -d assets/examples/driving/d20.mp4 \
  --output-dir $OUT 2>&1 | grep "Animated video:" | head -1

# Copy all results to Windows
echo ""
echo "Copying to outputs..."
for f in $OUT/tasuke--*.mp4; do
  name=$(basename $f)
  cp $f /mnt/c/QIH/engine/avatar/outputs/lp_$name
  echo "  -> lp_$name"
done

echo "Done!"
