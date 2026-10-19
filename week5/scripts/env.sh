#!/usr/bin/env bash
# source scripts/env.sh trong từng terminal Ubuntu hoặc container.
WEEK5_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source /opt/ros/humble/setup.bash
if [[ ! -f "$WEEK5_ROOT/../week4/install/setup.bash" ]]; then
  echo 'Chưa build simulator. Chạy colcon build --symlink-install trong thư mục week4.' >&2
  return 1
fi
source "$WEEK5_ROOT/../week4/install/setup.bash"
# Docker exec shells may omit XAUTHORITY even when the desktop cookie is valid.
if [[ -z "${XAUTHORITY:-}" && -r /tmp/tb4.Xauthority ]]; then
  export XAUTHORITY=/tmp/tb4.Xauthority
fi
export IGN_GAZEBO_RESOURCE_PATH="$WEEK5_ROOT/models:${IGN_GAZEBO_RESOURCE_PATH:-}"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
