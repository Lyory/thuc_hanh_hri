# Kiểm chứng bản sửa Gazebo và khung mặt

Cập nhật ngày 14/11/2026. Mọi bước build và chạy ROS/Python bên dưới được thực
hiện trong Docker Ubuntu 22.04.5, ROS 2 Humble, Python 3.10.12.

## Nhận diện mặt và biểu cảm

- Gói ROS build thành công; 25/25 unit test đạt.
- YuNet được đóng gói cùng project, kiểm tra SHA256 và chạy offline.
- Khung mặt lấy từ ảnh camera hiện tại, không lấy từ ảnh suy luận cũ.
- Ảnh mẫu dịch chuyển 120 px: khung YuNet dịch chuyển tương ứng, sai số dưới 8 px.
- DeepFace nhận diện được biểu cảm từ phần mặt do YuNet phát hiện.
- Webcam Integrated Webcam FHD: đọc được 30 ảnh và phát hiện mặt trong 30/30 ảnh
  ở lần thử ngày 13/11. Không lưu hoặc đưa ảnh webcam vào repository.
- Kiểm thử runtime xác nhận bỏ kết quả cũ khi mặt đổi vị trí lớn, dừng khi mất mặt,
  dừng khi camera lỗi, với cả Twist và TwistStamped.

Ảnh mẫu dùng khi thử dịch chuyển là
[img1.jpg trong DeepFace v0.0.93](https://github.com/serengil/deepface/blob/v0.0.93/tests/dataset/img1.jpg).
Kết quả trên một ảnh mẫu hoặc 30 ảnh webcam không đo được độ chính xác trong
mọi điều kiện ánh sáng, tư thế và biểu cảm.

## Gazebo và chuyển động

Đã mở Gazebo 11.10.2 với TurtleBot3 Burger trong phòng 4 × 4 m. Các tia laser
được ẩn để không che robot. Cửa sổ Gazebo và webcam được bố trí cạnh nhau.
Ảnh minh chứng: [gazebo_room.png](evidence/gazebo_room.png).

Đã phát lệnh trong mô phỏng riêng và đo `/odom`. Số liệu dưới đây tính cả
1.5 giây phanh sau khi ngừng phát lệnh, do mô hình robot có quán tính.

| Biểu cảm | Khoảng phát lệnh | Kết quả đo |
|---|---|---|
| Happy | 2 giây | Đi cung trái khoảng 0.193 m, góc +0.822 rad |
| Sad | 2 giây | Đi cung phải khoảng 0.195 m, góc −0.781 rad |
| Neutral | 1 giây | Không dịch chuyển đáng kể |
| Angry | 1 giây | Lùi khoảng 0.082 m |
| Fear | 1 giây | Tiến khoảng 0.082 m |
| Surprise | Khoảng 10.47 giây | Xoay khoảng 6.429 rad, gần một vòng |

Thời gian tiến/lùi/xoay của chương trình là điều khiển theo thời gian, chưa có
vòng phản hồi góc/quãng đường. Vì vậy góc xoay và quãng đường có sai số thực tế.

Demo mặc định dùng `--network none`, IPC riêng và ROS localhost trong container.
Đã khởi động được cả webcam và Gazebo trên desktop trong chế độ này. Kiểm tra
thêm ngày 14/11 xác nhận robot nhận `/cmd_vel` và phát `/odom` trong mạng cô lập.
Chưa kiểm chứng điều khiển TurtleBot vật lý qua LAN; chế độ `camera` dành riêng
cho trường hợp đó.
