# Kết quả kiểm tra tuần 7

Bản Git giữ các kết quả JSON, ảnh minh họa và mẫu giọng nói tổng hợp nhỏ trong
`evidence/`. Các tên file `.log`/`.jsonl` bên dưới là log của những lần chạy trên
máy phát triển, không đưa lên Git. Khi chạy lại, chương trình tự tạo log mới.

Ngày **28/10/2026**, múi giờ Asia/Ho_Chi_Minh. Chạy trong Docker Ubuntu
**22.04.5 LTS**, ROS 2 **Humble**, Python 3.10. Các lượt điều hướng/ASR ban đầu
bên dưới dùng image nền cục bộ `hri:humble`. Sau đó Dockerfile đã chuyển sang
image công khai để project có thể clone riêng; xem mục kiểm tra độc lập cuối
file. Không chạy ROS trên host.

## Phân vùng và logic

- Build thành công 4 package của TurtleBot 4 simulator bằng colcon.
- Tạo `config/regions.json`, `region_labels.npy`, `segmented_map.png` với A/B/C.
- Đích A (−2.025, 0.025), B (−2.025, −2.975), C (−6.025, −1.975), frame map.
  Clearance lần lượt khoảng 1,00 m, 1,00 m, 0,95 m; cùng thành phần liên thông
  khi chừa khoảng trống tối thiểu 0,35 m.
- `check_core.py` đạt: 6 câu hợp lệ, 7 câu bị từ chối, nhãn không đè tường/vùng
  chưa biết, clearance, đổi tọa độ với origin yaw khác 0 và trường hợp negate.
- Python compile và cú pháp Bash đạt. Image Docker cuối khởi tạo node và publish
  semantic markers thành công trong domain riêng để tránh ảnh hưởng mô phỏng.

Map PGM giữ nguyên từ tuần 4. Chỉ bản YAML của tuần 7 đổi free_thresh từ 0.25
thành 0.196 để giữ pixel 205 là vùng chưa biết. Các seed/nhãn chức năng được đặt
thủ công, ranh giới vùng tính tự động theo khoảng cách lan truyền có vật cản.
Không tuyên bố nhận diện tự động phòng học/phòng thí nghiệm từ ảnh.

## Nav2 thực trong mô phỏng

Gazebo Fortress chạy server không GUI, vẫn render LiDAR/camera. AMCL được đặt
pose khởi đầu đúng bản đồ, undock thành công. Nav2 map server, AMCL và các server
điều hướng active. Kết quả kiểm thử gửi văn bản:

| Câu lệnh | Chuỗi đích | Kết quả | Giây thực |
|---|---|---|---:|
| Đi đến khu vực A | A | SUCCEEDED | 29,82 |
| Di chuyển từ khu vực A đến khu vực B | A → B | Cả hai SUCCEEDED | 44,46 |
| Đi đến hành lang | C | SUCCEEDED | 68,41 |
| Đi từ khu vực A đến khu vực D | Không gửi goal | INVALID | — |

Bằng chứng: `evidence/nav2_verification.json`, `navigation.jsonl`,
`simulation.log`. Action status **4** là SUCCEEDED. Đây là chạy robot và
Nav2 thật trong simulation, không dùng mock action server.

## Âm thanh → Whisper → Nav2

Whisper `small`, CPU int8, tiếng Việt. Ba file âm thanh **tổng hợp** từ Google
Translate TTS ở `evidence/synthetic_speech/`, có manifest nguồn. Không phải
bản thu micro hoặc bằng chứng chất lượng nhận dạng giọng người thật.

| Nội dung âm thanh tổng hợp | Đích sau ASR | Nav2 | Giây thực toàn luồng |
|---|---|---|---:|
| Đi đến khu vực A | A | SUCCEEDED | 74,27 |
| Di chuyển từ khu vực A đến khu vực B | A → B | Cả hai SUCCEEDED | 48,23 |
| Đi đến phòng thí nghiệm | B | SUCCEEDED | 5,88 |

Lượt này bắt đầu khi robot ở C sau phép kiểm tra văn bản, nên thời gian đến A
khác lượt đầu. File thứ tư đọc “Đi đến khu vực D” bị Whisper nhận thành
“Đi đến khu vực 500”; parser từ chối vùng 500, không gửi goal. Điều này cho thấy
ASR vẫn có sai số, kể cả giọng tổng hợp; không phải mọi bản ghi đều nhận đúng.

Bằng chứng: `evidence/speech_nav2_verification.json`, `speech_pipeline.log`,
`transcripts.jsonl` và `navigation.jsonl`. Ba câu hợp lệ được nhận dạng từ âm
thanh rồi publish trực tiếp vào ROS, không thay bằng văn bản chép sẵn ở lượt này.

## Đang chạy, dừng và hủy

`verify_controls.py` đạt với Nav2 thực:

1. Nhận tuyến C → A, gửi goal C.
2. Nhận lệnh B khi đang bận, trả BUSY, không gửi thêm goal.
3. Nhận “dừng lại”, Nav2 ACK hủy và kết thúc goal C với status **5** (CANCELED).
4. Không gửi goal A còn lại.

Bằng chứng: `evidence/control_verification.json`, `control_verification_retry.log`.
Lượt kiểm tra đầu bị timeout do kênh phản hồi DDS chưa được khám phá khi phát
goal quá nhanh; robot vẫn nhận goal và lệnh hủy trong cleanup. Đã sửa bộ kiểm
thử để bắt tay kênh phản hồi bằng câu không điều hướng trước khi thử. Log thất
bại giữ ở `control_verification.log`; không dùng làm kết quả đạt.

## Giới hạn kiểm chứng

- Môi trường hiện tại không có `/dev/snd`, chưa kiểm tra thu micro thật và độ
  chính xác với giọng người dùng. Đã có đường thu micro ALSA trong chương trình.
- Đã kiểm tra ảnh phân vùng. Chưa kiểm tra trực quan GUI Gazebo/RViz; lượt Nav2
  thực chạy không GUI. RViz đã được cấu hình sẵn topic semantic markers.
- Chưa thử vật cản động hoặc đo va chạm hình học. Kết quả SUCCEEDED xác nhận
  các tuyến đã chạy; không phải bảo đảm tránh va chạm trong mọi tình huống.
- Không quay video trong lượt này. Các log và JSON là bằng chứng kiểm thử.
- Model và các kết quả build nằm trong workspace mount; ROS_DOMAIN_ID=77.

## Kiểm tra project có thể clone riêng — 28/10/2026

Dockerfile hiện dùng **`ros:humble-ros-base-jammy`** công khai, không cần
`hri:humble`. Đã build thành công image mới từ nền công khai và cài đầy đủ gói
APT/Python bằng Dockerfile/requirements. Fortress 6.18.0 lấy từ kho ROS đã được
image nền cấu hình sẵn; không phụ thuộc kho APT hoặc khóa ký trên máy tác giả.

Đã chạy `bash scripts/verify_clean_clone.sh`, tạo bản sao source tại
`/tmp/week7-clean-clone.ohJnje`, loại bỏ:

- build/install/log, cache model, evidence và cookie màn hình;
- toàn bộ dữ liệu phân vùng đã sinh trước đó;
- metadata Git và cache Python.

Trong bản sao không có thư mục tuần khác, phép kiểm tra đạt:

1. Build image từ Dockerfile có nền công khai.
2. Build mới cả 4 package simulator từ source đã kèm.
3. Tạo lại JSON, nhãn pixel và ảnh phân vùng từ map/seed trong project.
4. Kiểm tra logic/map, import Python, ament package, tài nguyên map/world/config,
   phiên bản Gazebo và tham số launch.

Lệnh `bash scripts/docker.sh check` tại project chính cũng đạt với image mới,
bao gồm kiểm tra package robot_state_publisher, joint_state_publisher và các
bridge ROS/Gazebo. Bằng chứng: `evidence/clean_clone.log`.

Đã khởi động thêm container từ image công khai mới, chỉ mount source bản sao
sạch cùng thiết bị render và cookie X11 của phiên desktop. Gazebo spawn robot,
AMCL và Nav2 active, undock thành công; `initialize.py` báo
`READY: AMCL active, Nav2 active, robot undocked`. Không mount code, map hay
install của các tuần khác. Bằng chứng: `evidence/standalone_smoke.log` và
`evidence/standalone_initialize.log`. Lượt kiểm tra mới này xác nhận khởi động
mô phỏng/định vị/undock; không chạy lại toàn bộ các tuyến trong bảng ở trên.

Phép kiểm tra này sử dụng Internet và cache layer công khai của Docker; không
phải kiểm tra cài đặt offline. Model Whisper không được chép từ máy tác giả;
README có lệnh tải model riêng sau khi clone. Các số liệu điều hướng ở phần
trên vẫn là kết quả lượt ban đầu, không được gán lại cho image mới.

## Debug sau khi đổi image — 07/11/2026

- Log build mới báo `No rule to make target ... libignition-common4-profiler.so.4.9.0`.
  Cache CMake trong workspace vẫn giữ đường dẫn 4.9.0, trong khi image đang chạy
  cung cấp thư viện 4.8.1. Thêm `--cmake-clean-cache` vào build để cấu hình lại
  đường dẫn trước khi tái dùng object. Build lại đủ 4 package đạt trong 4,60 giây,
  không tải thêm image, dependency hoặc model. Log: `evidence/debug_rebuild.log`.
- Log AMCL cũ có yêu cầu lifecycle mất phản hồi và chưa nhận initial pose;
  global costmap chờ transform `map`. Initialize giờ giới hạn mỗi yêu cầu
  lifecycle ở 3 giây rồi thử lại trong tổng timeout, và in rõ giai đoạn đang chờ.
- `scripts/docker.sh check` đạt sau build. Đã chạy mô phỏng không GUI hai phiên
  mới; phiên dùng bản initialize đã sửa đạt `READY: AMCL active, Nav2 active,
  robot undocked`. Log: `evidence/debug_demo_retry.log` và
  `evidence/debug_initialize_retry.log`.
- Chưa chạy lại toàn bộ tuyến điều hướng hoặc kiểm tra micro trong lượt debug.
  Thông báo service camera/motor phần cứng không có vẫn xuất hiện trong mô phỏng;
  AMCL, Nav2 và undock vẫn đạt. Các phiên kiểm tra được đóng sau khi hoàn tất.

## Sửa cửa sổ RViz trống — 07/11/2026

`config/navigation.rviz` đặt display `Semantic Regions` sau khóa `Enabled` của
Visualization Manager, làm YAML không hợp lệ. Chuyển display trở lại danh sách
`Displays`; bổ sung đọc và kiểm tra RViz YAML vào `check_install.py` vì
`ros2 launch --show-args` không phát hiện lỗi này.

Đã chạy `scripts/docker.sh check` đạt và mở lại riêng RViz trong phiên mô phỏng
đang chạy. Kiểm tra trực quan cửa sổ xác nhận có map, robot, LaserScan, costmap,
bảng Displays và Navigation 2; Navigation và Localization đều active. Không
khởi động lại Gazebo/Nav2, không initialize lại và không tải thêm gói.
Log: `evidence/debug_rviz.log`. Có một thông báo GLSL khi tạo map ban đầu;
ảnh kiểm tra sau đó xác nhận map/costmap đã render được.

## Bản đồ phòng, giao diện và ASR — 07/11/2026

Đã chuyển mặc định sang map 10 × 7 m, 200 × 140 pixel, hai phòng A/B nối hành
lang C qua cửa khoảng 1,5 m. `scripts/generate_demo_map.py` tạo map và world
`rooms.sdf` từ cùng các hình học tường/tủ. Bản cũ 402 × 402 pixel không còn là
map mặc định. Phân vùng tách lõi theo clearance 0,8 m rồi lan truyền nhãn, điểm
đích vẫn phải có clearance tối thiểu 0,35 m và liên thông với vị trí khởi đầu.

RViz trước đó không đăng ký `/semantic_regions` do dùng khóa `Marker Topic`;
đổi thành `Topic` đã có subscriber thực. Kiểm tra thông điệp xác nhận đúng ba
nhãn văn bản **A/B/C**, không kèm tên tiếng Việt. Giao diện Qt cũng chỉ ghi ID
trên map; chú giải và câu nhận dạng hiển thị riêng. Ảnh kiểm tra được tạo bằng
widget Qt tại `evidence/panel_preview.png`.

Giao diện hiện vị trí AMCL, đường `/plan`, câu `/voice_command`, trạng thái và
tuyến điều hướng; có nút thu một câu, chọn micro, thử văn bản và hủy goal. Demo
mặc định chạy Gazebo server + Qt, tự initialize và undock. Nút micro chờ cả Nav2
active và initialize kết thúc để không tranh điều khiển khi robot đang undock.
RViz bật qua `rviz:=true`; GUI Gazebo qua `headless:=false`. Trong thử nghiệm GUI
Gazebo đã crash ở MinimalScene render thread, nên không còn bật mặc định.

Đầu vào ALSA mặc định trên máy có thể trỏ jack headset; đã đọc metadata PCM từ
host để xác định micro số tích hợp **DMIC (hw:0,6), thiết bị sounddevice 4**.
Thông tin này được tạo lại trong `.docker-runtime/alsa-pcm`, không là dependency
bên ngoài project. Micro được chọn tự động, có thể đổi trong GUI. Đã kiểm tra
thiết bị hỗ trợ mono/48 kHz và kiểm tra PyAV đổi 48 kHz → 16 kHz. ASR báo mức
RMS/peak, im lặng hoặc không nhận được tiếng nói; bỏ bộ lọc xác suất thứ hai từng
có thể loại câu ngắn. Chưa đo độ chính xác giọng người dùng thật sau thay đổi.

Kiểm thử dùng **file giọng tổng hợp có sẵn**, model small đã tải, qua Whisper →
`/voice_command` → Nav2 thực trong Docker Humble:

| Câu | Tuyến | Kết quả | Giây thực |
|---|---|---|---:|
| Đi đến khu vực A | A | SUCCEEDED | 64,04 |
| Di chuyển từ khu vực A đến khu vực B | A → B | Cả hai SUCCEEDED | 448,56 |
| Đi đến phòng thí nghiệm | B | SUCCEEDED | 12,30 |
| File đọc khu vực D, ASR nghe thành khu vực 500 | Không gửi goal | INVALID | — |

Bằng chứng: `evidence/rooms_speech_verification.json`,
`evidence/rooms_speech_verification.log`, `evidence/rooms_demo_verified.log` và
`evidence/speech_pipeline.log`. Chặng A → B phải phục hồi nhiều lần và chậm;
SUCCEEDED không có nghĩa đã tối ưu thời gian hoặc đã kiểm chứng không va chạm
hình học. Lượt này chưa kiểm tra vật cản động. Reflex/safety của Create 3 vẫn giữ
cấu hình mặc định; lệnh CLI chẩn đoán tham số không áp dụng thay đổi.

`check` đạt với PyQt, phân vùng và RViz YAML/topic. Sau khi bổ sung trạng thái
lưu câu/tuyến gần nhất, đã kiểm tra lại câu phòng thí nghiệm tới B và snapshot
status cho GUI mở muộn. Không tải thêm gói, model hoặc asset trong lượt này;
Dockerfile khai báo thêm Qt rõ ràng cho máy clone mới (image hiện có đã có Qt).
Phiên cuối được mở ở chế độ nhẹ trong `evidence/rooms_final_demo.log`.

## Sửa robot kẹt dù đã có đường — 07/11/2026

Phát hiện hai phiên demo cùng domain 77, dùng khoảng 1135% CPU. Đã dừng cả
hai và thêm khóa `flock` dùng chung cho lệnh `demo`/`simulation`. Kiểm thử mở
chồng cả hai lệnh đều bị từ chối trước khi spawn thêm simulator/Nav2:
`evidence/stuck_duplicate_rejected.log`,
`evidence/stuck_simulation_duplicate_rejected.log`.

Sau khi còn một phiên, vẫn tái hiện được lỗi khi đi từ A sang B: tại vị trí
thật gần (0,0), Nav2 yêu cầu tiến 0,26 m/s nhưng odometry báo lùi khoảng
0,12 m/s; Create 3 báo đang chạy hành vi tự động và chặn vận tốc ngoài. AMCL
lúc đó lệch vị trí thật khoảng 0,64 m. Bằng chứng:
`evidence/stuck_single_motion_b.json` và `evidence/stuck_single_demo.log`.

Dock được spawn riêng tại (0,157; 0), yaw pi. Collision trong package Humble
là box 0,04 × 0,13 × 0,10 m, offset x=-0,045 trong frame dock; tâm collision
trong world là (0,202; 0). LiDAR cao khoảng 0,19 m nên không thấy vật cản thấp
này, còn map cũ bỏ sót dock và liên tục dẫn robot đi xuyên qua nó. Generator
giờ đánh dấu tất cả pixel giao footprint dock, kể cả box nhỏ hơn 1 pixel.
Tham chiếu liên thông dùng vị trí sau undock (-0,35; 0) vì spawn đang sát dock.
`check_core.py` kiểm tra dock là occupied và điểm sau undock có đủ clearance.

Giữ nguyên tốc độ, DWB và phản xạ an toàn; xác nhận qua service Create 3:
`reflexes_enabled=true`, `safety_override=none`
(`evidence/stuck_safety_settings.json`). Không sửa lỗi bằng cách tắt bumper.

Kiểm thử Nav2 bằng văn bản trên map đã sửa, một phiên và có giao diện Qt:

| Lệnh / trạng thái xuất phát | Tuyến đạt SUCCEEDED | Giây thực | Phục hồi |
|---|---|---:|---:|
| Đi đến A sau undock | A | 34,11 | 0 |
| Đi từ A đến B, đang ở A | A → B | 73,36 | 0 |
| Đi đến hành lang từ B | C | 55,41 | 0 |
| Đi từ A đến B, bắt đầu ở C (0,181; -0,874) | A → B | 122,76 | 0 |

Lệnh A → D bị từ chối và không gửi goal. Bằng chứng:
`evidence/stuck_fixed_navigation.json`, `evidence/stuck_fixed_demo.log` và
`evidence/stuck_from_c_route.json`. Lượt này kiểm tra chuyển động bằng văn bản,
không đo lại ASR; không phải benchmark cùng điều kiện với lượt giọng nói
448,56 giây phía trên. Không có thông báo lặp lại "Ignoring velocities" hoặc
"Reached backup limit" trong lượt điều hướng đã sửa. Không suy rộng thành
đảm bảo không va chạm với mọi vật cản động.

Giao diện 2D hiện LiDAR đỏ, vị trí thật Gazebo bằng vòng cam, vị trí ước lượng
từ TF bằng chấm đen, vận tốc yêu cầu/odom, tốc độ mô phỏng, sai lệch định vị,
cảnh báo Create 3 và khoảng cách/số lần phục hồi từ feedback Nav2. Quét callback
có giới hạn thời gian để không làm treo Qt; dữ liệu cảm biến dùng depth 1 để
giảm hiển thị trễ. Đã kiểm tra trực quan `evidence/panel_preview.png`.

Kiểm tra thêm phản hồi muộn từ chặng trước không được ghi đè tiến độ chặng mới.
`check` đạt trong Docker Humble. Bộ kiểm thử văn bản mặc định đã bổ sung tuyến
A → B sau khi về C. Không tải thêm gói/model hoặc build lại image; `util-linux`
đã có và được khai báo rõ trong Dockerfile cho lần build từ máy mới.

## Mở rộng nhiều điểm đến và preview toàn tuyến — 07/11/2026

Parser hỗ trợ A → C → B bằng câu “Đi từ phòng A qua hành lang C rồi đến phòng
B”, các chuỗi “Đi đến A rồi đến B” và “Đi đến B rồi quay lại C”. Alias bê/xê
được khai báo cho tên phòng/hành lang. Tất cả vùng được kiểm tra trước khi lập
đường; A → D → B bị từ chối mà không gửi goal A.

Trước khi di chuyển, node gọi Nav2 `ComputePathThroughPoses` từ pose hiện tại
qua toàn bộ danh sách đích. Path thành công mới được publish tại
`/voice_navigation/preview_path`, rồi thực hiện từng `NavigateToPose`; chỉ
chuyển chặng sau `SUCCEEDED`. Timeout lập đường là 15 giây trên steady clock.
Hủy hoặc timeout làm mất hiệu lực callback cũ để không khởi hành từ kết quả
trả về muộn. Các điểm đã đến và số chặng nằm trong snapshot trạng thái.

Giao diện Qt hiện toàn tuyến bằng nét đứt tím, chặng hiện tại xanh, số thứ tự
cạnh A/B/C và dòng ✓ đã đến / ▶ đang đi / ○ còn lại. RViz đã thêm display
`Route Preview` với QoS transient local. Preview ban đầu được giữ khi đang
điều hướng và xóa khi xong, hủy hoặc thất bại; đường chặng hiện tại tiếp tục
được Nav2 cập nhật theo costmap. Đã kiểm tra trực quan ảnh
`evidence/multidest_preview_active.png` khi robot ở chặng 2/3.

Kiểm thử Nav2 thực trong Docker Humble:

| Nguồn lệnh | Tuyến | Điểm preview | Giây thực | Phục hồi | Kết quả |
|---|---|---:|---:|---:|---|
| Văn bản câu A → C → B | A, C, B | 480 | 118,55 | 0 | Cả 3 SUCCEEDED |
| Giọng tổng hợp “đi từ phòng học qua hành lang rồi đến phòng thí nghiệm” → Whisper | A, C, B | 487 | 127,41 | 0 | Cả 3 SUCCEEDED |

Kiểm tra preview có các đích theo đúng thứ tự, toàn bộ điểm nằm trên pixel
trống, PLAN_READY trước GOAL_SENT, step lần lượt 1/2/3, completed cuối đủ A/C/B,
và preview được xóa sau khi hoàn tất. Bằng chứng:
`evidence/multidest_verification.json`,
`evidence/multidest_speech_verification.json`, `evidence/multidest_asr.log` và
`evidence/multidest_final_demo.log`.

Giới hạn ASR: mẫu đọc chữ cái liên tiếp `command_5.mp3` đã bị Whisper small
nghe thành “phòng Ad ... Hành Lang Xe”; lệnh bị từ chối và robot không đi.
Thử gợi ý từ vựng không sửa ổn định được lỗi này, nên không giữ thay đổi prompt
hoặc tự ánh xạ “Ad” thành A. Mẫu tên chức năng `command_6.mp3` nhận đúng và
thực hiện đủ tuyến. Cả hai mẫu đều là Google TTS, không phải bằng chứng nhận
giọng người dùng thật. Manifest và script tạo mẫu được kèm để tạo lại.

`check` gồm thêm 6 ca: preview thành công trước di chuyển; thất bại/path rỗng
không di chuyển; hủy bỏ kết quả muộn; acceptance muộn bị cancel; timeout; vùng
sai ở giữa bị từ chối trước planning. Startup được giới hạn polling lifecycle
0,2 giây khi chưa active để không flood service. Không cài thêm gói/model;
chỉ tải thêm hai mẫu MP3 nhỏ và dùng lại small. Không chạy lại kiểm tra clone
sạch/build image trong lượt này.

Đã kiểm tra tương thích planner với một đích: `ComputePathThroughPoses` nhận
một pose B, trả `SUCCEEDED` và path 7 điểm (`evidence/multidest_single_planner.log`).
Lần truy vấn đầu bị timeout phản hồi DDS; truy vấn sau khi chờ discovery đạt.
Đây là kiểm tra lập đường, không gửi thêm lệnh di chuyển robot.


## Kiểm tra bản publish nhánh week7 — 07/11/2026

Bản source chuẩn bị cho GitHub không chứa build/install/log, cache model hoặc
metadata riêng của máy. Từ bản sao này, chạy container mới bằng image
`hri-week7:humble` hiện có, tắt mạng (`--network none`), không dùng install cũ:

- Build thành công cả 4 package từ source; tạo lại phân vùng A/B/C từ map.
- `check_core.py`: 9 lệnh hợp lệ, 9 lệnh bị từ chối và kiểm tra bản đồ đều PASS.
- `check_route_planning.py`: 6 test đều PASS.
- `check_install.py`: import Python, package ROS, map/world, cấu hình RViz và
  tham số launch đều PASS; Gazebo 6.18.0.

Lượt này không build lại Docker image, không tải model và không chạy lại điều
hướng/thu micro. Kết quả thử nghiệm chuyển động và ASR được ghi ở các mục trước.
