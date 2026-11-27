# Điều khiển TurtleBot 4 bằng cử chỉ tay

## Clone riêng nhánh week6

Nhánh `week6` là một workspace độc lập ngay tại gốc repository. Nó có mã nguồn
nhận diện/điều khiển, source TurtleBot 4 Simulator, world và model AI; không cần
clone các nhánh khác hay workspace của bài trước.

```bash
git clone --branch week6 --single-branch --depth 1 \
  https://github.com/Lyory/thuc_hanh_hri.git ~/hri_week6
cd ~/hri_week6
```

`--single-branch` chỉ lấy nhánh week6; `--depth 1` chỉ lấy snapshot mới nhất.
Không có thư mục `week4/` hoặc `week5/` trong bản clone này.

## Cài thư viện và build trên Ubuntu 22.04

Cần máy **Ubuntu 22.04 + ROS 2 Humble** đã cài và webcam laptop/USB. Từ thư mục
vừa clone, cài dependency hệ thống bằng rosdep và thư viện Python bằng venv:

```bash
cd ~/hri_week6
bash scripts/install_dependencies.sh
source scripts/env.sh
bash scripts/build_workspace.sh
source scripts/env.sh
```

Script cài đặt cần mạng và quyền sudo để cài các package ROS/Gazebo/Create 3,
compiler và thư viện Python. Source simulator nằm sẵn trong
`src/turtlebot4_simulator/`, được build **cùng workspace** với node cử chỉ.
Không cần tải thêm repository simulator hay source môi trường của bài khác.
Thông tin giấy phép và nguồn tài nguyên có trong [THIRD_PARTY.md](THIRD_PARTY.md).

Venv `.venv` dùng Python 3.10 và thấy thư viện ROS hệ thống. Script build kiểm
tra/tải model chính thức khi cần, rồi build toàn bộ package trong `src/` bằng
`python -m colcon`. Kết quả nằm ở `build_humble/`, `install_humble/`, `log_humble/`.
Model và world đã kèm sẵn; các thư viện hệ thống vẫn cần được cài theo bước trên.

Kiểm tra hai package đều đến từ workspace vừa build:

```bash
ros2 pkg prefix turtlebot4_ignition_bringup
ros2 pkg prefix turtlebot4_gesture_control
```

Đường dẫn phải nằm dưới `~/hri_week6/install_humble/`.
Mỗi terminal mới đều cần:

```bash
cd ~/hri_week6
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

Không mở thêm teleop, Nav2 hoặc publisher `/cmd_vel` khác khi demo. Robot và dock
được spawn cách nhau hơn 5 m, nên robot không cần lệnh bàn phím để undock.
Dùng launch `simulation.launch.py` kèm theo để có đúng bố trí sân demo.

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

Mỗi terminal mới: `cd ~/hri_week6` rồi `source scripts/env.sh`.

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
