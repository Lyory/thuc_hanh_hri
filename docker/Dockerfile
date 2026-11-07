FROM ros:humble-ros-base-jammy
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN source /etc/os-release && test "$VERSION_ID" = 22.04 && test -f /opt/ros/humble/setup.bash
# The public ROS image already configures the signed ROS repository, which also
# supplies Fortress packages. No author-specific image or extra APT key is needed.
# Simulator sources are included in src/. Install their build/runtime dependencies,
# plus all ROS/Python/graphics/audio dependencies used by this project.
# Do not install ignition-fortress: that metapackage also pulls unused development
# libraries and Python bindings. Keep runtime engines and the GUI plugin headers.
# PyAV (a faster-whisper dependency) decodes audio; no ffmpeg CLI is used.
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates util-linux build-essential cmake python3-colcon-ros python3-colcon-bash \
    python3-venv python3-opencv python3-yaml python3-pyqt5 \
    libportaudio2 libgl1-mesa-dri libgl1-mesa-glx \
    libxkbcommon-x11-0 libxcb-xinerama0 fonts-dejavu-core \
    ignition-tools libignition-gazebo6 libignition-gazebo6-plugins \
    libignition-rendering6-ogre2 libignition-physics5-dartsim \
    libignition-gui6-dev qml-module-qtquick-extras \
    ros-humble-turtlebot4-description ros-humble-turtlebot4-msgs \
    ros-humble-turtlebot4-navigation ros-humble-turtlebot4-node ros-humble-turtlebot4-viz \
    ros-humble-irobot-create-ignition-bringup ros-humble-irobot-create-nodes \
    ros-humble-irobot-create-toolbox ros-humble-ign-ros2-control \
    ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-simple-commander \
    ros-humble-rviz2 ros-humble-joint-state-publisher \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/week7-venv
COPY requirements.txt /tmp/week7-requirements.txt
RUN /opt/week7-venv/bin/pip install --no-cache-dir -r /tmp/week7-requirements.txt
ENV OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 ROS_DOMAIN_ID=77
WORKDIR /root/hri/week7
CMD ["sleep", "infinity"]
