#!/usr/bin/env bash
# Source this file on Ubuntu 22.04 / ROS 2 Humble or in the Humble container.
WEEK6_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo 'Cần Ubuntu 22.04 + ROS 2 Humble để chạy trực tiếp bài tuần 6.' >&2
  return 1
fi
source /opt/ros/humble/setup.bash
if [[ -n "${TURTLEBOT4_SETUP:-}" ]]; then
  if [[ ! -f "$TURTLEBOT4_SETUP" ]]; then
    echo "Không tìm thấy môi trường simulator: $TURTLEBOT4_SETUP" >&2
    return 1
  fi
  source "$TURTLEBOT4_SETUP"
elif [[ -f "$WEEK6_ROOT/../week4/install/local_setup.bash" ]]; then
  source "$WEEK6_ROOT/../week4/install/local_setup.bash"
fi
if [[ -f /.dockerenv && -f /opt/week6-venv/bin/activate ]]; then
  source /opt/week6-venv/bin/activate
elif [[ -f "$WEEK6_ROOT/.venv/bin/activate" ]]; then
  source "$WEEK6_ROOT/.venv/bin/activate"
fi
if [[ -f "$WEEK6_ROOT/install_humble/local_setup.bash" ]]; then
  source "$WEEK6_ROOT/install_humble/local_setup.bash"
fi
if [[ -f /.dockerenv && -z "${XAUTHORITY:-}" && -r /tmp/tb4.Xauthority ]]; then
  export XAUTHORITY=/tmp/tb4.Xauthority
fi
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
