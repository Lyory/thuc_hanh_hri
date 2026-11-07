# Project tuần 7 độc lập

- Thư mục này là root của một project có thể clone riêng; không yêu cầu các
  thư mục week4/week5/week6 hoặc bất kỳ file nào bên ngoài project.
- Chạy và kiểm tra ROS, simulator, OpenCV và ASR trong Docker Ubuntu 22.04 /
  ROS 2 Humble. Không dùng ROS trên host để build hay chạy project.
- Dockerfile phải build được từ image công khai; không phụ thuộc image cục bộ
  như hri:humble hoặc trạng thái container trên máy tác giả.
- Khai báo dependency hệ thống trong Dockerfile, dependency Python trong
  requirements.txt. Khi bổ sung file/model/asset, đưa vào project hoặc cung cấp
  bước tải/tạo có thể tái lập; không dựa vào cache hay kết quả build cũ.
- README phải hướng dẫn từ máy mới: cài Docker/gói host, clone project, build,
  tải model, chạy mô phỏng, khởi tạo robot và nhận giọng nói. Dùng đường dẫn host
  tương đối với root project, không dùng /home/quan hoặc thư mục tuần khác.
