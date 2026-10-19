#!/usr/bin/env bash
# Chạy trong container hri; dùng màn hình riêng :99, không cần thao tác chuột.
set -eo pipefail
cd -- "$(dirname -- "$0")/.."
source scripts/env.sh
mkdir -p evidence
if DISPLAY=:99 xdpyinfo >/dev/null 2>&1; then
  echo 'Màn hình :99 đang được dùng. Dừng lượt demo cũ trước khi chạy lại.' >&2
  exit 1
fi
demo_pids=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${demo_pids[@]}"; do kill -INT -- "-$pid" 2>/dev/null || true; done
  # RViz Qt có thể không thoát chỉ bằng SIGINT; để FFmpeg chốt MP4 trước.
  sleep 5
  for pid in "${demo_pids[@]}"; do kill -TERM -- "-$pid" 2>/dev/null || true; done
  for pid in "${demo_pids[@]}"; do wait "$pid" 2>/dev/null || true; done
  kill "$xvfb_pid" 2>/dev/null || true
  wait "$xvfb_pid" 2>/dev/null || true
}
Xvfb :99 -screen 0 1800x1000x24 -nolisten tcp > evidence/xvfb.log 2>&1 &
xvfb_pid=$!
trap cleanup EXIT
trap 'exit 130' INT TERM
sleep 2
DISPLAY=:99 xdpyinfo >/dev/null
setsid ros2 launch "$PWD/launch/localization.launch.py" headless:=true rviz_display:=:99 \
  > evidence/simulation.log 2>&1 &
demo_pids+=("$!")
DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 __GLX_VENDOR_LIBRARY_NAME=mesa \
  setsid .venv/bin/python scripts/yolo_detector.py --show > evidence/yolo.log 2>&1 &
demo_pids+=("$!")
setsid .venv/bin/python scripts/monitor_run.py > evidence/monitor.log 2>&1 &
demo_pids+=("$!")
setsid bash scripts/record_demo.sh > evidence/recording.log 2>&1 &
demo_pids+=("$!")
# Bộ đợi trong node kiểm tra AMCL, clock và action server, timeout 180s.
python3 scripts/navigate_goals.py --initialize > evidence/navigation.log 2>&1
echo 'Hoàn thành. Xem evidence/week5_demo.mp4 và evidence/navigation.csv.'
