#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
image="hri-week8:humble"
action="${1:-run}"
if (($#)); then shift; fi

case "$action" in
    build)
        docker build -t "$image" "$project_root"
        ;;
    test)
        docker run --rm --init "$image" xvfb-run -a bash -c \
            'python3 -m pytest -q tests && python3 scripts/verify_container.py'
        ;;
    exec)
        docker run --rm --init --network host --ipc host \
            -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" "$image" "$@"
        ;;
    run)
        camera_device="${CAMERA_DEVICE:-/dev/video0}"
        : "${DISPLAY:?Cần desktop X11 hoặc XWayland và biến DISPLAY để mở webcam.}"
        if [[ ! -c "$camera_device" ]]; then
            echo "Không tìm thấy webcam: $camera_device" >&2
            exit 1
        fi
        command -v xauth >/dev/null || { echo 'Cần cài xauth trên host.' >&2; exit 1; }
        xauth_file="$(mktemp /tmp/week8-xauth.XXXXXX)"
        trap 'rm -f "$xauth_file"' EXIT
        xauth nlist "$DISPLAY" | sed 's/^..../ffff/' | xauth -f "$xauth_file" nmerge -
        if [[ ! -s "$xauth_file" ]]; then
            echo 'Không lấy được Xauthority cho DISPLAY; chạy từ terminal trong desktop.' >&2
            exit 1
        fi
        docker run --rm --init --network host --ipc host \
            --device "$camera_device:$camera_device" \
            -e DISPLAY -e QT_X11_NO_MITSHM=1 \
            -e XAUTHORITY=/tmp/week8.xauth \
            -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
            --mount type=bind,src=/tmp/.X11-unix,dst=/tmp/.X11-unix,readonly \
            --mount "type=bind,src=$xauth_file,dst=/tmp/week8.xauth,readonly" \
            "$image" ros2 run emotion_turtlebot emotion_control "$@"
        ;;
    *)
        echo "Cách dùng: $0 {build|test|run [ROS args]|exec command [args]}" >&2
        exit 2
        ;;
esac
