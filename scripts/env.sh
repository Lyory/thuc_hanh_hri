#!/usr/bin/env bash
WEEK7_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
[[ -f /.dockerenv && -f /opt/ros/humble/setup.bash ]] || { echo 'Chạy qua scripts/docker.sh trong Docker Humble.' >&2; return 1; }
source /opt/ros/humble/setup.bash
source /opt/week7-venv/bin/activate
[[ ! -f "$WEEK7_ROOT/install_humble/local_setup.bash" ]] || source "$WEEK7_ROOT/install_humble/local_setup.bash"
export ROS_DOMAIN_ID=77
export PYTHONPATH="$WEEK7_ROOT/scripts:${PYTHONPATH:-}"

# Keep generated logs and caches on the workspace filesystem, outside Docker's
# writable layer (which normally lives on the host root partition).
export ROS_LOG_DIR="$WEEK7_ROOT/.docker-runtime/ros-logs"
export ROS_HOME="$WEEK7_ROOT/.docker-runtime/ros"
export IGN_HOMEDIR="$WEEK7_ROOT/.docker-runtime/gazebo"
export XDG_CACHE_HOME="$WEEK7_ROOT/.docker-runtime/cache"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$ROS_LOG_DIR" "$ROS_HOME" "$IGN_HOMEDIR" "$XDG_CACHE_HOME"

# Avoid large core dumps if a simulator/GUI process crashes.
ulimit -c 0
