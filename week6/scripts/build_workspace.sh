#!/usr/bin/env bash
set -eo pipefail
WEEK6_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$WEEK6_ROOT"
source scripts/env.sh
python -c 'import cv2, mediapipe, rclpy' || {
  echo 'Thiếu thư viện. Source scripts/env.sh rồi cài python -m pip install -r requirements.txt.' >&2
  exit 1
}
ros2 pkg prefix turtlebot4_ignition_bringup >/dev/null
ros2 pkg prefix irobot_create_ignition_bringup >/dev/null
python scripts/download_model.py
python -m colcon --log-base log_humble build \
  --build-base build_humble --install-base install_humble \
  --symlink-install --packages-select turtlebot4_gesture_control
if [[ -n "${LOCAL_UID:-}" && -n "${LOCAL_GID:-}" && $(id -u) == 0 ]]; then
  chown -R "$LOCAL_UID:$LOCAL_GID" build_humble install_humble log_humble
fi
