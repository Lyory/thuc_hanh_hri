# Tuần 5 — TurtleBot 4, Localization, Nav2 và YOLO

Hướng dẫn chạy trực tiếp trên **Ubuntu 22.04 + ROS 2 Humble + Ignition Gazebo Fortress**. Cần có desktop và driver đồ họa hoạt động; các cửa sổ Gazebo, RViz và OpenCV mở trên phiên desktop hiện tại.

Project dùng lại maze và bản đồ tuần 4. Hai bước chạy được tách riêng:

| Bước | Launch | Chức năng |
|---|---|---|
| 1 | `localization.launch.py` | Gazebo, robot, RViz, map, AMCL và Nav2; chờ đặt initial pose |
| 2 | `navigation.launch.py` | Tự đi qua các goal và mở camera YOLO; dùng pose đã đặt ở bước 1 |

## 1. Tải source và cài dependency

Giả định ROS 2 Humble đã được cài tại `/opt/ros/humble`.

```bash
cd ~
git clone --branch week5 https://github.com/Lyory/thuc_hanh_hri.git
cd thuc_hanh_hri
source /opt/ros/humble/setup.bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-pip python3-venv \
  ros-humble-turtlebot4-simulator ros-humble-turtlebot4-desktop \
  ros-humble-turtlebot4-navigation ros-humble-irobot-create-nodes \
  ros-humble-navigation2 ros-humble-nav2-simple-commander ros-humble-cv-bridge \
  ros-humble-slam-toolbox ros-humble-teleop-twist-keyboard
```

Cần cài Ignition Fortress nếu máy chưa có lệnh `ign gazebo`; xem [hướng dẫn chính thức](https://gazebosim.org/docs/fortress/install_ubuntu/).

## 2. Build simulator tuần 4 — thực hiện lần đầu

Source simulator được giữ trong `week4/src` để có cùng cấu hình robot/dock đã dùng với bản đồ này.

```bash
cd ~/thuc_hanh_hri/week4
source /opt/ros/humble/setup.bash
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
colcon build --symlink-install
```

Sau khi build, cài thư viện YOLO và tải weights:

```bash
cd ~/thuc_hanh_hri/week5
bash scripts/install.sh
```

Script tự dùng `sudo` cho apt khi chạy bằng tài khoản thường; `.venv` và weights được tạo trong thư mục tuần 5. **Không chạy toàn bộ script bằng `sudo`** để tránh tạo các file Python thuộc quyền root. PyTorch dùng CPU; NumPy/OpenCV được ghim phiên bản tương thích với cv_bridge Humble.

Không cần build colcon cho tuần 5 vì các node Python được chạy trực tiếp. `build/`, `install/`, log, `.venv` và weights được tạo tại máy, không lưu trong Git.

## 3. Terminal 1 — Localization

Trong mỗi terminal mới, cần source môi trường trước khi chạy lệnh ROS:

```bash
cd ~/thuc_hanh_hri/week5
source scripts/env.sh
ros2 launch "$PWD/launch/localization.launch.py"
```

Launch mở Gazebo và RViz, spawn robot gần `(0, 0)`, rồi nạp AMCL/Nav2 sau khoảng 15 giây. Robot chưa tự chạy goal.

1. Chờ map xuất hiện trên RViz; đặt **Fixed Frame = `map`**.
2. Dùng **2D Pose Estimate** đặt vị trí và hướng robot khớp với Gazebo.
3. Kiểm tra điểm LiDAR `/scan` trùng với tường trên map.

Với map đi kèm và robot vừa spawn tại dock, pose ban đầu gần **`(0, 0, 0)`** trong frame `map`. Map tuần 4 xoay khoảng 180° so với world Gazebo, nên yaw Gazebo không dùng trực tiếp làm yaw trên map.

**Giữ terminal 1 chạy trong suốt bài thực hành.** Model robot tên `turtlebot4` trong bảng Entity tree của Gazebo.

## 4. Terminal 2 — Navigation tự động và camera YOLO

Sau khi localization đúng, mở terminal thứ hai:

```bash
cd ~/thuc_hanh_hri/week5
source scripts/env.sh
ros2 launch "$PWD/launch/navigation.launch.py"
```

Chương trình giữ pose AMCL ở bước 1, tự undock nếu cần, rồi chạy **Goal 1 → Goal 2 → Goal 3**. Mỗi goal chỉ chuyển tiếp khi nhận `SUCCEEDED`; thất bại hoặc timeout thì dừng. Robot dừng 5 giây mô phỏng tại mỗi goal để quan sát.

Cửa sổ YOLO vẽ bounding box, tên class và confidence; terminal in kết quả và node publish ảnh lên `/yolo/annotated`.

**Không teleop hoặc đặt navigation goal bằng chuột khi chương trình đang chạy.** Ctrl+C ở terminal 2 để dừng navigation/YOLO; Ctrl+C ở terminal 1 để đóng mô phỏng. Dừng phiên cũ trước khi mở lại, tránh trùng node và `/clock`.

## 5. Sửa tọa độ goal

Sửa **`week5/config/goals.yaml`** bằng trình soạn thảo bất kỳ:

```yaml
initial_pose: [0.0, 0.0, 0.0]
goals:
  - {name: Goal 1, x: -2.0, y: 0.0, yaw: 1.5708}
  - {name: Goal 2, x: -2.0, y: -3.0, yaw: 3.1416}
  - {name: Goal 3, x: -6.0, y: -2.0, yaw: -1.5708}
```

- `x`, `y`: tọa độ **frame `map`**, đơn vị mét; chọn vùng trống cách tường/vật cản đủ xa.
- `yaw`: radian; `0` → +X, `1.5708` → +Y, `3.1416` → −X, `-1.5708` → −Y.
- Robot đi theo thứ tự các dòng trong `goals`. Giữ ít nhất ba goal; có thể thêm dòng.
- Giữ `initial_pose` trong file. Launch bước 2 không dùng trường này để đặt lại pose; nó chỉ được dùng khi chạy node riêng với `--initialize`.

Node đọc YAML lúc khởi động. Muốn áp dụng tọa độ mới, Ctrl+C **terminal 2**, lưu file rồi mở lại launch navigation; giữ terminal 1 chạy. Robot bắt đầu lại từ Goal 1 với pose AMCL hiện tại.

Để khảo sát điểm mới, chọn **Publish Point** trên RViz và xem:

```bash
ros2 topic echo /clicked_point
```

Hoặc ghi ba lần click thành file mới, với yaw tự chọn:

```bash
python3 scripts/record_goals.py --yaw 1.5708 3.1416 -1.5708
ros2 launch "$PWD/launch/navigation.launch.py" goals:="$PWD/config/goals_recorded.yaml"
```

Publish Point cho x/y; yaw được chọn riêng theo hướng muốn robot/camera nhìn. Có thể xem pose robot bằng `ros2 topic echo /amcl_pose`.

## 6. File và kết quả

| Đường dẫn | Nội dung |
|---|---|
| `maps/map.yaml`, `maps/map.pgm` | Map quét từ tuần 4 |
| `worlds/maze.sdf` | Maze với 3 người, 4 ghế, 1 ô tô và 2 bình chữa cháy |
| `models/README.md` | Vị trí và nguồn các mô hình |
| `scripts/navigate_goals.py` | ROS 2 node Python dùng Nav2 Simple Commander gửi goal tuần tự |
| `scripts/yolo_detector.py` | ROS 2 node nhận RGB → cv_bridge → YOLOv8n → ảnh có bounding box |
| `config/nav2.yaml` | Cấu hình navigation/costmap |
| `evidence/navigation.csv` | Kết quả từng goal; cần đủ ba `SUCCEEDED` |
| `evidence/detections.jsonl` | Class, confidence và bounding box đã phát hiện |

YOLO hiện tại có class `person`, `chair`, `car`; **chưa có class bình chữa cháy**. Muốn nhận diện đúng loại này cần model được train phù hợp hoặc tích hợp YOLO-World. Vật cản mới không được vẽ thêm vào map cũ; Nav2 dùng LiDAR để cập nhật costmap.

`evidence/` được tạo khi chạy. CSV navigation bị ghi đè mỗi lượt; JSONL detection được nối tiếp. Log trực tiếp nằm ở terminal và `~/.ros/log`. Video demo, log và output runtime không có trong bản source trên GitHub. Xem `VALIDATION.md` để phân biệt kết quả kiểm thử cũ với thay đổi world mới; chưa xác nhận lại toàn bộ bài trên máy Ubuntu native sạch.

## 7. Khi gặp lỗi

| Hiện tượng | Xử lý |
|---|---|
| `Chưa build simulator` | Chạy mục 2; phải có `week4/install/setup.bash`. |
| `ros2: command not found` hoặc thiếu package | Source `scripts/env.sh` trong terminal hiện tại và kiểm tra dependency mục 1. |
| Qt `xcb`, `could not connect to display` | Chạy từ terminal trong desktop của chính người dùng; không dùng `sudo` để chạy GUI. Kiểm tra `echo "$DISPLAY"`, giữ nguyên XAUTHORITY của desktop nếu có. |
| Gazebo đen hoặc không thấy robot | Project dùng MinimalScene + OGRE cho GUI, OGRE2 cho cảm biến. Dùng GUI config đi kèm và tìm model `turtlebot4` gần `(0, 0)`. |
| Chờ TF `map → base_link` | Kiểm tra AMCL/map_server active và đã đặt 2D Pose Estimate đúng ở terminal 1. |
| Không có ảnh camera hoặc `/scan` | Kiểm tra Gazebo đang Play, robot đã spawn và controller active. |

Lệnh kiểm tra, sau khi source môi trường:

```bash
ros2 lifecycle get /amcl
ros2 lifecycle get /map_server
ros2 lifecycle get /bt_navigator
ros2 control list_controllers
ros2 topic echo /clock --once
ros2 topic info /scan
ros2 topic info /oakd/rgb/preview/image_raw
```

Tham khảo: [TurtleBot 4 Navigator](https://turtlebot.github.io/turtlebot4-user-manual/tutorials/turtlebot4_navigator.html), [Nav2 Simple Commander](https://docs.nav2.org/commander_api/index.html), [Ultralytics](https://docs.ultralytics.com/).
