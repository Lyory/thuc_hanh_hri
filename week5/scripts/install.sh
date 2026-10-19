#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
apt_command=(apt-get)
if [[ $EUID -ne 0 ]]; then
  apt_command=(sudo apt-get)
fi
"${apt_command[@]}" update
"${apt_command[@]}" install -y ros-humble-turtlebot4-navigation ros-humble-nav2-simple-commander \
  ros-humble-cv-bridge python3-pip python3-venv
python3 -m venv --system-site-packages .venv
.venv/bin/pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements.txt
source scripts/env.sh
mkdir -p weights
cd weights
../.venv/bin/python -c 'from ultralytics import YOLO; YOLO("yolov8n.pt")'
