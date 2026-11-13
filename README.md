# Tuần 8: Nhận diện biểu cảm và điều khiển TurtleBot

Gói ROS 2 Python dùng webcam, OpenCV và DeepFace để nhận diện biểu cảm,
hiển thị hình ảnh cùng kết quả và xuất vận tốc lên `/cmd_vel` ở 20 Hz.
Môi trường mục tiêu: Ubuntu 24.04, ROS 2 Jazzy, Python 3.12 và desktop có webcam.

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

## 2. Cài đặt

Trong thư mục bài tập:

```bash
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`--system-site-packages` giúp dùng `rclpy` từ ROS đã cài. Không cài `rclpy`
bằng pip. Cần OpenCV có GUI, không thay bằng `opencv-python-headless`.
Nếu thiếu công cụ hệ thống: cài `python3-venv`, `python3-colcon-common-extensions`
và `ros-jazzy-geometry-msgs` qua trình quản lý gói của Ubuntu.
DeepFace/TensorFlow là các phụ thuộc lớn; lần đầu cần mạng để tải trọng số
về `~/.deepface/weights`. Chương trình nạp mô hình trước khi mở camera.

Build gói (vẫn trong thư mục bài tập và venv đã kích hoạt):

```bash
python -m colcon build --symlink-install --packages-select emotion_turtlebot
source install/setup.bash
```

Dùng `python -m colcon` để entry point được build bằng Python của venv chứa
DeepFace. Giữ venv khi chạy; mỗi terminal mới cần source ROS, activate venv
và source `install/setup.bash`.

## 3. Chạy

Khởi động bringup TurtleBot hoặc mô phỏng của lớp trước. Máy chạy chương trình
và robot cần cùng `ROS_DOMAIN_ID` và cấu hình DDS để tìm thấy nhau.
Tắt các node teleop/navigation khác đang xuất vào cùng topic vận tốc.

Xác định kiểu message robot đang nhận:

```bash
ros2 topic info /cmd_vel -v
```

Nếu robot nhận `geometry_msgs/msg/Twist` (mặc định của bài):

```bash
ros2 run emotion_turtlebot emotion_control
```

Nếu driver robot nhận `geometry_msgs/msg/TwistStamped`:

```bash
ros2 run emotion_turtlebot emotion_control --ros-args -p stamped:=true
```

Đổi webcam, ví dụ camera số 1:

```bash
ros2 run emotion_turtlebot emotion_control --ros-args -p camera_index:=1
```

Nếu robot dùng namespace, remap đúng topic, ví dụ `--ros-args -r /cmd_vel:=/robot1/cmd_vel`.
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

Kiểm thử tự động không cần DeepFace, webcam hay robot:

```bash
python -m pytest -q tests
```

Các bài kiểm thử kiểm tra sáu ánh xạ, lọc kết quả liên tiếp, chuyển biểu cảm,
mất mặt, ngưỡng điểm, watchdog, giới hạn hành động, không tự lặp,
chọn mặt lớn nhất và phân biệt lỗi mô hình với không có mặt.
Cần `pytest`, `rclpy`, `geometry_msgs` và OpenCV trong môi trường chạy test.

Để xem lệnh gửi thật từ chương trình, ở terminal khác đã source ROS:

```bash
ros2 topic echo /cmd_vel
ros2 topic hz /cmd_vel
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
- `package.xml`, `setup.py`, `setup.cfg`, `resource/`: khai báo gói `ament_python`.

Tham khảo API: [DeepFace](https://github.com/serengil/deepface)
và [geometry_msgs](https://index.ros.org/p/geometry_msgs/).
