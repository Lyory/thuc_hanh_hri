# Tuần 7 — Phân vùng bản đồ và điều hướng bằng giọng nói

**Hướng dẫn chạy trực tiếp trên Ubuntu 22.04 và ROS 2 Humble** (không dùng Docker).

TurtleBot 4, Gazebo Fortress, Nav2, OpenCV và Whisper. Đây là **project độc lập**,
có thể clone riêng, không cần thư mục tuần khác. Simulator upstream nằm ở
`src/turtlebot4_simulator`, giữ giấy phép gốc.

```text
map + region_seeds.yaml → segment_map.py → regions.json + ảnh phân vùng
micro / file âm thanh → Whisper → /voice_command (std_msgs/String)
                                      ↓
                             voice_navigation.py
                                      ↓
                         NavigateToPose → Nav2 → robot
```

## 1. Cài đặt từ máy mới

Yêu cầu: Ubuntu **22.04** desktop x86_64 (X11 hoặc XWayland), đã cài
**ROS 2 Humble** theo [hướng dẫn chính thức](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)
(kho APT `packages.ros.org` đã được thêm), có Internet ở lần cài đầu.

### 1.1. Cài gói hệ thống

```bash
sudo apt update
sudo apt install -y \
  git build-essential cmake python3-colcon-common-extensions \
  python3-venv python3-pip python3-opencv python3-yaml python3-pyqt5 \
  libportaudio2 libgl1-mesa-dri libgl1-mesa-glx \
  libxkbcommon-x11-0 libxcb-xinerama0 fonts-dejavu-core \
  ignition-tools libignition-gazebo6 libignition-gazebo6-plugins \
  libignition-rendering6-ogre2 libignition-physics5-dartsim \
  libignition-gui6-dev qml-module-qtquick-extras \
  ros-humble-turtlebot4-description ros-humble-turtlebot4-msgs \
  ros-humble-turtlebot4-navigation ros-humble-turtlebot4-node ros-humble-turtlebot4-viz \
  ros-humble-irobot-create-ignition-bringup ros-humble-irobot-create-nodes \
  ros-humble-irobot-create-toolbox ros-humble-ign-ros2-control \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-nav2-simple-commander \
  ros-humble-rviz2 ros-humble-joint-state-publisher
```

Gazebo Fortress được cài từ kho ROS. Không cần meta-package `ignition-fortress`
đầy đủ, SciPy hay FFmpeg dòng lệnh (PyAV giải mã âm thanh).

### 1.2. Clone project

```bash
git clone --branch week7 --single-branch https://github.com/Lyory/thuc_hanh_hri.git turtlebot4-voice-navigation
cd turtlebot4-voice-navigation
```

Cấu trúc tại root project:

```text
.
├── README.md
├── requirements.txt
├── scripts/                 # env, build, demo, phân vùng, ASR, ROS nodes, kiểm tra
├── launch/                  # Các launch của riêng project
├── config/                  # Seed, Nav2, RViz; nhãn vùng được build tạo lại
├── maps/map.yaml
├── maps/map.pgm
├── worlds/rooms.sdf
└── src/turtlebot4_simulator/ # Source đã kèm, bao gồm LICENSE và 4 package
```

`src/turtlebot4_simulator` là source thực đã kèm, không cần submodule hay clone thêm.

### 1.3. Tạo môi trường Python

Tại root project:

```bash
source /opt/ros/humble/setup.bash
python3 -m venv --system-site-packages .venv
touch .venv/COLCON_IGNORE
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

`.venv` dùng chung thư viện ROS, OpenCV, PyQt5 của hệ thống qua
`--system-site-packages`; chỉ cài thêm `numpy`, `faster-whisper`, `sounddevice`.

### 1.4. Build và kiểm tra

```bash
bash scripts/build.sh
```

Script nạp `scripts/env.sh` (ROS Humble + `.venv`), build 4 package simulator vào
`build_humble/`, `install_humble/` (giới hạn 2 job, đổi bằng `WEEK7_BUILD_JOBS=N`)
rồi chạy phân vùng bản đồ. Sau build có thể kiểm tra (khuyến nghị):

```bash
source scripts/env.sh
python scripts/check_core.py && python scripts/check_route_planning.py && python scripts/check_install.py
```

Chỉ dùng một model Whisper `small`. Lần thu đầu sẽ tự tải nếu chưa có. Muốn tải
trước khi mở demo, chạy **một lần**:

```bash
source scripts/env.sh
python scripts/speech_recognition.py --download-only --model small
```

Model lưu trong `models/`, không cần tải lại.

> **Mỗi terminal mới** muốn chạy lệnh `python scripts/...` hoặc `ros2 ...` của
> project phải `source scripts/env.sh` tại root project trước. Script đặt
> `ROS_DOMAIN_ID=77`; log/cache ROS và Gazebo nằm trong `.runtime/`.

## 2. Mở demo và nói lệnh

Mỗi lần dùng chỉ cần một terminal tại root project:

```bash
bash scripts/demo.sh launch/week7.launch.py
```

Demo chạy Gazebo server và mở cửa sổ **Điều hướng giọng nói · A / B / C**; tự khởi tạo
AMCL, Nav2 và undock robot vừa spawn. Đợi `READY: AMCL active, Nav2 active, robot
undocked` trong terminal và trạng thái Nav2 active trên giao diện. **Không chạy
initialize thêm lần nữa** khi dùng chế độ mặc định, nhất là khi robot đã di chuyển.

Trong cửa sổ điều khiển:

1. Chọn micro. Mặc định ưu tiên micro USB hoặc micro số laptop (DMIC) khi có;
   có thể chọn lại thiết bị trong danh sách.
2. Bấm **Thu một câu (6 giây)**. Chờ hiện **Đang thu**, rồi nói.
3. Đọc câu nhận dạng ở ô **Bạn nói**, tuyến A → B và trạng thái thực hiện.
4. Quan sát robot và đường Nav2 màu xanh trên bản đồ. Nút **Dừng robot / hủy
   tuyến** gửi yêu cầu hủy, đợi trạng thái đã hủy trước khi gửi tuyến khác.

| Nói | Thực hiện |
|---|---|
| “Đi đến khu vực A.” | Đến phòng học A |
| “Di chuyển từ khu vực A đến khu vực B.” | Đến A trước, sau đó đến B, kể cả khi bắt đầu ở C |
| “Đi đến phòng thí nghiệm.” | Đến B |
| “Đi từ phòng A qua hành lang C rồi đến phòng B.” | A → C → B |
| “Đi đến A rồi đến B.” | A → B |
| “Đi đến B rồi quay lại C.” | B → C |
| “Đi đến khu vực D.” | Báo vùng không tồn tại; không gửi đích nào |

Ô **Gửi văn bản thử nghiệm** dùng kiểm tra điều hướng khi chưa có micro; không
phải kết quả nhận giọng nói. Lệnh mới khi robot bận bị từ chối (`BUSY`); mỗi chặng
chỉ tiếp tục khi Nav2 báo `SUCCEEDED`. Nếu một chặng thất bại, các chặng còn lại
được hủy. Nút dừng phát lệnh hủy goal Nav2, không chỉ đổi chữ trên giao diện.

Muốn mở thêm RViz, chạy `bash scripts/demo.sh launch/week7.launch.py rviz:=true`.
RViz hiển thị map, LiDAR, costmap, đường Nav2, nhãn A/B/C và lớp màu Semantic
Regions. Trên bản đồ chỉ ghi A/B/C để tránh lỗi font; tên đầy đủ nằm trong chú giải.
GUI dùng Qt (PyQt5), không cần trình duyệt hoặc web service.

### Tuyến nhiều điểm đến và đường dự kiến

Nói **“Đi từ phòng A qua hành lang C rồi đến phòng B.”** hoặc nhập cùng câu vào
ô thử văn bản. Chương trình kiểm tra toàn bộ tên vùng, rồi yêu cầu Nav2 lập
đường từ vị trí hiện tại qua **A → C → B** trước khi gửi goal di chuyển đầu tiên.
Robot đến A trước dù đang ở C; mỗi chặng chỉ tiếp tục sau `SUCCEEDED`.

- Đường **tím nét đứt** trên cửa sổ điều khiển là toàn tuyến dự kiến ban đầu;
  đường **xanh** là chặng hiện tại, được Nav2 cập nhật khi di chuyển.
- Ô số cạnh nhãn A/B/C biểu thị thứ tự ghé. Dòng tuyến dùng ✓ cho điểm đã đến,
  ▶ cho chặng đang chạy và ○ cho điểm còn lại; trạng thái có số chặng, ví dụ 2/3.
- RViz có display **Route Preview** màu tím, topic `/voice_navigation/preview_path`,
  cùng các khu vực trong **Semantic Regions**. Bật qua `rviz:=true`.
- Nav2 có thể cập nhật đường chặng hiện tại khi xuất hiện vật cản. Đường toàn
  tuyến là phương án tính lúc nhận lệnh, không phải cam kết đường luôn giữ nguyên.

Nếu có vùng sai ở giữa câu (A → D → B), toàn bộ lệnh bị từ chối. Nếu lập đường
thất bại hoặc hết thời gian chờ 15 giây, robot chưa bắt đầu tuyến. Nút dừng hủy
cả yêu cầu lập đường đang chờ hoặc goal đang chạy và bỏ các điểm chưa đi;
preview được xóa khi hủy, thất bại hoặc hoàn thành.

Cũng có thể nói **“Đi từ phòng học qua hành lang rồi đến phòng thí nghiệm.”**
Whisper small có thể nghe nhầm chữ cái đọc liền nhau; kiểm tra phần **Bạn nói**.
Các cách đọc “bê/xê” được cấu hình làm alias, còn tên lạ như “phòng Ad” vẫn bị
từ chối. Dùng tên chức năng đầy đủ khi nhận dạng chữ cái chưa chính xác.

Giao diện chẩn đoán hiển thị điểm LiDAR màu đỏ, vòng cam là vị trí thật Gazebo,
chấm đen là vị trí ước lượng từ TF, vận tốc yêu cầu/odom và tốc độ mô phỏng.
Khi robot bị chặn, xem cảnh báo bumper, giới hạn lùi hoặc hành vi Create 3;
trạng thái Nav2 hiện khoảng cách còn lại và số lần phục hồi. Có đường đi chưa
đảm bảo robot đang chuyển động. `demo.sh` dùng khóa `.runtime/demo.lock` để không
chạy hai bộ mô phỏng/Nav2 trong cùng domain.

## 3. Bản đồ phòng và phân vùng

Bản đồ mới **10 × 7 m**, độ phân giải 0,05 m/pixel (200 × 140 pixel). Khu có tường
bao khoảng 9 × 5,5 m; hai cửa rộng 1,5 m nối phòng với hành lang, có tủ làm vật cản.

```text
             ┌─────────────────┬─────────────────┐
             │ A · Phòng học   │ B · Thí nghiệm  │
             │    tủ           │           tủ    │
             ├────  cửa  ──────┼────  cửa  ──────┤
             │             C · Hành lang        │
             │      vị trí robot khi khởi tạo   │
             └───────────────────────────────────┘
```

| ID | Tên | Đích x, y gần đúng (m, frame map) |
|---|---|---|
| A | Phòng học | −2,2; 2,2 |
| B | Phòng thí nghiệm | 2,2; 2,2 |
| C | Hành lang | 0; −1 |

`maps/map.pgm`, `maps/map.yaml`, `worlds/rooms.sdf` đã kèm trong project.
`scripts/generate_demo_map.py` tạo cả map và world từ **cùng các hình học tường/tủ**,
không tải asset bên ngoài. World cũ `worlds/maze.sdf` không còn là world mặc định.
Dock được spawn riêng, có collision thấp hơn LiDAR nên footprint của nó cũng
được đánh dấu trong map tại pose spawn mặc định. Không bỏ ô dock này: robot có
thể liên tục đụng dock rồi tự lùi dù Nav2 đã vẽ đường. Điểm tham chiếu liên
thông trong YAML là `start: [-0.35, 0]`, tức vị trí sau khi undock, không phải
vị trí đang tiếp xúc dock lúc spawn.
Nếu sửa hình học, tái tạo bằng:

```bash
source scripts/env.sh
python scripts/generate_demo_map.py
python scripts/segment_map.py
```

Dừng demo trước khi đổi bản đồ rồi khởi động lại. Muốn chỉ sửa seed hoặc alias,
sửa `config/region_seeds.yaml` và chạy `python scripts/segment_map.py`.

Phân vùng dùng OpenCV threshold occupancy, distance transform, thành phần liên
thông 4 hướng. Ngưỡng `partition_clearance: 0.8` tách lõi phòng qua cửa hẹp,
sau đó lan truyền nhãn ra vùng trống để giữ hành lang thành vùng riêng. Tên chức năng do cấu hình gán,
không suy luận tự động “phòng học” từ hình ảnh. Chương trình tạo lại:

- `config/regions.json`: ID, tên, alias, diện tích và điểm đích.
- `config/region_labels.npy`: nhãn mỗi pixel.
- `config/segmented_map.png`: ảnh phân vùng có A/B/C.

Điểm đích phải nằm trong vùng an toàn liên thông với vị trí khởi đầu, clearance
ít nhất 0,35 m. Seed không an toàn được chuyển tới điểm an toàn gần nhất. Chuyển
pixel ↔ tọa độ ROS dùng resolution, origin và góc yaw của map YAML. Nav2 dùng
map và LiDAR để lập đường, cập nhật costmap và tránh vật cản.

## 4. Micro, nhận dạng và chế độ terminal

Whisper dùng CPU int8, 2 luồng; chỉ nạp model khi bấm thu. Giao diện thu từng câu,
không nghe liên tục. Đầu vào được thu theo sample rate gốc của thiết bị rồi đổi
về 16 kHz bằng PyAV. Mức thu dBFS/peak hiển thị sau khi thu. Tín hiệu gần như im
lặng được báo rõ, không âm thầm gửi văn bản rỗng thành lệnh robot.

Nếu không nhận giọng nói, chọn micro DMIC/USB đúng thiết bị, kiểm tra mute trong
cài đặt âm thanh của Ubuntu rồi thử lại. Mức thu có tín hiệu chưa đảm bảo ASR đúng;
đọc lại câu trong **Bạn nói**. Độ chính xác vẫn phụ thuộc tiếng ồn và phát âm.

Không mở đồng thời terminal recognition và nút thu GUI trên cùng thiết bị.
Muốn dùng riêng terminal (sau `source scripts/env.sh`):

```bash
python scripts/speech_recognition.py --list-devices
python scripts/speech_recognition.py --model small --device N
```

Thay `N` bằng chỉ số input. Tùy chọn `--once` thu một câu sau khi nạp model;
`--cpu-threads 1` giảm CPU nhưng có thể chậm hơn. Nếu chỉ muốn mở lại cửa sổ điều
khiển khi demo còn chạy:

```bash
python scripts/voice_panel.py
```

Dùng file thật đã đặt trong project:

```bash
python scripts/speech_recognition.py --audio evidence/lenh_cua_toi.wav
```

Thêm `--no-publish` để chỉ nhận dạng. Với nhiều file, lệnh ASR không đợi robot
hoàn tất giữa các file; gửi từng file và đợi hoàn tất để tránh `BUSY`.

## 5. Dừng, chạy nhẹ và cập nhật

Ctrl+C terminal demo để dừng các node. Lần sau chỉ chạy lại `demo.sh`; không build
lại hoặc tải model mỗi lần.

| Tình huống | Lệnh / cách xử lý |
|---|---|
| Không cần cửa sổ Gazebo/RViz, vẫn muốn bảng điều khiển | `bash scripts/demo.sh launch/week7.launch.py headless:=true rviz:=false` |
| Chạy hoàn toàn không GUI | `bash scripts/demo.sh launch/week7.launch.py headless:=true rviz:=false panel:=false` |
| Bật cả Gazebo 3D và RViz (nặng hơn) | `bash scripts/demo.sh launch/week7.launch.py headless:=false rviz:=true` |
| Muốn tự initialize bằng terminal thứ hai | Chạy demo với `auto_initialize:=false`, rồi `python scripts/initialize.py` một lần |
| Chỉ chạy mô phỏng + AMCL/Nav2, không có giao diện giọng nói | `bash scripts/demo.sh launch/localization.launch.py` |
| Sửa Python/launch | Dừng rồi mở lại demo; không cần build lại |
| Sửa simulator C++ | `bash scripts/build.sh` |
| Sửa `requirements.txt` | `.venv/bin/python -m pip install -r requirements.txt` |
| Sửa seed/map | `python scripts/segment_map.py`, rồi mở lại demo |

Log ứng dụng lưu trong `evidence/` (`transcripts.jsonl`, `navigation.jsonl`);
log/cache ROS và Gazebo nằm trong `.runtime/`.

## 6. Kiểm tra và xử lý lỗi

```bash
source scripts/env.sh
python scripts/check_core.py && python scripts/check_route_planning.py && python scripts/check_install.py
```

Lệnh kiểm tra logic phân tích câu, map/clearance, dependency, package, launch và
cú pháp YAML RViz. Sau khi demo tự initialize xong, ở terminal thứ hai (sau
`source scripts/env.sh`) có thể kiểm tra Nav2 thực:

```bash
# Văn bản → Nav2 (robot sẽ di chuyển):
python scripts/verify_navigation.py
# Giọng tổng hợp có sẵn → Whisper → Nav2:
python scripts/verify_navigation.py --speech
# Hủy và từ chối tuyến khi đang bận:
python scripts/verify_controls.py
# Nhiều điểm, thứ tự A → C → B và hình học preview:
python scripts/verify_multidest.py
# Cùng câu nhiều điểm qua file giọng tổng hợp và Whisper:
python scripts/verify_multidest.py --speech
```

Chạy từng kiểm thử riêng, không đồng thời ra lệnh qua micro. Nếu thiếu mẫu tổng
hợp, `scripts/make_speech_fixtures.py` có thể tạo lại qua Google TTS (cần Internet);
**không cần tải mẫu để dùng micro/demo**. Kết quả giọng tổng hợp không thay thế
kiểm tra micro thật. Kết quả kiểm thử được ghi vào `evidence/` (không đưa lên Git).
Mẫu đọc chữ cái là `evidence/synthetic_speech/command_5.mp3`; mẫu dùng tên
chức năng là `command_6.mp3` (dùng cho kiểm thử `--speech`). Script tạo mẫu chỉ
tải file còn thiếu hoặc có nội dung đã thay đổi theo manifest. Whisper small có
thể nhận sai mẫu đọc chữ cái liền nhau; mẫu dùng tên chức năng ổn định hơn.

| Lỗi | Xử lý |
|---|---|
| `Cần Ubuntu 22.04 + ROS 2 Humble` | Cài ROS 2 Humble vào `/opt/ros/humble` |
| `Chưa có .venv` | Làm lại bước 1.3 tại root project |
| `Package ... not found` khi chạy | Chạy `bash scripts/build.sh`, rồi `source scripts/env.sh` trong terminal đó |
| Không mở cửa sổ | Chạy từ terminal của phiên desktop (có `DISPLAY`) |
| RViz trống | Chạy `check_install.py`; Semantic Regions phải dùng Topic `/semantic_regions` |
| Build báo thiếu đường dẫn libignition cũ | `build.sh` đã dùng `--cmake-clean-cache`; nếu vẫn lỗi, xóa `build_humble/ install_humble/` rồi build lại |
| AMCL chưa có pose / frame map | Đợi auto-initialize; không tắt demo trong khi chờ |
| `Demo tuần 7 đang chạy` | Đã có một demo khác; dừng nó trước (Ctrl+C) |
| Micro trả rỗng | Xem dBFS/peak; chọn DMIC/USB thay jack headset và kiểm tra mute |
| Model/gói không tải được lần đầu | Kiểm tra kết nối tới APT Ubuntu/ROS, PyPI, Hugging Face |

Project dùng `ROS_DOMAIN_ID=77` để tách khỏi các chương trình ROS khác trên máy.
