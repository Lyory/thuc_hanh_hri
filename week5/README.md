# Tuần 5 — TurtleBot 4, Localization, Nav2 và YOLO


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

Cài thư viện YOLO và tải weights:

```bash
cd ~/thuc_hanh_hri/week5
bash scripts/install.sh
```
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
