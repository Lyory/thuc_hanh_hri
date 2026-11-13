FROM ros:humble-ros-base-jammy

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive \
    TF_USE_LEGACY_KERAS=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    CUDA_VISIBLE_DEVICES=-1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-colcon-common-extensions python3-pytest \
    ros-humble-geometry-msgs \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    libxcb-xinerama0 libxkbcommon-x11-0 libx11-xcb1 xauth xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/week8
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir --timeout=120 pip==25.3
# Resume large downloads after transient timeouts and retain the build cache.
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install --timeout=120 --retries=5 --resume-retries=10 -r requirements.txt \
    && python3 -m pip check
# Include Emotion weights in the image; runtime needs no model download.
RUN python3 -c "from deepface import DeepFace; DeepFace.build_model(model_name='Emotion', task='facial_attribute')"

COPY package.xml setup.py setup.cfg ./
COPY resource/ resource/
COPY emotion_turtlebot/ emotion_turtlebot/
COPY tests/ tests/
COPY scripts/ scripts/
RUN source /opt/ros/humble/setup.bash \
    && colcon build --packages-select emotion_turtlebot \
    && source install/setup.bash \
    && python3 -m pytest -q tests

ENTRYPOINT ["/bin/bash", "/opt/week8/scripts/entrypoint.sh"]
CMD ["ros2", "run", "emotion_turtlebot", "emotion_control"]
