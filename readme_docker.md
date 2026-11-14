# Tuần 8: Biểu cảm khuôn mặt điều khiển TurtleBot

**Chạy trực tiếp trên Ubuntu 22.04 + ROS 2 Humble:** xem
[readme.md](readme.md).

Chạy trong **Docker Ubuntu 22.04 + ROS 2 Humble**. Một lệnh mở:

- **Gazebo 3D:** TurtleBot3 Burger trong phòng đơn giản 4 × 4 m.
- **Webcam:** khung mặt, biểu cảm và vận tốc điều khiển robot trong Gazebo.

## 1. Chuẩn bị

Máy Linux cần Docker, webcam và desktop X11/XWayland. User hiện tại cần có
quyền chạy Docker. Không cần tự khởi động mô phỏng ở terminal khác.

Nếu thiếu `xauth`:

```bash
sudo apt-get install -y xauth
```

## 2. Build và chạy

Mở terminal trong thư mục project:

Dừng phiên chạy cũ bằng **Ctrl+C** trước để giải phóng webcam, rồi chạy:

```bash
./scripts/docker.sh build
./scripts/docker.sh run
```

Build lần đầu cần mạng để tải dependency. Sau khi build xong, những lần sau
chỉ cần lệnh `run`. Khi cập nhật mã nguồn, chạy lại `build` một lần.

Demo Gazebo chạy trong mạng Docker riêng, không kết nối mạng ngoài; lệnh vận tốc
chỉ dùng trong mô phỏng. Webcam và hai cửa sổ vẫn hoạt động bình thường.

Đợi robot xuất hiện trong cửa sổ Gazebo, sau đó nhìn vào webcam. Khung xanh
bám theo mặt trên ảnh hiện tại. Giữ biểu cảm trong giây lát để nhận diện ổn định.
Dùng con lăn chuột trong Gazebo để phóng to hoặc thu nhỏ khung nhìn robot.

| Biểu cảm | Hành động |
|---|---|
| Happy — Vui vẻ | Đi cong trái |
| Sad — Buồn | Đi cong phải |
| Neutral — Bình thường | Dừng |
| Angry — Tức giận | Lùi nhẹ trong 1 giây |
| Surprise — Ngạc nhiên | Xoay tại chỗ khoảng một vòng |
| Fear — Sợ hãi | Tiến nhẹ trong 1 giây |

Muốn lặp lại hành động tiến/lùi/xoay, chuyển về Neutral rồi thể hiện lại
biểu cảm mong muốn. Khi mất mặt hoặc điểm biểu cảm thấp, robot dừng;
khung mặt vẫn hiển thị khi đã tìm được mặt nhưng chưa chắc chắn biểu cảm.

Nhấn **Q**, **Esc**, **Ctrl+C** hoặc đóng cửa sổ để thoát toàn bộ demo.

## 3. Nếu dùng webcam khác

Ví dụ webcam là `/dev/video2`:

```bash
CAMERA_DEVICE=/dev/video2 ./scripts/docker.sh run
```

Script đưa webcam được chọn vào `/dev/video0` bên trong container.
Hình webcam được lật ngang như gương. Nên để mặt đủ sáng và vừa trong ảnh;
YuNet phát hiện mặt riêng, DeepFace nhận diện biểu cảm trên phần mặt đã cắt.

## 4. Nếu dùng TurtleBot thật

Khởi động bringup của robot thật, tắt demo Gazebo, rồi chỉ chạy camera:

```bash
./scripts/docker.sh camera
```

Nếu robot dùng domain `10`:

```bash
ROS_DOMAIN_ID=10 ./scripts/docker.sh camera
```

Nếu driver nhận `TwistStamped`:

```bash
./scripts/docker.sh camera --ros-args -p stamped:=true
```

Máy và robot cần cùng mạng và `ROS_DOMAIN_ID`. Tắt teleop/navigation khác
đang xuất lệnh lên `/cmd_vel`.
