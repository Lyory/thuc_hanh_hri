# Vật thể trong maze tuần 5

World hiện có **10 vật thể**: 3 người, 4 ghế, 1 ô tô và 2 bình chữa cháy.
Tất cả là mô hình static, có visual và collision, được lưu local để chạy offline.

| Tên trong Gazebo | Loại | x world | y world |
|---|---|---:|---:|
| `chair_goal1` | Ghế | 1.5 | -1.5 |
| `person_goal2` | Người | 3.2 | 3.2 |
| `chair_goal3` | Ghế | 6.6 | 3.2 |
| `person_near_goal1` | Người thêm gần Goal 1 | 1.7 | -3.4 |
| `person_east` | Người ở phía đông | 8.8 | 2.5 |
| `chair_north` | Ghế phía bắc | 2.8 | 4.2 |
| `chair_parking` | Ghế gần khu đỗ xe | 8.8 | -0.8 |
| `car_parking` | Ô tô Hatchback | 6.8 | -2.5 |
| `extinguisher_goal1` | Bình chữa cháy gần Goal 1 | 2.7 | -1.7 |
| `extinguisher_north` | Bình chữa cháy phía bắc | 3.5 | 4.7 |

Tọa độ trên là frame **world của Gazebo**, khác frame map của goal.
Đổi vị trí ở các thẻ `<include>` cuối `worlds/maze.sdf`.
Sau khi sửa, dừng và mở lại `localization.launch.py` để Gazebo nạp world mới;
cần thực hiện lại localization trước khi chạy navigation.

## Nguồn mô hình

- `chair`: [OpenRobotics / Chair v3](https://fuel.gazebosim.org/1.0/OpenRobotics/models/Chair/3).
- `person`: [OpenRobotics / MaleVisitorOnPhone v2](https://fuel.gazebosim.org/1.0/OpenRobotics/models/MaleVisitorOnPhone/2).
- `hatchback`: [osrf/gazebo_models — hatchback](https://github.com/osrf/gazebo_models/tree/master/hatchback).
- `fire_extinguisher`: mô hình SDF tự dựng cho bài thực hành, gồm thân đỏ, nhãn,
  đồng hồ áp suất, van, tay cầm và vòi phun.

Giữ `model.config` của nguồn để lưu tên tác giả. Mesh/texture người và ghế giữ
nguyên; URI chuyển sang local, model đặt static. Hatchback giữ nguyên kích
thước/mesh/texture, chỉnh đường dẫn texture tương đối trong MTL và bỏ dòng
`Tr` trùng với `d` để giảm cảnh báo OBJLoader.

## Navigation và YOLO

Giữ nguyên tường maze, `map.yaml`, `map.pgm` và ba goal. Các vật thể mới không
được vẽ vào map cũ; Nav2 dùng LiDAR để đưa chúng vào costmap.

YOLOv8n hiện tại có các class `person`, `chair`, `car`; khả năng phát hiện phụ
thuộc góc nhìn và ảnh mô phỏng. Model này **không có class fire extinguisher**.
Muốn nhận diện bình chữa cháy đúng tên cần đổi sang model được train cho class
đó hoặc bổ sung YOLO-World; thêm vật thể vào Gazebo không tự thêm class cho YOLO.

Kiểm tra ngày 19/10/2026: Gazebo `ign sdf -k` báo `Valid`; các URI/texture local
hợp lệ; bounding box collision của 10 vật thể không chồng nhau hoặc chồng tường.
Ba goal còn liên thông sau khi chừa khoảng trống 0,35 m theo kiểm tra hình học
bảo thủ trên map kết hợp bounding box vật thể. Chưa chạy lại toàn bộ Nav2 với
world 10 vật thể; video và lượt 3/3 goal ngày 14/10 thuộc world trước khi thêm.
