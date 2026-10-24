# Thực hành HRI — Tuần 6

Nhận diện cử chỉ tay bằng webcam, OpenCV và MediaPipe để điều khiển TurtleBot 4
trong Gazebo trên **Ubuntu 22.04 + ROS 2 Humble**.

Bắt đầu tại [hướng dẫn cài đặt và chạy trực tiếp tuần 6](week6/README.md).

| Thư mục | Nội dung |
| --- | --- |
| `week4/` | Source simulator, cấu hình và bản đồ từ bài trước |
| `week5/` | Bài navigation và nhận diện đối tượng đã có |
| `week6/` | Nhận diện cử chỉ, xác nhận hành vi và dừng bảo vệ |

Tuần 6 gồm `gesture_recognition_node`, `robot_behavior_node`, model MediaPipe,
sân trống và các launch đặt tên theo chức năng. Giữ cử chỉ ổn định để chọn,
giơ ngón cái để xác nhận, xòe tay để dừng và nắm tay để hủy. Không có file test
được thêm trong tuần 6.

Nhánh này chỉ bổ sung mã nguồn, tài nguyên và README chạy trực tiếp của tuần 6.
Các file dành riêng cho Docker, môi trường Python, kết quả build và log tuần 6
được giữ ở máy, không đưa lên repository.
