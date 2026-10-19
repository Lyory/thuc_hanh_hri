#!/usr/bin/env bash
# Ghi màn hình ảo riêng :99 (RViz + YOLO); Ctrl+C để kết thúc MP4.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
mkdir -p evidence
exec ffmpeg -y -f x11grab -framerate 15 -video_size 1800x1000 \
  -i "${WEEK5_DEMO_DISPLAY:-:99}" -c:v libx264 -threads 2 -preset ultrafast \
  -crf 24 -pix_fmt yuv420p "${1:-evidence/week5_demo.mp4}"
