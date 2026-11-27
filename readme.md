# Chạy trực tiếp trên Ubuntu 22.04 và ROS 2 Humble

## 1. Clone project

Mở terminal Bash và chạy:

```bash
git clone --branch week8 --single-branch https://github.com/Lyory/thuc_hanh_hri.git thuc_hanh_hri_week8
cd thuc_hanh_hri_week8
```

## 2. Cài các gói cần thiết

```bash
sudo apt update
sudo apt install -y \
  python3-venv python3-pip python3-colcon-common-extensions \
  ros-humble-ros2launch ros-humble-geometry-msgs \
  ros-humble-turtlebot3-gazebo ros-humble-robot-state-publisher \
  libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
  libxcb-xinerama0 libxkbcommon-x11-0 libx11-xcb1
```

Các gói TurtleBot3 sẽ cài Gazebo và plugin ROS cần cho mô phỏng.

## 3. Tạo môi trường Python và cài DeepFace

Vẫn trong thư mục project:

```bash
source /opt/ros/humble/setup.bash
/usr/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
touch .venv/COLCON_IGNORE

python -m pip install --timeout=120 pip==25.3
python -m pip install --timeout=120 --retries=5 --resume-retries=10 -r requirements.txt
```

Môi trường `.venv` dùng được các thư viện ROS đã cài trên máy qua
`--system-site-packages`. Các phiên bản DeepFace, TensorFlow, NumPy và OpenCV
được cố định trong `requirements.txt`. Lần đầu cần mạng và có thể tải vài trăm MB.

Tải trước mô hình biểu cảm để lúc chạy webcam không phải chờ tải:

```bash
python -c "from deepface import DeepFace; DeepFace.build_model(model_name='Emotion', task='facial_attribute')"
```

Trọng số được lưu trong `~/.deepface/weights`. Mô hình phát hiện mặt YuNet đã có
trong thư mục `models/` của project.

## 4. Build gói ROS

Giữ môi trường `.venv` đang kích hoạt và chạy:

```bash
python -m colcon build --symlink-install --packages-select emotion_turtlebot
source install/setup.bash
```

Dùng `python -m colcon` để executable được tạo bằng Python của `.venv`, nơi
đã cài DeepFace. Sau khi sửa mã hoặc cập nhật project, chạy lại bước build.

## 5. Chạy Gazebo và webcam

Đóng các ứng dụng khác đang dùng webcam và dừng phiên demo cũ, rồi chạy:

```bash
export ROS_DOMAIN_ID=88
export ROS_LOCALHOST_ONLY=1
ros2 launch emotion_turtlebot demo.launch.py
```

Domain `88` và chế độ localhost dùng cho demo trên cùng máy. Đợi TurtleBot xuất
hiện trong phòng Gazebo, sau đó nhìn vào webcam và giữ biểu cảm trong giây lát.
Dùng con lăn chuột trong Gazebo để phóng to hoặc thu nhỏ khung nhìn robot.

| Biểu cảm | Hành động |
|---|---|
| Happy — Vui vẻ | Đi cong trái |
| Sad — Buồn | Đi cong phải |
| Neutral — Bình thường | Dừng |
| Angry — Tức giận | Lùi nhẹ trong 1 giây |
| Surprise — Ngạc nhiên | Xoay tại chỗ khoảng một vòng |
| Fear — Sợ hãi | Tiến nhẹ trong 1 giây |

Muốn lặp lại hành động tiến/lùi/xoay, chuyển về Neutral rồi thể hiện lại biểu cảm.
Khi mất mặt hoặc điểm biểu cảm thấp, robot dừng. Giữ mặt đủ sáng và vừa khung hình.

Nhấn **Q**, **Esc**, **Ctrl+C** hoặc đóng cửa sổ để thoát demo.

### Những lần chạy sau

Mở terminal trong thư mục `thuc_hanh_hri_week8`:

```bash
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source install/setup.bash
export ROS_DOMAIN_ID=88
export ROS_LOCALHOST_ONLY=1
ros2 launch emotion_turtlebot demo.launch.py
```

### Nếu webcam là `/dev/video2`

Sau khi kích hoạt môi trường như trên, chạy:

```bash
ros2 launch emotion_turtlebot demo.launch.py camera_index:=2
```

### Nếu Gazebo bị đen màn hình hoặc lỗi OpenGL

Chạy bằng bộ dựng hình phần mềm:

```bash
LIBGL_ALWAYS_SOFTWARE=1 ros2 launch emotion_turtlebot demo.launch.py
```
