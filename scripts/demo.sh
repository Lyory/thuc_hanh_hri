#!/usr/bin/env bash
set -eo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
exec 9>.runtime/demo.lock
flock -n 9 || { echo 'Demo tuần 7 đang chạy. Dùng cửa sổ hiện có hoặc dừng demo cũ trước.' >&2; exit 1; }
exec ros2 launch "$@"
