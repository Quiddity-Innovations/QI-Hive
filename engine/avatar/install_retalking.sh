#!/bin/bash
set -e

PIP=/home/hyosuke/miniconda3/envs/retalking/bin/pip
PYTHON=/home/hyosuke/miniconda3/envs/retalking/bin/python

echo "Installing video-retalking requirements..."

# Install core requirements (pinned versions)
$PIP install basicsr==1.4.2 -q 2>&1 | tail -1
$PIP install kornia==0.5.1 -q 2>&1 | tail -1
$PIP install face-alignment==1.3.4 -q 2>&1 | tail -1
$PIP install einops==0.4.1 -q 2>&1 | tail -1
$PIP install facexlib==0.2.5 -q 2>&1 | tail -1
$PIP install librosa==0.9.2 -q 2>&1 | tail -1
$PIP install dlib==19.24.0 -q 2>&1 | tail -1
$PIP install "numpy==1.23.4" -q 2>&1 | tail -1
$PIP install ninja==1.10.2.3 -q 2>&1 | tail -1
$PIP install imageio imageio-ffmpeg realesrgan gfpgan -q 2>&1 | tail -1

echo "Verifying..."
$PYTHON -c "import torch, cv2, librosa, dlib; print('All imports OK')"
echo "Done"
