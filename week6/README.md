# Điều khiển TurtleBot 4 bằng cử chỉ tay

## Các thành phần

```text
webcam → gesture_recognition_node → /detected_gesture (std_msgs/String)
                                  ↓
                            robot_behavior_node → /cmd_vel (geometry_msgs/Twist)
                                  ↑
                              /odom, /scan
                                  ↓
                    /robot_behavior_state → cửa sổ webcam
```

| File launch | Tác dụng |
| --- | --- |
| `simulation.launch.py` | Gazebo, sân trống 12 × 12 m, TurtleBot 4 và bridge cảm biến |
| `gesture_recognition.launch.py` | Đọc webcam, nhận diện, hiển thị và publish cử chỉ |
| `gesture_control.launch.py` | Chạy mô phỏng cùng hai node; có thể dùng simulation đã mở |


Lấy project:

```bash
git clone --branch week6 https://github.com/Lyory/thuc_hanh_hri.git ~/thuc_hanh_hri
cd ~/thuc_hanh_hri/week6
sudo apt update
sudo apt install python3-pip python3-venv python3-colcon-common-extensions libgl1 libglib2.0-0
```

Script môi trường tự nạp `/opt/ros/humble/setup.bash` và simulator tại
`../week4/install/local_setup.bash` nếu có. Nếu workspace simulator ở vị trí khác,
chỉ định trước khi source:

```bash
# Chỉ cần dòng này nếu simulator nằm ở workspace riêng:
export TURTLEBOT4_SETUP=/duong/dan/workspace_simulator/install/setup.bash
source scripts/env.sh
ros2 pkg prefix turtlebot4_ignition_bringup
ros2 pkg prefix irobot_create_ignition_bringup
```

## Cài thư viện và build

Tại thư mục `~/thuc_hanh_hri/week6`:

```bash
python3 -m venv --system-site-packages .venv
source scripts/env.sh
python -m pip install -r requirements.txt
bash scripts/build_workspace.sh
source scripts/env.sh
```

Venv dùng Python 3.10 của Ubuntu 22.04 và thấy các thư viện ROS hệ thống qua
`--system-site-packages`. Script build kiểm tra/tải model chính thức rồi dùng
`python -m colcon` từ venv để tạo executable có thể import MediaPipe.
Kết quả nằm trong `build_humble/`, `install_humble/`, `log_humble/`.

Mỗi terminal mới cần:

```bash
cd ~/thuc_hanh_hri/week6
source scripts/env.sh
```

## Chạy toàn bộ demo

```bash
ros2 launch turtlebot4_gesture_control gesture_control.launch.py
```

Đổi sang webcam khác:

```bash
ros2 launch turtlebot4_gesture_control gesture_control.launch.py camera_index:=1
```

Sau khi sửa mã nguồn, YAML, launch hoặc model, đóng phiên demo rồi build lại:

```bash
bash scripts/build_workspace.sh
source scripts/env.sh
```

Đợi robot xuất hiện ở tâm sân, LiDAR và odometry hoạt động; giữ một bàn tay trong
khung hình, đủ sáng.


| Cử chỉ / nội dung String | Tác dụng |
| --- | --- |
| Vẫy tay / `Wave` | Chọn chào: quay trái 0,5 rad, phải 1 rad, trái 0,5 rad |
| Một ngón / `Pointing_Up` | Chọn 4 chu kỳ tiến 0,35 m rồi lùi 0,35 m; tổng 8 chặng |
| Hai ngón / `Victory` | Chọn một vòng tròn bán kính 0,45 m, góc quay đủ 2π |
| Ngón cái / `Thumb_Up` | Xác nhận và chạy hành vi vừa chọn |
| Xòe tay / `Open_Palm` | Dừng, xóa hành vi và lựa chọn; không tự chạy lại |
| Nắm tay / `Closed_Fist` | Hủy, xóa lựa chọn và về `IDLE` |

Giữ cử chỉ chọn và xác nhận ít nhất **0,45 giây** mỗi cử chỉ. Cửa sổ webcam hiển
thị nhãn, confidence và trạng thái `IDLE`, `SELECTED`, `RUNNING`, `STOPPED`.
Sau khi chọn, xác nhận trong **8 giây**. Tiếp tục giữ Thumbs Up trong khi robot
thực hiện để duy trì tín hiệu điều khiển. Đưa tay ra ngoài khung quá **0,8 giây**
sẽ hủy chuyển động; đưa tay trở lại không làm robot tự chạy tiếp.
Nếu lựa chọn đã hết hạn mà vẫn giữ cử chỉ cũ, nắm tay để hủy rồi chọn lại.

Một lần giữ Thumbs Up chỉ kích hoạt một lần. Sau khi hoàn tất hoặc dừng do mất
tín hiệu, chọn lại rồi xác nhận lại. Không dùng việc giấu tay rồi giơ lại Thumbs Up
để phát lệnh lần nữa.

### Cách vẫy tay và ưu tiên dừng

MediaPipe có sẵn năm nhãn tĩnh trong bảng; `Wave` là phần mở rộng theo thời gian:
tay được AI nhận là `Open_Palm`, cổ tay dịch ngang ít nhất 10% chiều rộng khung
hình mỗi lượt và đổi hướng ít nhất hai lần trong 1,8 giây. Thực hiện trái → phải
→ trái → phải ở cùng độ cao. Confidence hiển thị của Wave là confidence nhận
diện bàn tay xòe nền, không phải xác suất của một model Wave riêng.

Chỉ nhận Wave khi đang chờ/dừng hoặc đang chọn lời chào. Lúc đầu các frame
`Open_Palm` đưa robot về dừng; khi đủ chuyển động, nhãn chuyển thành `Wave` và
được giữ đến khi đổi tư thế tay. Giữ thêm 0,45 giây rồi chuyển sang Thumbs Up.
**Trong lúc `RUNNING`, mọi Open Palm đều dừng ngay, kể cả tay đang vẫy.**
Wave cũng phải xác nhận bằng Thumbs Up để đáp ứng quy tắc mọi hành vi di chuyển
đều cần xác nhận.


## Chạy riêng từng thành phần

Mỗi terminal mới: `cd ~/thuc_hanh_hri/week6` rồi `source scripts/env.sh`.

Mô phỏng:

```bash
ros2 launch turtlebot4_gesture_control simulation.launch.py
```

Kiểm tra webcam đơn thuần, đóng cửa sổ trước khi chạy nhận diện:

```bash
ros2 run turtlebot4_gesture_control webcam_viewer --camera-index 0
```

Chỉ nhận diện, không điều khiển:

```bash
ros2 launch turtlebot4_gesture_control gesture_recognition.launch.py
# Trong terminal khác đã source môi trường:
ros2 topic echo /detected_gesture
```

Điều khiển dùng mô phỏng đã mở (đóng node nhận diện riêng trước để tránh trùng camera):

```bash
ros2 launch turtlebot4_gesture_control gesture_control.launch.py start_simulation:=false
```

Quan sát topic trong các terminal khác:

```bash
ros2 topic info /cmd_vel --verbose
ros2 topic echo /cmd_vel
ros2 topic echo /robot_behavior_state
ros2 topic hz /scan
ros2 topic hz /odom
```

Để kiểm tra robot nhận `/cmd_vel` mà vẫn không dùng bàn phím điều khiển, chọn
Pointing Up rồi xác nhận bằng tay. Quan sát `linear.x` dương/âm trên `/cmd_vel`
và robot tiến/lùi trong Gazebo. Khi chưa xác nhận, Twist phải bằng 0.

## Dừng an toàn và giới hạn

- Chỉ publish cử chỉ hợp lệ khi confidence ít nhất 0,70; không có tay là `No_Hand`,
  tín hiệu không đủ tin cậy là `Unknown`. Cả hai không gia hạn quyền điều khiển.
- Nhãn chọn/xác nhận cần ổn định 0,45 giây, khoảng ngắt frame trên 0,25 giây làm
  tính lại thời gian. Không reset khóa chống lặp chỉ vì một frame nhiễu.
- Open Palm và Closed Fist được xử lý ngay khi có frame đủ confidence; không
  đợi debounce. Twist 0 được phát ngay trong callback và tiếp tục ở 20 Hz.
- Mất cử chỉ hợp lệ trên 0,8 giây, mất `/scan` hoặc `/odom` trên 0,6 giây đều
  dừng và xóa hành vi; timer dùng đồng hồ monotonic, không phụ thuộc `/clock`.
- Lidar kiểm tra mọi hướng: vật cản cách tâm cảm biến dưới 0,40 m hoặc quá nhiều
  ray không hợp lệ sẽ hủy chuyển động. Không tắt guard để ép robot chạy.
- Độ dài/góc quay được tích lũy từ odometry có dấu, không chỉ chạy theo thời gian.
  Không tiến triển ít nhất 0,005 m/rad trong 6 giây sẽ hủy; mỗi chặng còn có giới
  hạn tổng thời gian bằng 10 lần thời lượng danh định (ít nhất 30 giây), cho phép
  simulation chạy chậm. Khi pause, mất dữ liệu cảm biến mới sẽ làm dừng sớm hơn.
- Sân trống giới hạn rủi ro va chạm; LiDAR là cơ chế dừng, không phải thuật toán
  tránh đường như Nav2. Mốc 0,40 m là khoảng cách từ cảm biến, không từ vỏ robot.
  Quỹ đạo và vị trí kết thúc có sai số do độ trễ, quán tính và odometry.
- Watchdog của node xử lý mất camera/nhận diện khi node điều khiển còn hoạt động.
  Trường hợp kill cưỡng bức cả node điều khiển phụ thuộc timeout vận tốc của base;
  cần xác minh cấu hình base trước khi mở rộng sang robot thật.


