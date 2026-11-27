#!/usr/bin/env bash
# Source this file on Ubuntu 22.04 / ROS 2 Humble: source scripts/env.sh
WEEK7_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ -f /opt/ros/humble/setup.bash ]] || { echo 'Cần Ubuntu 22.04 + ROS 2 Humble (/opt/ros/humble).' >&2; return 1; }
[[ -f "$WEEK7_ROOT/.venv/bin/activate" ]] || { echo 'Chưa có .venv; làm theo bước cài đặt trong README.md.' >&2; return 1; }
source /opt/ros/humble/setup.bash
source "$WEEK7_ROOT/.venv/bin/activate"
[[ ! -f "$WEEK7_ROOT/install_humble/local_setup.bash" ]] || source "$WEEK7_ROOT/install_humble/local_setup.bash"
export ROS_DOMAIN_ID=77
export PYTHONPATH="$WEEK7_ROOT/scripts:${PYTHONPATH:-}"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2

# Keep generated logs and caches inside the project.
export ROS_LOG_DIR="$WEEK7_ROOT/.runtime/ros-logs"
export ROS_HOME="$WEEK7_ROOT/.runtime/ros"
export IGN_HOMEDIR="$WEEK7_ROOT/.runtime/gazebo"
export XDG_CACHE_HOME="$WEEK7_ROOT/.runtime/cache"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$ROS_LOG_DIR" "$ROS_HOME" "$IGN_HOMEDIR" "$XDG_CACHE_HOME"

# Avoid large core dumps if a simulator/GUI process crashes.
ulimit -c 0
