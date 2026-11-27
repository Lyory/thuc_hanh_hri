#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
# Colcon's sequential executor still allows CMake/Make to launch many jobs.
export CMAKE_BUILD_PARALLEL_LEVEL="${WEEK7_BUILD_JOBS:-2}"
[[ "$CMAKE_BUILD_PARALLEL_LEVEL" =~ ^[1-9][0-9]*$ ]] || { echo 'WEEK7_BUILD_JOBS phải là số nguyên dương.' >&2; exit 1; }
export MAKEFLAGS="-j$CMAKE_BUILD_PARALLEL_LEVEL"
# Image/library versions may change while the bind-mounted build tree survives.
# Reconfigure cached library paths before reusing existing object files.
python -m colcon --log-base log_humble build --build-base build_humble --install-base install_humble --symlink-install --executor sequential --cmake-clean-cache --cmake-args -DBUILD_TESTING=OFF
python scripts/segment_map.py
