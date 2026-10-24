# Điều khiển TurtleBot 4 bằng cử chỉ tay

Bài tuần 6 dùng **Ubuntu 22.04, ROS 2 Humble, Gazebo Fortress**, webcam thật,
OpenCV và MediaPipe **Tasks Gesture Recognizer**. Toàn bộ thao tác chọn, xác nhận,
dừng và hủy trong demo đều bằng tay. Không có file test trong bài.

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

Mã nguồn ở `src/turtlebot4_gesture_control/turtlebot4_gesture_control/`.
Thông số ở `src/turtlebot4_gesture_control/config/gesture_control.yaml`.
Model chính thức `gesture_recognizer.task` được đặt trong thư mục `models/` của package.

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

### Kịch bản trình bày

1. Giơ một ngón: chỉ thấy `SELECTED`, robot chưa chạy. Giơ ngón cái: tiến–lùi 4 lần.
2. Giơ hai ngón rồi ngón cái: chạy một vòng tròn. Giữ ngón cái sau khi kết thúc:
   robot vẫn đứng yên.
3. Vẫy tay rồi ngón cái: robot quay trái–phải chào và trở lại hướng ban đầu gần đúng.
4. Khi đang chạy, xòe tay: robot dừng; nắm tay: về chờ. Chọn lại trước lần chạy sau.
5. Khi đang chạy, đưa tay ra ngoài camera: robot dừng sau timeout. Thử đóng cửa sổ
   webcam hoặc rút camera: node điều khiển cũng dừng khi mất kết quả nhận diện.

Không cần bấm phím trong các bước trên. `cv2.waitKey(1)` chỉ xử lý sự kiện cửa sổ,
không ánh xạ phím sang lệnh robot.

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

## Kết thúc demo

Dừng robot bằng Open Palm hoặc Closed Fist trước, rồi nhấn Ctrl+C tại terminal
launch để đóng các node và Gazebo. Bàn phím chỉ dùng khởi chạy/kết thúc chương
trình; chọn, xác nhận, dừng và hủy hành vi trong demo đều dùng cử chỉ tay.

## Xử lý lỗi

| Hiện tượng | Cách xử lý |
| --- | --- |
| Không có `/dev/video*` | Cắm/bật webcam, kiểm tra `ls -l /dev/video*` và quyền truy cập thiết bị |
| Camera đang bị chiếm | Đóng browser/video call/webcam_viewer và node nhận diện cũ |
| `No module named mediapipe` | Source `scripts/env.sh`, cài `python -m pip install -r requirements.txt` và build lại |
| Không mở được cửa sổ | Chạy trong terminal desktop có DISPLAY; `show_window:=false` chỉ dành cho chạy không GUI |
| Model không tồn tại | Chạy `bash scripts/build_workspace.sh`, hoặc truyền `model_path:=/đường/dẫn/model.task` |
| Robot báo thiếu LiDAR/odom | Đợi spawn xong, kiểm tra bridge và topic; không xác nhận khi Gazebo pause |
| Thường xuyên mất tín hiệu | Tăng ánh sáng, đưa cả bàn tay vào khung, giảm tải CPU; giữ Thumbs Up khi chạy |
| Wave không được chọn | Vẫy ngang đủ rộng hai lần đổi chiều; giữ bàn tay xòe cùng độ cao, sau đó giữ thêm 0,45 giây |
| Robot dừng vì vật cản | Dọn vùng mô phỏng hoặc khởi chạy lại sân; chọn và xác nhận lại |

## Tài liệu gốc

- [MediaPipe Gesture Recognizer Python](https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer/python)
- [OpenCV đọc và hiển thị webcam](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html)
- [TurtleBot 4 Simulator trên Humble](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html)
- [Cài Gazebo Fortress và repository OSRF](https://gazebosim.org/docs/fortress/install_ubuntu/)
