# Tuần 7 — Phân vùng bản đồ và điều hướng bằng giọng nói

**Hướng dẫn cho người clone project từ GitHub, dùng ROS 2 Humble.**
Nếu dùng máy của tác giả đã thiết lập Docker, xem [README.local.md](README.local.md)
để chạy ngay, không lặp lại phần cài đặt.

Ubuntu **22.04**, **ROS 2 Humble**, TurtleBot 4, Gazebo Fortress, Nav2.
Mọi bước build, xử lý ảnh, nhận âm thanh và chạy ROS đều ở trong Docker.
Đây là **project độc lập**, có thể clone riêng. Dockerfile dùng image công khai
`ros:humble-ros-base-jammy`; không cần image hay container của tác giả.
Container `hri-week7` mount root project vào `/root/hri/week7` bên trong Docker;
tên/vị trí thư mục clone trên host có thể tùy chọn. Không cần thư mục tuần khác.
Simulator upstream nằm ở `src/turtlebot4_simulator`, giữ giấy phép gốc.

```text
map + region_seeds.yaml → segment_map.py → regions.json + ảnh phân vùng
micro / file âm thanh → Whisper → /voice_command (std_msgs/String)
                                      ↓
                             voice_navigation.py
                                      ↓
                         NavigateToPose → Nav2 → robot
```

## 1. Cài đặt từ máy mới

Hướng dẫn dành cho Linux Ubuntu desktop x86_64 có X11 hoặc XWayland, Docker
Engine và kết nối Internet. Bên trong Docker luôn là Ubuntu 22.04 + Humble;
host không cần cài ROS, Gazebo hoặc thư viện Python. Nếu host đã cài Humble,
vẫn chạy các lệnh qua Docker bên dưới; script tự nạp môi trường ROS trong container.
Windows/macOS và ARM chưa
được kiểm chứng với cấu hình truyền GUI, thiết bị và mạng này.

### 1.1. Gói trên host

Nếu Docker đã được cài và `docker info` chạy thành công, chỉ cài
`git xauth` nếu thiếu. Nếu chưa có Docker, trên Ubuntu sạch:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git xauth
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

Đăng xuất/đăng nhập lại để áp dụng nhóm Docker, sau đó kiểm tra:

```bash
docker info
```

Nếu đã dùng một bản Docker khác, làm theo [hướng dẫn Docker cho Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
để xử lý gói xung đột trước khi chuyển bản cài. Các lệnh ở trên chỉ là hướng
dẫn cho người clone; project không tự thay đổi Docker trên host.

### 1.2. Clone riêng project

Clone riêng nhánh `week7` của repository `thuc_hanh_hri`:

```bash
git clone --branch week7 --single-branch https://github.com/Lyory/thuc_hanh_hri.git turtlebot4-voice-navigation
cd turtlebot4-voice-navigation
```

Repository cần có cấu trúc dưới đây ngay tại root, không cần thư mục bao ngoài
`hri` hoặc các thư mục tuần khác:

```text
.
├── AGENTS.md
├── README.md
├── requirements.txt
├── docker/Dockerfile
├── scripts/                 # Docker, build, phân vùng, ASR, ROS nodes, kiểm tra
├── launch/                  # Các launch của riêng project
├── config/                  # Seed, Nav2, RViz; nhãn vùng được build tạo lại
├── maps/map.yaml
├── maps/map.pgm
├── worlds/rooms.sdf
└── src/turtlebot4_simulator/ # Source đã kèm, bao gồm LICENSE và 4 package
```

Khi đưa project này lên repository riêng, đưa toàn bộ source/cấu hình/map/world
và Dockerfile vào Git. Không chỉ đưa README hoặc scripts. `src/turtlebot4_simulator`
là source thực đã kèm, không cần submodule hay clone thêm workspace.

### 1.3. Chuẩn bị lần đầu

Từ root project trên host, build image công khai và 4 package simulator:

```bash
bash scripts/docker.sh build
```

Image cài Humble, Fortress runtime, Nav2, RViz, OpenCV, Qt, PortAudio và Whisper.
Dependency APT nằm trong `docker/Dockerfile`, Python trong `requirements.txt`.
Không cần SciPy, Git trong container hoặc FFmpeg dòng lệnh; PyAV giải mã âm thanh.

Sau build có thể kiểm tra (khuyến nghị, không bắt buộc mỗi lần chạy):

```bash
bash scripts/docker.sh check
```

Chỉ dùng một model Whisper `small`. Lần thu đầu sẽ tự tải nếu chưa có. Muốn tải
trước khi mở demo, chạy tùy chọn này **một lần**:

```bash
bash scripts/docker.sh recognition --download-only --model small
```

Model lưu trong `models/`; không cần tải lại sau khi dừng hoặc tạo lại container.
Lần cài đầu cần Internet cho Docker Hub, APT Ubuntu/ROS, PyPI và Hugging Face.

## 2. Mở demo và nói lệnh

Mỗi lần dùng chỉ cần một terminal tại root project trên host:

```bash
bash scripts/docker.sh demo
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

Muốn mở thêm RViz, chạy `bash scripts/docker.sh demo rviz:=true`. RViz hiển thị map, LiDAR, costmap, đường Nav2, nhãn A/B/C và lớp màu Semantic
Regions. Trên bản đồ chỉ ghi A/B/C để tránh lỗi font; tên đầy đủ nằm trong chú giải.
GUI dùng Qt đã khai báo trong Docker, không cần trình duyệt hoặc web service.

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
  cùng các khu vực trong **Semantic Regions**. Bật qua `demo rviz:=true`.
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
đảm bảo robot đang chuyển động. `demo` và `simulation` dùng chung khóa để không
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
Nếu sửa hình học, tái tạo bằng Docker:

```bash
bash scripts/docker.sh exec python scripts/generate_demo_map.py
bash scripts/docker.sh segment
```

Dừng demo trước khi đổi bản đồ rồi khởi động lại. Muốn chỉ sửa seed hoặc alias,
sửa `config/region_seeds.yaml` và chạy `segment`.

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
cài đặt âm thanh host rồi thử lại. Mức thu có tín hiệu chưa đảm bảo ASR đúng;
đọc lại câu trong **Bạn nói**. Độ chính xác vẫn phụ thuộc tiếng ồn và phát âm.

Không mở đồng thời terminal recognition và nút thu GUI trên cùng thiết bị.
Muốn dùng riêng terminal:

```bash
bash scripts/docker.sh recognition --list-devices
bash scripts/docker.sh recognition --model small --device N
```

Thay `N` bằng chỉ số input. Tùy chọn `--once` thu một câu sau khi nạp model;
`--cpu-threads 1` giảm CPU nhưng có thể chậm hơn. Nếu chỉ muốn mở lại cửa sổ điều
khiển khi demo còn chạy:

```bash
bash scripts/docker.sh panel
```

Dùng file thật đã đặt trong project:

```bash
bash scripts/docker.sh recognition --audio evidence/lenh_cua_toi.wav
```

Thêm `--no-publish` để chỉ nhận dạng. Với nhiều file, lệnh ASR không đợi robot
hoàn tất giữa các file; gửi từng file và đợi hoàn tất để tránh `BUSY`.

Script truyền ALSA `/dev/snd` vào Docker khi có. Nếu vừa gắn micro sau khi tạo
container, dừng demo rồi `bash scripts/docker.sh recreate`. Môi trường chỉ dùng
PulseAudio/PipeWire mà không có thiết bị ALSA cần chuyển tiếp âm thanh riêng.

## 5. Dừng, chạy nhẹ và cập nhật

Ctrl+C terminal demo để dừng các node, rồi có thể dừng container:

```bash
bash scripts/docker.sh stop
```

Lần sau chỉ chạy `demo`. Không build lại hoặc tải model mỗi lần.

| Tình huống | Lệnh / cách xử lý |
|---|---|
| Không cần cửa sổ Gazebo/RViz, vẫn muốn bảng điều khiển | `bash scripts/docker.sh demo headless:=true rviz:=false` |
| Chạy hoàn toàn không GUI | `bash scripts/docker.sh demo headless:=true rviz:=false panel:=false` |
| Muốn tự initialize bằng terminal thứ hai | Chạy demo với `auto_initialize:=false`, rồi `bash scripts/docker.sh initialize` một lần |
| Sửa Python/launch | Dừng rồi mở lại demo; không cần build image |
| Sửa simulator C++ | `bash scripts/docker.sh rebuild` |
| Sửa Dockerfile/requirements | `bash scripts/docker.sh build` |
| Sửa seed/map | `segment`, rồi mở lại demo |

Build giới hạn 2 job. ASR chỉ dùng model small; không yêu cầu tải model khác.
Dockerfile không cài meta-package Fortress đầy đủ hoặc SciPy. Qt đã có trên máy
hiện tại và được khai báo rõ để người clone cài đủ. Console Docker xoay vòng
10 MB/file, 2 file khi tạo container mới. ROS log/cache nằm trong
`.docker-runtime/` của project; log ứng dụng lưu trong `evidence/`.

## 6. Kiểm tra và xử lý lỗi

```bash
bash scripts/docker.sh check
```

Lệnh kiểm tra logic phân tích câu, map/clearance, dependency, package, launch và
cú pháp YAML RViz. Sau khi demo tự initialize xong, có thể kiểm tra Nav2 thực:

```bash
# Văn bản → Nav2 (robot sẽ di chuyển):
bash scripts/docker.sh exec python scripts/verify_navigation.py
# Giọng tổng hợp có sẵn → Whisper → Nav2:
bash scripts/docker.sh exec python scripts/verify_navigation.py --speech
# Hủy và từ chối tuyến khi đang bận:
bash scripts/docker.sh exec python scripts/verify_controls.py
# Nhiều điểm, thứ tự A → C → B và hình học preview:
bash scripts/docker.sh exec python scripts/verify_multidest.py
# Cùng câu nhiều điểm qua file giọng tổng hợp và Whisper:
bash scripts/docker.sh exec python scripts/verify_multidest.py --speech
```

Chạy từng kiểm thử riêng, không đồng thời ra lệnh qua micro. Nếu thiếu mẫu tổng
hợp, `scripts/make_speech_fixtures.py` có thể tạo lại qua Google TTS (cần Internet);
**không cần tải mẫu để dùng micro/demo**. Kết quả giọng tổng hợp không thay thế
kiểm tra micro thật. Kết quả có ngày và giới hạn tại [VALIDATION.md](VALIDATION.md).
Mẫu đọc chữ cái là `evidence/synthetic_speech/command_5.mp3`; mẫu dùng tên
chức năng là `command_6.mp3` (dùng cho kiểm thử `--speech`). Script tạo mẫu chỉ
tải file còn thiếu hoặc có nội dung đã thay đổi theo manifest. Kết quả sai của
mẫu đọc chữ cái được ghi riêng trong VALIDATION, không tính là kiểm thử đạt.

| Lỗi | Xử lý |
|---|---|
| Docker permission denied | Kiểm tra nhóm Docker và đăng nhập lại sau khi thêm nhóm |
| Không mở cửa sổ | Dùng terminal desktop có DISPLAY/Xauthority và X11/XWayland |
| RViz trống | Chạy `check`; cấu hình phải đọc được YAML và Semantic Regions dùng Topic `/semantic_regions` |
| Build báo thiếu đường dẫn libignition cũ | `rebuild` tự làm mới cache CMake, không cần tải lại gói |
| AMCL chưa có pose / frame map | Đợi auto-initialize; không tắt demo trong khi chờ |
| Micro trả rỗng | Xem dBFS/peak; chọn DMIC/USB thay jack headset và kiểm tra mute |
| Model/gói không tải được lần đầu | Kiểm tra kết nối Docker Hub/APT/PyPI/Hugging Face |

Để kiểm tra clone độc lập từ source (chỉ dành cho phát triển):

```bash
bash scripts/verify_clean_clone.sh
```

Bản sao nằm trong `.docker-runtime/`, tự dọn cùng tag image sau khi kết thúc.
Dùng `WEEK7_KEEP_CHECK=1` nếu cần giữ để debug. Không dùng bước này mỗi lần demo.

Không chạy ROS trên host, không cần source ROS 2 Jazzy của host. Project dùng
`ROS_DOMAIN_ID=77`, container riêng `hri-week7` và image công khai Humble.
