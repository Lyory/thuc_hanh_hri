# Thực hành HRI — Tuần 5

TurtleBot 4 trên **Ubuntu 22.04 + ROS 2 Humble + Ignition Gazebo Fortress**:

- Tái sử dụng bản đồ tuần 4 để localization bằng AMCL.
- ROS 2 node Python tự gửi ít nhất ba goal tuần tự qua Nav2 Simple Commander.
- Nhận diện người, ghế và xe bằng camera RGB, cv_bridge và YOLOv8n.

**Bắt đầu tại [hướng dẫn tuần 5](week5/README.md)**: cài dependency, build simulator và chạy hai launch riêng cho localization và navigation/YOLO.

| Thư mục | Nội dung |
|---|---|
| `week4/` | Source simulator, maze và map nền từ bài trước |
| `week5/` | Launch, node navigation/YOLO, cấu hình goal và mô hình vật thể |

Nhánh `week5` chỉ chứa source và tài nguyên cần chạy. Các thư mục `build`, `install`, log, `.venv`, weights tải về, video và kết quả chạy được tạo tại máy và không đưa lên Git.
