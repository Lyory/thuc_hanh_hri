#!/usr/bin/env bash
set -eo pipefail
WEEK7_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
WEEK7_IMAGE=hri-week7:humble
WEEK7_CONTAINER=hri-week7
WEEK7_RUNTIME="$WEEK7_ROOT/.docker-runtime"

die() { echo "$*" >&2; exit 1; }

managed_container() {
  [[ $(docker inspect --format '{{index .Config.Labels "hri.week7.workspace"}}' "$WEEK7_CONTAINER") == "$WEEK7_ROOT" ]] \
    || die "Container $WEEK7_CONTAINER không thuộc workspace này. Đổi tên container đó trước."
}

prepare_display() {
  mkdir -p "$WEEK7_RUNTIME"
  chmod 700 "$WEEK7_RUNTIME"
  if [[ -z "${DISPLAY:-}" ]]; then
    return
  fi
  command -v xauth >/dev/null || die 'Host cần xauth để mở cửa sổ Gazebo/RViz.'
  local cookie
  cookie=$(xauth nlist "$DISPLAY" 2>/dev/null)
  [[ -n "$cookie" ]] || die 'Không đọc được Xauthority cho DISPLAY hiện tại; chạy từ terminal desktop của bạn.'
  touch "$WEEK7_RUNTIME/xauthority"
  chmod 600 "$WEEK7_RUNTIME/xauthority"
  printf '%s\n' "$cookie" | sed 's/^..../ffff/' | xauth -f "$WEEK7_RUNTIME/xauthority" nmerge -
}

start_container() {
  docker image inspect "$WEEK7_IMAGE" >/dev/null 2>&1 || die 'Chạy bash scripts/docker.sh build trước.'
  prepare_display
  # ALSA names inside Docker often omit DMIC/headset descriptions.
  if [[ -r /proc/asound/pcm ]]; then
    local audio_metadata
    audio_metadata=$(mktemp "$WEEK7_RUNTIME/alsa-pcm.XXXXXX")
    cat /proc/asound/pcm > "$audio_metadata"
    chmod 600 "$audio_metadata"
    mv -f "$audio_metadata" "$WEEK7_RUNTIME/alsa-pcm"
  fi
  if docker container inspect "$WEEK7_CONTAINER" >/dev/null 2>&1; then
    managed_container
    if [[ $(docker inspect --format '{{.Image}}' "$WEEK7_CONTAINER") == $(docker image inspect --format '{{.Id}}' "$WEEK7_IMAGE") ]]; then
      docker start "$WEEK7_CONTAINER" >/dev/null
      return
    fi
    # Runtime state lives in the mounted workspace; use the rebuilt image.
    docker rm -f "$WEEK7_CONTAINER" >/dev/null
  fi
  local args=(run -d --name "$WEEK7_CONTAINER" --network host
    --log-driver local --log-opt max-size=10m --log-opt max-file=2
    --label "hri.week7.workspace=$WEEK7_ROOT"
    --env "DISPLAY=${DISPLAY:-}" --env XAUTHORITY=/run/week7-display/xauthority
    --env "LOCAL_UID=$(id -u)" --env "LOCAL_GID=$(id -g)"
    --mount "type=bind,source=$WEEK7_ROOT,target=/root/hri/week7"
    --mount "type=bind,source=$WEEK7_RUNTIME,target=/run/week7-display,readonly")
  [[ ! -d /tmp/.X11-unix ]] || args+=(--mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly)
  [[ ! -d /dev/dri ]] || args+=(--device /dev/dri)
  [[ ! -d /dev/snd ]] || args+=(--device /dev/snd)
  docker "${args[@]}" "$WEEK7_IMAGE" >/dev/null
}

run_inside() {
  start_container
  local interactive=(-i)
  [[ ! -t 0 || ! -t 1 ]] || interactive=(-it)
  docker exec "${interactive[@]}" "$WEEK7_CONTAINER" bash -c 'source /root/hri/week7/scripts/env.sh && exec "$@"' bash "$@"
}

action=${1:-help}
if [[ $# -gt 0 ]]; then shift; fi
case "$action" in
  build)
    docker build -f "$WEEK7_ROOT/docker/Dockerfile" -t "$WEEK7_IMAGE" "$WEEK7_ROOT"
    run_inside bash /root/hri/week7/scripts/build.sh
    ;;
  start) start_container ;;
  rebuild) run_inside bash /root/hri/week7/scripts/build.sh ;;
  shell) run_inside bash --norc ;;
  demo) run_inside bash /root/hri/week7/scripts/demo.sh /root/hri/week7/launch/week7.launch.py "$@" ;;
  simulation) run_inside bash /root/hri/week7/scripts/demo.sh /root/hri/week7/launch/localization.launch.py "$@" ;;
  panel) run_inside python /root/hri/week7/scripts/voice_panel.py "$@" ;;
  recognition) run_inside python /root/hri/week7/scripts/speech_recognition.py "$@" ;;
  segment) run_inside python /root/hri/week7/scripts/segment_map.py "$@" ;;
  navigation) run_inside python /root/hri/week7/scripts/voice_navigation.py "$@" ;;
  initialize) run_inside python /root/hri/week7/scripts/initialize.py "$@" ;;
  check) run_inside bash -c 'python scripts/check_core.py && python scripts/check_route_planning.py && python scripts/check_install.py' ;;
  exec) [[ $# -gt 0 ]] || die 'Thiếu lệnh sau exec'; run_inside "$@" ;;
  stop)
    if docker container inspect "$WEEK7_CONTAINER" >/dev/null 2>&1; then
      managed_container
      docker stop --time 15 "$WEEK7_CONTAINER" >/dev/null
    fi
    ;;
  recreate)
    if docker container inspect "$WEEK7_CONTAINER" >/dev/null 2>&1; then
      managed_container
      docker rm -f "$WEEK7_CONTAINER" >/dev/null
    fi
    start_container
    ;;
  *)
    echo 'Dùng trên host: bash scripts/docker.sh {build|rebuild|demo|simulation|panel|recognition|navigation|initialize|segment|check|shell|exec|start|stop|recreate}'
    echo 'Ví dụ: bash scripts/docker.sh recognition --model small'
    ;;
esac
