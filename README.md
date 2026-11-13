# Tuần 8: Nhận diện biểu cảm và điều khiển TurtleBot

Chương trình chạy trong **Docker Ubuntu 22.04 + ROS 2 Humble**,
nhận diện biểu cảm qua webcam và điều khiển TurtleBot qua `/cmd_vel`.

## 1. Chuẩn bị

- Máy Linux đã cài Docker và user hiện tại có quyền chạy Docker.
- Webcam kết nối với máy, mặc định là `/dev/video0`.
- Mở terminal từ desktop có X11 hoặc XWayland để hiển thị cửa sổ camera.
- Khởi động TurtleBot hoặc mô phỏng của lớp, cùng mạng và `ROS_DOMAIN_ID`
  với chương trình. Mặc định dùng domain `0`.
- Tắt chương trình teleop/navigation khác đang điều khiển robot.

Cài `xauth` trên máy Ubuntu nếu chưa có:

```bash
sudo apt-get install -y xauth
```

Không cần cài ROS hoặc DeepFace trên máy host.

## 2. Build lần đầu

Mở terminal tại thư mục project, chạy:

```bash
./scripts/docker.sh build
```

Lần đầu cần mạng để tải dependency và mô hình nên có thể mất nhiều thời gian.
Chỉ cần build lại khi sửa mã nguồn. Nếu image đã được build sẵn, chuyển thẳng
sang bước chạy.

## 3. Chạy chương trình

Trong thư mục project:

```bash
./scripts/docker.sh run
```

Khi cửa sổ webcam hiện lên, hướng mặt vào camera và giữ biểu cảm trong giây lát
để chương trình nhận diện ổn định.

| Biểu cảm | Hành động |
|---|---|
| Happy — Vui vẻ | Đi cong sang trái |
| Sad — Buồn | Đi cong sang phải |
| Neutral — Bình thường | Dừng |
| Angry — Tức giận | Lùi nhẹ trong 1 giây |
| Surprise — Ngạc nhiên | Xoay tại chỗ khoảng một vòng |
| Fear — Sợ hãi | Tiến nhẹ trong 1 giây |

Tiến, lùi và xoay chỉ thực hiện một lần khi đổi biểu cảm. Muốn lặp lại,
chuyển về Neutral rồi thể hiện lại biểu cảm mong muốn. Giữ mặt trong khung hình;
robot sẽ dừng khi mất mặt hoặc kết quả nhận diện không còn hợp lệ.

Nhấn **Q**, **Esc** trong cửa sổ camera hoặc **Ctrl+C** ở terminal để dừng và thoát.

## 4. Các trường hợp cần đổi cấu hình

Nếu dùng webcam `/dev/video2`:

```bash
CAMERA_DEVICE=/dev/video2 ./scripts/docker.sh run --ros-args -p camera_index:=2
```

Nếu robot dùng domain `10`:

```bash
ROS_DOMAIN_ID=10 ./scripts/docker.sh run
```

Nếu driver robot nhận `TwistStamped` thay cho `Twist`:

```bash
./scripts/docker.sh run --ros-args -p stamped:=true
```
