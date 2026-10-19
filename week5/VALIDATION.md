# Kết quả kiểm thử tuần 5

Kiểm thử thực tế trong container `hri`, Ubuntu 22.04 / ROS 2 Humble, ngày 14/10/2026 (Asia/Bangkok).

Lượt cuối chạy `scripts/run_virtual_demo.sh` từ robot mới spawn, tự đặt initial pose, tự undock và tự gửi goal; không teleop hoặc đặt navigation goal bằng chuột.

| Goal trong frame map | x | y | yaw rad | Kết quả | Giây mô phỏng | Giây thực |
|---|---:|---:|---:|---|---:|---:|
| Goal 1 | -2.0 | 0.0 | 1.57079632679 | SUCCEEDED | 9.24 | 27.51 |
| Goal 2 | -2.0 | -3.0 | 3.14159265359 | SUCCEEDED | 17.3 | 58.58 |
| Goal 3 | -6.0 | -2.0 | -1.57079632679 | SUCCEEDED | 20.3 | 62.47 |

YOLOv8n nhận ảnh thật từ `/oakd/rgb/preview/image_raw`, cv_bridge BGR, xuất `/yolo/annotated` và cửa sổ OpenCV. Lượt cuối ghi nhận `person` confidence tới 91%, `chair` tới 86%. Có một số dự đoán sai class trong ảnh mô phỏng; giữ nguyên tất cả kết quả trong JSONL.

Theo dõi 4883 message hazard trong lượt chạy: 0 message bumper, 0 message stall. Đây là kết quả cảm biến, không phải kiểm chứng hình học cho mọi dạng tiếp xúc. Median của tỷ lệ endpoint LiDAR cách vật cản trên map dưới 15 cm là 94.8%; median khoảng cách endpoint là 0.05 m. Các vật thể mới không nằm trong map cũ nên một số điểm LiDAR không trùng map là bình thường.

Map YAML/PGM giống từng byte với tuần 4. XML của ground_plane/border/obstacles giữ nguyên. Cả ba goal nằm trong vùng trống liên thông sau khi chừa margin 0,35 m trên map. Python compile, bash syntax, YAML/XML và launch arguments đã kiểm tra.

Cấu hình cuối dùng LiDAR costmap; không dùng lớp camera depth kế thừa vì tạo vật cản giả và đường vòng lớn khi thử. Nav2 controller 10 Hz, costmap 3 Hz, BT 20 Hz, action ACK timeout 1000 ms và lifecycle bond timeout 30 s. Tuyến goal cuối tránh dock thấp.

Video: `evidence/week5_demo.mp4` (RViz + RGB + camera YOLO trên Xvfb riêng). Dữ liệu: `evidence/navigation.csv`, `evidence/detections.jsonl`, `evidence/monitor-summary.json`, `evidence/telemetry.jsonl`. Lượt thất bại giữ riêng trong `evidence/failed_run/` và `evidence/failed_run_2/`, không dùng làm bằng chứng lượt đạt.

Sau lượt cuối, script tự dừng ROS/Gazebo/YOLO/Xvfb và hoàn tất MP4. Container `hri` giữ trạng thái đang chạy để có thể mở shell chạy lại.

## Cập nhật vật thể ngày 19/10/2026

World hiện có 10 vật thể (3 người, 4 ghế, 1 ô tô, 2 bình chữa cháy). Đã kiểm tra
SDF hợp lệ, texture/URI local, không chồng bounding box collision với tường
và ba goal còn liên thông với khoảng trống kiểm tra 0,35 m. Chưa chạy lại trọn
chuỗi navigation với world mới; video và số liệu ngày 14/10 ở trên thuộc world
cũ. Xem `models/README.md` để biết tọa độ và giới hạn class YOLO.
