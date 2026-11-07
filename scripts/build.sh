#!/usr/bin/env bash
set -eo pipefail
cd /root/hri/week7
source scripts/env.sh
# Colcon's sequential executor still allows CMake/Make to launch many jobs.
export CMAKE_BUILD_PARALLEL_LEVEL="${WEEK7_BUILD_JOBS:-2}"
[[ "$CMAKE_BUILD_PARALLEL_LEVEL" =~ ^[1-9][0-9]*$ ]] || { echo 'WEEK7_BUILD_JOBS phải là số nguyên dương.' >&2; exit 1; }
export MAKEFLAGS="-j$CMAKE_BUILD_PARALLEL_LEVEL"
# Image/library versions may change while the bind-mounted build tree survives.
# Reconfigure cached library paths before reusing existing object files.
python -m colcon --log-base log_humble build --build-base build_humble --install-base install_humble --symlink-install --executor sequential --cmake-clean-cache --cmake-args -DBUILD_TESTING=OFF
python scripts/segment_map.py
if [[ -n "${LOCAL_UID:-}" && -n "${LOCAL_GID:-}" ]]; then
  chown -R "$LOCAL_UID:$LOCAL_GID" build_humble install_humble log_humble \
    config/regions.json config/region_labels.npy config/segmented_map.png
fi
