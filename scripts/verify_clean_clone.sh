#!/usr/bin/env bash
# Host-side check: build a source-only copy without cached assets or outputs.
set -euo pipefail
PROJECT_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# Use the project filesystem, not /tmp on the host root partition.
mkdir -p "$PROJECT_ROOT/.docker-runtime"
CHECK_ROOT=$(mktemp -d "$PROJECT_ROOT/.docker-runtime/clean-clone.XXXXXX")
CHECK_IMAGE="hri-week7-clean-check:run-$$"
cleanup() {
  if [[ "${WEEK7_KEEP_CHECK:-0}" == 1 ]]; then
    echo "Giữ lại $CHECK_ROOT và $CHECK_IMAGE (WEEK7_KEEP_CHECK=1)."
  else
    docker image rm "$CHECK_IMAGE" >/dev/null 2>&1 || true
    rm -rf -- "$CHECK_ROOT"
  fi
}
trap cleanup EXIT
echo "Bản sao source độc lập: $CHECK_ROOT"
tar -C "$PROJECT_ROOT" \
  --exclude='./build_humble' --exclude='./install_humble' --exclude='./log_humble' \
  --exclude='./models' --exclude='./evidence' --exclude='./.docker-runtime' \
  --exclude='.git' --exclude='__pycache__' \
  --exclude='./config/regions.json' --exclude='./config/region_labels.npy' \
  --exclude='./config/segmented_map.png' -cf - . | tar -C "$CHECK_ROOT" -xf -
docker build -f "$CHECK_ROOT/docker/Dockerfile" -t "$CHECK_IMAGE" "$CHECK_ROOT"
docker run --rm \
  --env "LOCAL_UID=$(id -u)" --env "LOCAL_GID=$(id -g)" \
  --mount "type=bind,source=$CHECK_ROOT,target=/root/hri/week7" \
  "$CHECK_IMAGE" bash -c \
  'trap "chown -R \"$LOCAL_UID:$LOCAL_GID\" /root/hri/week7" EXIT; bash scripts/build.sh && source scripts/env.sh && python scripts/check_core.py && python scripts/check_route_planning.py && python scripts/check_install.py'
echo "PASS: build từ source riêng, không dùng install/model/evidence hoặc workspace tuần khác."
echo "Mặc định tự dọn bản sao và tag image kiểm tra; đặt WEEK7_KEEP_CHECK=1 để giữ khi debug."
