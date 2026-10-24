# Tài nguyên bên thứ ba

- `src/turtlebot4_simulator/`: source TurtleBot 4 Simulator cho ROS 2 Humble,
  giữ nguyên mã nguồn và LICENSE Apache 2.0 từ bản simulator đã dùng cho các bài
  thực hành. Upstream: https://github.com/turtlebot/turtlebot4_simulator/tree/humble.
  Thư mục `.github` phục vụ quản trị upstream không được đưa vào bản phân phối này.
- `src/turtlebot4_gesture_control/models/gesture_recognizer.task`: model MediaPipe
  chính thức, float16, version 1. Nguồn và checksum nằm trong `models/README.md`
  cùng thư mục.

Các package nền ROS 2, Create 3, Gazebo và mô tả robot được cài qua dependency
manager của Ubuntu/ROS theo `scripts/install_dependencies.sh`, không đóng gói
binary phụ thuộc máy trong repository.
