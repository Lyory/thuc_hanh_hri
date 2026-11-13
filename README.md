# Tuần 8: Nhận diện biểu cảm và điều khiển TurtleBot

Gói ROS 2 Python dùng webcam, OpenCV và DeepFace để nhận diện biểu cảm,
hiển thị hình ảnh cùng kết quả và xuất vận tốc lên `/cmd_vel` ở 20 Hz.
Môi trường chạy: **Docker Ubuntu 22.04, ROS 2 Humble, Python 3.10**.
Host chỉ cần Docker, desktop X11/XWayland và webcam; không dùng ROS/Python trên host
để build hoặc chạy project. Image dùng CPU, không yêu cầu CUDA/GPU.

## 1. Các hành động

| Biểu cảm | Hành động | `linear.x` (m/s) | `angular.z` (rad/s) | Thời gian |
|---|---|---:|---:|---|
| Happy | Đi cong trái | 0.10 | +0.40 | Khi còn biểu cảm |
| Sad | Đi cong phải | 0.10 | −0.40 | Khi còn biểu cảm |
| Neutral | Dừng | 0 | 0 | Ngay khi nhận diện hợp lệ |
| Angry | Lùi nhẹ | −0.08 | 0 | 1 giây, khoảng 8 cm |
| Surprise | Xoay trái một vòng | 0 | +0.60 | `2π / 0.60 ≈ 10.47` giây |
| Fear | Tiến nhẹ | +0.08 | 0 | 1 giây, khoảng 8 cm |

Theo hệ trục robot ROS, `angular.z > 0` rẽ trái. Với Happy/Sad,
bán kính cung lý tưởng là `R = |v/ω| = 0.25 m`.
Quãng đường và góc xoay là ước lượng từ vận tốc × thời gian, không có phản hồi
odometry. Trượt bánh, gia tốc và ngắt nhận diện có thể khiến robot xoay chưa đủ
360°. Nếu bài chấm đòi góc đo chính xác trên robot, cần bổ sung phản hồi `/odom`.

Chỉ di chuyển sau ba kết quả liên tiếp cùng biểu cảm, điểm DeepFace ≥ 50%.
Đây là điểm dự đoán của mô hình, không phải xác suất cảm xúc thực của người.
Kết quả mất mặt, `disgust` (nhãn thứ bảy của DeepFace), điểm thấp hoặc kết quả
cũ hơn 2.5 giây đều đưa vận tốc về 0. Trong lúc xác nhận biểu cảm khác,
robot cũng dừng. Khi không có kết quả mới, watchdog dừng sau tối đa 2.5 giây
tính từ thời điểm chụp ảnh hợp lệ gần nhất.

Tiến/lùi/xoay chạy một lần cho mỗi lần đổi biểu cảm ổn định. Giữ nguyên biểu cảm
sau khi hết thời gian sẽ không lặp hành động. Chuyển về Neutral rồi biểu cảm
mong muốn để kích hoạt lại. Mất mặt không tự kích hoạt lại hành động.
Nếu nhiều người xuất hiện, chương trình chọn khuôn mặt lớn nhất trong từng ảnh;
không theo dõi danh tính giữa các ảnh.

## 2. Build Docker

Trên máy Linux có Docker Engine đang hoạt động, cài thêm `xauth` trên host
(ví dụ Ubuntu: `sudo apt-get install xauth`). Docker phải truy cập được bằng
user hiện tại; có thể dùng `sudo ./scripts/docker.sh ...` nếu máy yêu cầu,
nhưng khi chạy GUI nên dùng user desktop có quyền Docker và Xauthority.
Không cần cài ROS, DeepFace hay tạo venv trên host.

Clone đúng nhánh sau khi project đã được đẩy lên GitHub, hoặc mở thư mục
mã nguồn hiện có:

```bash
git clone --branch week8 https://github.com/Lyory/thuc_hanh_hri.git
cd thuc_hanh_hri
./scripts/docker.sh build
./scripts/docker.sh test
```

`Dockerfile` dùng image công khai `ros:humble-ros-base-jammy`, không cần các
image bài tuần trước trên máy tác giả. Build cài dependency, tải trọng số Emotion
vào image, build gói bằng ROS Humble, chạy unit test và kiểm chứng runtime.
Lần đầu cần mạng và vài GB dung lượng cho TensorFlow; chạy nhận diện sau khi
build không cần tải mô hình nữa. Mã nguồn được COPY vào image: sau khi sửa mã,
chạy lại lệnh build để cập nhật.

Các phiên bản chính được cố định trong `requirements.txt`: DeepFace 0.0.93, RetinaFace 0.0.17,
TensorFlow 2.16.2, tf-keras 2.16.0, NumPy 1.26.4 và OpenCV 4.10.0.84.
Không dùng `opencv-python-headless` vì bài thực hành cần cửa sổ camera.
RetinaFace được cố định để tránh phiên bản mới kéo thêm OpenCV headless.
Build dùng pip 25.3, cache và tải tiếp sau gián đoạn để xử lý các gói lớn.

## 3. Chạy trong container

Khởi động bringup TurtleBot hoặc mô phỏng của lớp trước. Robot và container cần
cùng `ROS_DOMAIN_ID`; mặc định script dùng domain 0. Script dùng mạng host và
IPC host để DDS giao tiếp trên Linux. Tắt các node teleop/navigation khác đang
xuất vào cùng topic vận tốc.

Xem thông tin hệ điều hành, ROS và Python bên trong image:

```bash
./scripts/docker.sh exec bash -c 'cat /etc/os-release; echo "$ROS_DISTRO"; python3 --version'
./scripts/docker.sh exec ros2 topic info /cmd_vel -v
```

Trong terminal desktop có `DISPLAY` và Xauthority hợp lệ, với webcam `/dev/video0`
và robot nhận `geometry_msgs/msg/Twist`:

```bash
./scripts/docker.sh run
```

Script truyền đúng thiết bị webcam, socket X11 và cookie Xauthority vào container;
không cần `--privileged` hoặc tắt kiểm soát truy cập X bằng `xhost +`.
Wayland cần XWayland và `DISPLAY`; môi trường SSH/headless không có màn hình
sẽ không mở được cửa sổ webcam. Lệnh `test` dùng màn hình ảo Xvfb nên không cần
webcam hay màn hình desktop.

Nếu driver nhận `geometry_msgs/msg/TwistStamped`:

```bash
./scripts/docker.sh run --ros-args -p stamped:=true
```

Đổi webcam, ví dụ `/dev/video2`, đồng thời đặt chỉ số OpenCV tương ứng:

```bash
CAMERA_DEVICE=/dev/video2 ./scripts/docker.sh run --ros-args -p camera_index:=2
```

Đặt domain khác, ví dụ 10, cho cả lệnh run và các terminal theo dõi:

```bash
ROS_DOMAIN_ID=10 ./scripts/docker.sh run
ROS_DOMAIN_ID=10 ./scripts/docker.sh exec ros2 topic echo /cmd_vel
```

Nếu robot dùng namespace, thêm `--ros-args -r /cmd_vel:=/robot1/cmd_vel`.
Không chạy cả hai kiểu message cùng lúc trên `/cmd_vel`.

Cửa sổ hiện webcam, khung mặt, nhãn và điểm dự đoán, vận tốc tiến/lùi và góc.
Nhấn **Q**, **Esc**, đóng cửa sổ hoặc **Ctrl+C** để thoát và gửi vận tốc 0.
Lỗi camera hoặc lỗi suy luận cũng dừng chương trình và gửi lệnh dừng.
Suy luận chạy ở luồng riêng để việc nạp/xử lý mô hình không chặn vòng xuất lệnh.
FPS suy luận phụ thuộc CPU/GPU; vòng hiển thị và xuất lệnh đặt mục tiêu 20 Hz.

Thử trên vùng sàn trống với vận tốc thấp đã đặt trong mã. Driver robot cần có
timeout vận tốc riêng để dừng khi tiến trình bị kill/mất mạng; chương trình
không thể gửi lệnh dừng khi hệ điều hành hoặc kết nối đã ngừng hoạt động.

## 4. Kiểm thử và minh chứng bài thực hành

Kiểm thử tự động trong image đã build, không cần webcam hay robot:

```bash
./scripts/docker.sh test
```

Các bài kiểm thử kiểm tra sáu ánh xạ, lọc kết quả liên tiếp, chuyển biểu cảm,
mất mặt, ngưỡng điểm, watchdog, giới hạn hành động, không tự lặp,
chọn mặt lớn nhất và phân biệt lỗi mô hình với không có mặt.
Mọi dependency kiểm thử được cài trong Docker. `scripts/verify_container.py`
kiểm tra Ubuntu 22.04/Python 3.10/Humble, chạy mô hình Emotion thật, xác nhận ảnh
không có mặt không sinh nhãn, mở cửa sổ OpenCV bằng Xvfb, rồi chạy node và
subscriber ROS thật với camera/nhãn giả để kiểm tra vận tốc và dừng khi camera lỗi.
Phần ROS này dùng domain 187 và topic riêng `/week8_test/cmd_vel`.
Kiểm chứng đó không thay thế việc nhận diện mặt thật qua webcam hay kết nối
robot qua mạng.

Để xem lệnh gửi thật từ chương trình, ở terminal khác trên host:

```bash
./scripts/docker.sh exec ros2 topic echo /cmd_vel
./scripts/docker.sh exec ros2 topic hz /cmd_vel
```

Kiểm tra lần lượt sáu hàng trong bảng, giữ mỗi biểu cảm ít nhất ba lần suy luận;
dùng Neutral giữa các lượt. Với Surprise cần giữ mặt hợp lệ trong suốt vòng xoay.
Thử che mặt, rời camera, rút camera và nhấn Q: robot phải dừng theo cơ chế trên.
Quay màn hình camera cùng robot/mô phỏng làm minh chứng; test tự động không
thay thế được việc xác nhận nhận diện và chuyển động trên thiết bị thực tế.

## 5. Cấu trúc và luồng xử lý

- `emotion_turtlebot/node.py`: đọc webcam → luồng DeepFace → chọn mặt lớn nhất
  → vẽ kết quả → xuất `Twist` hoặc `TwistStamped`.
- `emotion_turtlebot/controller.py`: lọc biểu cảm → ánh xạ vận tốc → giới hạn
  thời gian và dừng khi dữ liệu quá cũ; độc lập với ROS và camera.
- `tests/`: kiểm thử logic điều khiển và đầu ra bộ nhận diện bằng dữ liệu giả.
- `Dockerfile`, `.dockerignore`, `scripts/docker.sh`, `scripts/entrypoint.sh`: build và chạy container.
- `scripts/verify_container.py`: kiểm chứng runtime trong container.
- `package.xml`, `setup.py`, `setup.cfg`, `resource/`: khai báo gói `ament_python`.

Tham khảo API: [DeepFace](https://github.com/serengil/deepface),
[ROS Docker image](https://hub.docker.com/_/ros)
và [geometry_msgs](https://index.ros.org/p/geometry_msgs/).
