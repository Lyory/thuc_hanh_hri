#!/usr/bin/env bash
set -eo pipefail
WEEK6_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$WEEK6_ROOT"
source /etc/os-release
if [[ "$VERSION_ID" != 22.04 || ! -f /opt/ros/humble/setup.bash ]]; then
  echo 'Cần Ubuntu 22.04 với ROS 2 Humble đã cài trước.' >&2
  exit 1
fi
source /opt/ros/humble/setup.bash
sudo apt-get update
sudo apt-get install -y build-essential cmake python3-pip python3-venv \
  python3-colcon-common-extensions python3-rosdep libgl1 libglib2.0-0 curl gnupg
if ! apt-cache show ignition-fortress >/dev/null 2>&1; then
  sudo curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
    --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
  printf 'deb [arch=%s signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable jammy main\n' \
    "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null
  sudo apt-get update
fi
sudo apt-get install -y ignition-fortress
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update --rosdistro humble
rosdep install --from-paths src --ignore-src -y --rosdistro humble
if [[ ! -f .venv/bin/activate ]]; then
  python3 -m venv --system-site-packages .venv
fi
source .venv/bin/activate
python -m pip install -r requirements.txt
