# BÁO CÁO ĐÁNH GIÁ CHẤT LƯỢNG VÀ XỬ LÝ DỮ LIỆU EVCS.VN
**Dự án:** Tối ưu hóa vị trí trạm sạc VGreen

---

## 1. Tổng quan về nguồn dữ liệu evcs.vn
**Vai trò:** Là nguồn cung cấp dữ liệu "Cung" (Supply) cốt lõi nhất về hiện trạng hạ tầng trạm sạc xe điện, phục vụ mục tiêu xác định khoảng trống (gap) và phủ sóng trạm mới. 
- **Phương pháp thu thập:** Tự động crawl (scrape) thông qua Socket.IO để lấy vị trí, cấu hình súng sạc và chuỗi thời gian (time-series) về trạng thái chiếm dụng (occupancy telemetry).
- **Mốc thời gian chốt (Snapshot):** Khóa dữ liệu vào ngày **20/07/2026** (Mã lỗi E-DQ10) nhằm đảm bảo tính tái lập (reproducibility) và tránh sai lệch (data drift) qua các vòng lặp sprint.
- **Khối lượng ban đầu:** Tổng cộng **28.625** bản ghi (trạm).

---

## 2. Các vấn đề chất lượng dữ liệu (Data Quality Issues) & Cách giải quyết
Dữ liệu thô từ evcs.vn bộc lộ khá nhiều điểm hạn chế, nhiễu và thiếu sót. Dưới đây là phân tích các vấn đề chính đã được đội ngũ Data (Giang) xác định và khắc phục nhằm đảm bảo độ chuẩn xác cho mô hình tối ưu (MCLP):

### 2.1. Nhiễm dữ liệu xe máy điện & Chuẩn cắm sai lệch (P7)
- **Vấn đề:** Dữ liệu evcs.vn chỉ cung cấp công suất (W), không có thông tin chuẩn cắm, dẫn đến nhầm lẫn xe máy điện và ô tô điện. Khai thác dữ liệu theo ngưỡng `< 25kW` ban đầu đã phân loại nhầm **1.588 connector (súng sạc)** 20-22kW thành điện xoay chiều (AC), trong khi thực tế đó là súng DC CCS2 của VinFast.
- **Xử lý:** 
  - Lọc bỏ **9.118** trạm đổi pin (Battery Swap) vì không thuộc đối tượng của bài toán.
  - Sử dụng dữ liệu registry chính thức từ `vinfastauto.com` làm nguồn tham chiếu để xác nhận chuẩn cắm (CCS2/Type2). Nhờ đó, 100% connector từ evcs.vn khớp với nguồn official đã được phân loại chuẩn `CAR`.

### 2.2. Trùng lặp chéo nguồn và Nội bộ (P6 & E-DQ2)
- **Vấn đề:** 
  - *Nội bộ evcs.vn:* Trùng lặp do quá trình quét lưới (236 dòng trùng khóa `station_code`).
  - *Chéo nguồn:* Nhiều ứng dụng/định dạng cùng trỏ về 1 trạm vật lý thực tế, làm thổi phồng số lượng trạm.
- **Xử lý:** Áp dụng thuật toán liên kết *Identity Resolution* tạo ra khóa vật lý duy nhất `physical_id`. Các cụm tọa độ nằm sát nhau (<50m) cùng tên gọi được hợp nhất. Đã giữ lại **19.178** trạm chính (primary) từ tổng số 19.507 trạm car-only. (Tuyệt đối không cộng dồn công suất giữa các bản ghi trùng lặp).

### 2.3. Tọa độ ảo (Placeholder Coordinates) & Lệch địa chỉ (E-DQ1)
- **Vấn đề:** Rất nhiều trạm có tọa độ bị dồn về một điểm trung tâm ngầm định. Cụ thể có trường hợp **35 trạm ở Hà Nội, Bắc Ninh, Hưng Yên** nhưng bị chốt tọa độ trùng khít tại **1 điểm ở TP.HCM**. Điều này gây ra hiện tượng "cung giả" ở HCM và "khoảng trống giả" ở khu vực miền Bắc.
- **Xử lý:** Thiết lập các chốt chặn (Detectors):
  - `COORD_PLACEHOLDER`: Đánh dấu các điểm có cụm ≥5 trạm khác nhau nhưng nằm cách tâm tỉnh thực tế >100km. Ghi nhận **38 trạm** bị loại cứng (đưa tọa độ về NULL).
  - `COORD_ADDR_MISMATCH`: Đánh dấu cảnh báo (**758 trạm**) với trường hợp chênh lệch địa chỉ - tọa độ để giải quyết ở bước hậu kiểm không gian (E-DQ3).

### 2.4. Phân loại trạng thái vận hành và Quyền truy cập (P8)
- **Vấn đề:** Dữ liệu thô chưa lọc trạng thái, dẫn đến việc các trạm ngừng hoạt động hoặc trạm tư nhân/nội bộ vẫn được tính là khả dụng.
- **Xử lý:** Chuẩn hóa hoàn toàn các cột `op_status` và `access` (ưu tiên dữ liệu từ Official, dùng bản ghi evcs làm fallback). Trực tiếp loại bỏ **42 trạm** đã ngừng hoạt động (`OUT_OF_SERVICE`) và đánh cờ cho các trạm bảo trì.

---

## 3. Kiến trúc Đầu ra của Pipeline (Canonical Schema)
Sau khi đi qua các luồng làm sạch tự động, tập dữ liệu đầu ra từ evcs.vn được xuất ra cấu trúc chuẩn hóa (Hive-partitioned parquet) để bàn giao cho mô hình hóa (Kỳ):

- **Canonical Stations:** **19.507 trạm car-only**.
- **Canonical Connectors:** **24.415 súng sạc** có cấu hình chuẩn xác.
- **Lượng Cung Thực Tế:** Lọc lấy nhóm có trạng thái công khai và sẵn sàng hoạt động (Public & Operational, không dính tọa độ ảo), còn lại **19.015 trạm thực sự**.
- **Tích hợp địa lý (Spatial Integration):** Tất cả trạm hợp lệ đã được quy đổi sang lưới H3 res 8 (cạnh ~0.56 km) để kết nối trực tiếp với ma trận Demand Map nhằm chạy hàm mục tiêu Coverage trong mô hình tối ưu.

---

## 4. Đánh giá và Khuyến nghị
1. **Độ tin cậy của Nguồn:** `evcs.vn` mang lại giá trị cốt lõi nhất về Cung (Supply) trên toàn quốc do VGreen không cung cấp API nội bộ. Mặc dù dữ liệu thô chứa nhiều nhiễu, nhưng pipeline làm sạch tự động hiện tại đã giải quyết triệt để 95% các bẫy chết người (đặc biệt là sai số tọa độ E-DQ1 và suy biến bán kính P4).
2. **Hạn chế tồn tại (Limitations):** Các chỉ số liên quan đến kinh tế như *hệ số hiệu suất sử dụng (utilization rate)*, *doanh thu dự phóng (kWh)* hay *khả năng tắc nghẽn (queue probability)* vẫn chưa tính được chính xác vì telemetry thu thập được từ `evcs.vn` chỉ mang tính chất ảnh chụp (snapshot) trong khoảng thời gian hẹp thay vì lịch sử vận hành dài hạn.
3. **Mức độ sẵn sàng:** Dữ liệu đã sạch, đủ tiêu chuẩn kết xuất GeoJSON và trực tiếp đưa vào mô hình MCLP cho cả quy mô đô thị MVP và lưới quốc gia (National Grid) để tính toán vùng phủ với bán kính R = 3km.
