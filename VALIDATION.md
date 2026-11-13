# Kiểm chứng Docker — 13/11/2026

Đã build và chạy image `hri-week8:humble` bằng Docker Engine.
Không dùng ROS/Python trên host cho các kiểm tra dưới đây.

| Kiểm tra | Kết quả |
|---|---|
| `/etc/os-release` trong container | Ubuntu 22.04.5 LTS, `VERSION_ID=22.04` |
| `ROS_DISTRO` | `humble` |
| `python3 --version` | Python 3.10.12 |
| `pip check` | Không có dependency lỗi |
| `colcon build` | Gói `emotion_turtlebot` build thành công |
| `python3 -m pytest -q tests` | 23/23 tests đạt |
| Mô hình Emotion thật | Nạp trọng số, chạy suy luận, nhận đủ 7 điểm đầu ra hữu hạn |
| Ảnh đen không có mặt | Không sinh nhãn điều khiển |
| OpenCV GUI trên Xvfb | Mở được cửa sổ và xử lý sự kiện |
| Node và subscriber ROS thật, camera/nhãn giả | Nhận lệnh Happy và vận tốc 0 khi camera lỗi, với cả Twist/TwistStamped |
| Executable `ros2 run` khi tắt mạng | Nạp mô hình offline, khởi tạo Humble, báo rõ webcam không tồn tại |
| Luồng nhận diện thật trên ảnh mẫu DeepFace | Phát hiện mặt và trả nhãn `happy`, điểm làm tròn 100.0% |

Ảnh mẫu chỉ được tải vào bộ nhớ khi kiểm tra, từ
[DeepFace v0.0.93 — img1.jpg](https://github.com/serengil/deepface/blob/v0.0.93/tests/dataset/img1.jpg).
Kết quả của một ảnh mẫu không phải phép đo độ chính xác nhận diện của mô hình.

Tái chạy kiểm tra chính:

```bash
./scripts/docker.sh build
./scripts/docker.sh test
./scripts/docker.sh exec bash -c 'cat /etc/os-release; echo "$ROS_DISTRO"; python3 --version'
```

Phiên làm việc không có thiết bị `/dev/video*`, chưa kết nối TurtleBot.
Vì vậy chưa xác minh webcam vật lý, quyền hiển thị desktop X11 của người dùng,
giao tiếp DDS tới robot qua LAN hoặc quỹ đạo thực tế. Phần GUI được kiểm tra
bằng Xvfb; kiểm tra truyền lệnh ROS dùng hai node trong cùng tiến trình,
domain 187 và topic riêng `/week8_test/cmd_vel`.
