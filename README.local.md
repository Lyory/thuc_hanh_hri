# Máy hiện tại — Humble trong Docker, Jazzy giữ nguyên trên host

Chạy mọi lệnh từ root project trên **host**. Máy đã có image, kết quả build và
model `small`; không cài Docker lại, không build lại image hay tải model khác.
Cài mới từ GitHub: [README.md](README.md).

## 1. Chạy hằng ngày — một lệnh

```bash
bash scripts/docker.sh demo
```

Demo tự chạy Gazebo server, mở cửa sổ **Điều hướng giọng nói · A / B / C** và tự
initialize/undock. Đợi `READY: AMCL active, Nav2 active, robot undocked`.
Không chạy initialize thêm lần nữa khi dùng chế độ mặc định.

Trong cửa sổ điều khiển:

1. Chọn micro; chế độ tự chọn ưu tiên USB hoặc micro số laptop DMIC.
2. Bấm **Thu một câu (6 giây)**, đợi **Đang thu** rồi nói.
3. Xem câu trong **Bạn nói**, tuyến và trạng thái từng chặng.
4. Xem robot/đường Nav2 trên map. Bấm **Dừng robot / hủy tuyến** nếu cần.

| Nói | Đích |
|---|---|
| “Đi đến khu vực A.” | A — Phòng học bên trái |
| “Di chuyển từ khu vực A đến khu vực B.” | A trước, B sau |
| “Đi đến phòng thí nghiệm.” | B — phòng bên phải |
| “Đi đến hành lang.” | C — hành lang phía dưới |
| “Đi đến khu vực D.” | Báo không tồn tại, không gửi goal |
| “Đi từ phòng A qua hành lang C rồi đến phòng B.” | A → C → B |
| “Đi đến B rồi quay lại C.” | B → C |

Bản đồ mới 10 × 7 m, hai phòng có cửa rộng nối hành lang; nhãn A/B/C và màu vùng
hiện trên cửa sổ điều khiển và trên RViz nếu bật `rviz:=true`. Ô gửi văn bản là cách thử khi chưa có micro,
không phải kết quả nhận dạng tiếng nói.

Với nhiều điểm, Nav2 tính toàn tuyến trước khi robot khởi hành. Đường tím nét
đứt là toàn tuyến dự kiến; đường xanh là chặng hiện tại. Ô số trên map ghi thứ
tự ghé; dòng tuyến đánh dấu ✓ đã đến, ▶ đang chạy, ○ còn lại và hiện chặng 1/3,
2/3, 3/3. Robot chỉ chuyển sang điểm sau khi chặng trước thành công.

Ví dụ A → D → B bị từ chối toàn bộ. Nếu không lập được đường, robot chưa bắt
đầu tuyến. Bấm dừng để hủy cả tuyến; các điểm còn lại và preview được xóa.
Khi bật RViz, display **Route Preview** hiện toàn tuyến màu tím.

Câu dùng tên đầy đủ: **“Đi từ phòng học qua hành lang rồi đến phòng thí nghiệm.”**
Nếu Whisper nghe nhầm A/B/C, xem phần **Bạn nói** rồi thử tên chức năng; hệ thống
vẫn từ chối tên lạ, không tự ép phiên âm sai thành vùng hợp lệ.

Chỉ mở một demo. Nếu chạy lại khi phiên cũ còn mở, script sẽ báo và từ chối
chạy trùng; muốn mở lại riêng giao diện dùng `bash scripts/docker.sh panel`.

Nếu robot đứng yên dù đã có đường, xem khung chẩn đoán: vận tốc yêu cầu so với
odom, điểm LiDAR đỏ, cảnh báo bumper/giới hạn lùi và số lần Nav2 phục hồi.
Chấm đen là vị trí ước lượng, vòng cam là vị trí thật trong Gazebo. Hai dấu lệch
xa nhau cho thấy định vị đang sai. Dock thấp không lọt vào tia LiDAR đã được
đánh dấu riêng trong map để Nav2 đi vòng, không cố chạy xuyên qua nó.

## 2. Khi micro chưa nhận

Micro bạn dùng là micro tích hợp laptop, **DMIC** (hiện là thiết bị 4).
Chế độ tự chọn đã ưu tiên DMIC thay vì jack headset của đầu vào ALSA mặc định. Chọn thiết bị có nhãn DMIC trong danh sách nếu chưa nhận được giọng.
Giao diện hiện dBFS/peak, cảnh báo tín hiệu im lặng và lỗi thiết bị; kiểm tra thêm
mute trong cài đặt âm thanh host. Không mở terminal recognition đồng thời nút thu.

Muốn dùng terminal thay giao diện:

```bash
bash scripts/docker.sh recognition --list-devices
bash scripts/docker.sh recognition --model small --device N
```

Thay `N` bằng chỉ số input. Không cần dùng `--download-only` khi đã có model.

## 3. Dừng, mở lại và chạy nhẹ

Ctrl+C terminal demo, sau đó nếu muốn:

```bash
bash scripts/docker.sh stop
```

Lần sau chỉ chạy `demo`. Mặc định đã tắt cửa sổ 3D/RViz để tiết kiệm CPU/RAM. Muốn mở thêm RViz:

```bash
bash scripts/docker.sh demo rviz:=true
```

Hoàn toàn không GUI: thêm `panel:=false`. Muốn bật cả Gazebo 3D và RViz:
`bash scripts/docker.sh demo headless:=false rviz:=true` (nặng hơn; GUI Gazebo có thể lỗi render trên máy này). Nếu tự khởi tạo bằng terminal riêng,
chạy demo với `auto_initialize:=false`, rồi `bash scripts/docker.sh initialize`
đúng một lần cho robot vừa spawn. Định vị robot đã di chuyển bằng 2D Pose Estimate.

Nếu chỉ đóng bảng điều khiển mà demo còn chạy:

```bash
bash scripts/docker.sh panel
```

## 4. Chỉ chạy khi cần cập nhật

| Tình huống | Lệnh |
|---|---|
| Sửa Python hoặc launch | Dừng rồi mở lại demo |
| Sửa C++ simulator / cache CMake trỏ thư viện cũ | `bash scripts/docker.sh rebuild` |
| Sửa Dockerfile hoặc requirements | `bash scripts/docker.sh build` |
| Kiểm tra dependency, logic và cấu hình RViz | `bash scripts/docker.sh check` |
| Sửa seed hoặc alias | `bash scripts/docker.sh segment`, rồi mở lại demo |

Map PGM/YAML và world mới đã có trong project, không tải map/model/asset ngoài.
Tái tạo hình học khi sửa generator (dừng demo trước):

```bash
bash scripts/docker.sh exec python scripts/generate_demo_map.py
bash scripts/docker.sh segment
```

Build 2 job; Whisper CPU int8 với 2 luồng. Chỉ dùng model small hiện có. Không
cần SciPy, FFmpeg dòng lệnh hay bộ Fortress development đầy đủ. Giao diện dùng Qt
đã có trong Docker. ROS log/cache nằm trong `.docker-runtime/`; console Docker
xoay vòng 10 MB/file, 2 file. Core dump được tắt để tránh file crash lớn.

Log nhận dạng: `evidence/transcripts.jsonl`; điều hướng: `evidence/navigation.jsonl`.
Chi tiết thuật toán, kiểm thử và lỗi: [README.md](README.md).
Kết quả kiểm chứng: [VALIDATION.md](VALIDATION.md).
