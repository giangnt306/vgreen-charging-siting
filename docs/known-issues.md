
# KNOWN ISSUES & LIMITATIONS REGISTER

*Danh sách vấn đề của bài toán tối ưu vị trí trạm sạc VGreen. Đây là **nguồn chân lý để monitor & xử lý** — mỗi vấn đề có: kết luận (verdict), mức độ, phạm vi xử lý trong internship, chủ sở hữu, hướng khắc phục, trạng thái. Cập nhật cột **Trạng thái** khi tiến triển.*

## 1. Chú giải

- **Verdict:**
  - ✅ Confirmed
  - ◑ Confirmed-partial (đúng nhưng đã xử lý một phần / trên roadmap)
  - ⚠️ Needs-clarification (yếu / phụ thuộc cách phát biểu)
- **Mức độ:** 🔴 Fatal · 🟠 High · 🟡 Medium · ⚪ Low
- **Phạm vi (trong 3 sprint):**
  - `FIX` bắt buộc sửa
  - `SIMPLIFY` sửa bản rút gọn cho MVP
  - `DOC` không sửa được trong scope → **phải ghi rõ là limitation**
  - `ROADMAP` đã có trong kế hoạch
  - `FUTURE` ngoài quy trình hiện tại
- **Trạng thái:**
  - ☐ Open
  - ◐ In-progress/Partial
  - ☑ Done
  - ⊘ Won't-fix (chấp nhận & document)

---

## 2. Bảng tổng hợp vấn đề

### A. Demand Target & Data Science

| ID           | Vấn đề                                                                 | Verdict | Mức | Phạm vi      | Owner     | Trạng thái | Ghi chú                                                                                                                                                   |
| ------------ | ------------------------------------------------------------------------- | ------- | ---- | ------------- | --------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P1** | Heuristic weights thay vì fit model có giám sát trên 18,6M occupancy | ✅      | 🟠   | SIMPLIFY      | Giang     | ☑           | - Công thức tính demand proxy hiện không sử dụng occupancy polling dataset.<br />- Heuristic weights thủ công thay vì fit model thông qua ML |
| **P2** | Selection bias: chỉ quan sát demand nơi**đã có** trạm        | ✅      | ⚪   | DOC → FUTURE | Giang/Kỳ | ⊘           |                                                                                                                                                            |
| **P3** | Cửa sổ 7,15 ngày → bỏ qua mùa vụ/lễ/thời tiết                   | ✅      | ⚪   | DOC → FUTURE | Giang     | ⊘           |                                                                                                                                                            |

### B. Spatial Geometry & Siting Mechanics

| ID           | Vấn đề                                                                                                                                           | Verdict | Mức | Phạm vi              | Owner       | Trạng thái | Ghi chú                                                                                                                                                                                                                                                                                                                                                                    |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ---- | --------------------- | ----------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P4** | **- Bán kính suy biến:** 500 m < 800 m (tâm ô res 8) → MCLP = sort top-p<br />- 500 m không phải khoảng cách đo đạc cho xe hơi | ✅      | 🔴   | **FIX (chặn)** | Kỳ + Giang | ☑           | Mỗi ô đất H3 res 8 rộng ~800m. Nếu bán kính sạc chỉ là 500m thì trạm sạc chỉ phủ đúng ô chứa nó mà không phủ sang ô bên cạnh. Bài toán tối ưu bị "hỏng" (suy biến) thành việc chỉ chọn các ô đông nhất từ trên xuống dưới (`sort top-p`). Ngoài ra, người đi ô tô điện không sạc trong bán kính đi bộ 500m. |
| **P5** | Candidate set chưa định nghĩa; thiếu lọc land-use (hồ/núi/đất cấm)                                                                       | ✅      | 🟡   | SIMPLIFY              | Giang       | ◐           |                                                                                                                                                                                                                                                                                                                                                                             |

### C. Master Data & Entity Resolution

| ID           | Vấn đề                                                                          | Verdict | Mức | Phạm vi  | Owner | Trạng thái | Ghi chú                                                                                                                                                                              |
| ------------ | ---------------------------------------------------------------------------------- | ------- | ---- | --------- | ----- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P6** | Trùng PK (236 dòng); số trạm lệch giữa doc/report (28.417 vs 28.625)         | ✅      | 🟡   | FIX       | Giang | ☑           | Dữ liệu trạm sạc cào từ nhiều nguồn bị trùng ID (cùng 1 trạm nhưng ghi nhận nhiều lần) và số liệu trong các báo cáo cũ không thống nhất (28.417 vs 28.625). |
| **P7** | Nhiễm xe máy điện: dùng power tier chung thay vì chuẩn cắm (CCS2)          | ✅      | 🟠   | FIX       | Giang | ☑           | Xe máy và ô tô cùng dùng loại sạc AC nhưng với công suất khác nhau                                                                                                      |
| **P8** | Thiếu lọc trạng thái vận hành & access (private vs public)                   | ✅      | 🟡   | FIX       | Giang | ☑           |                                                                                                                                                                                       |
| **P9** | Lệch thời điểm giữa các đợt crawl (occupancy 2026 · WorldPop 2020 · OSM) | ✅      | 🟡   | FIX + DOC | Giang | ☑           |                                                                                                                                                                                       |

### D. Covariates & Feature Engineering

| ID            | Vấn đề                                                                     | Verdict | Mức | Phạm vi | Owner | Trạng thái | Ghi chú                                                                     |
| ------------- | ----------------------------------------------------------------------------- | ------- | ---- | -------- | ----- | ------------ | ---------------------------------------------------------------------------- |
| **P10** | WorldPop 2020 lỗi thời (6 năm)                                             | ✅      | 🟡   | DOC      | Giang | ⊘           | Accepted limitation. Dùng WorldPop spatial ratio + GSO province scaling.    |
| **P11** | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ) | ✅      | 🟠   | SIMPLIFY | Giang | ☑           | Demand Proxy A/B với POI/Roads + Meta RWI wealth index (robustness r=0.91). |

---

## 3. Bộ giải pháp triển khai

### A. Demand Target & Data Science

* **P1 (Heuristic weights vs Fit model 18,6M occupancy):**

  * * **Hiện tại (Sprint 1–3):** Dùng 2 công thức Proxy A & B khác nhau để thử nghiệm. Kết quả Pha 3 & 4 cho thấy 2 công thức này cho ra gợi ý vị trí đặt trạm tương đồng tới **91%** ($r = 0.91$), chứng minh công thức heuristic đã rất ổn định.
    * **Lộ trình nâng cấp (D2 / Track A2):** Dùng 18,6M lượt sạc thực tế từ `evcs_vn` để chạy mô hình hồi quy (spatial CV) cân chỉnh lại trọng số.
    * **Thẩm định Pha 5 (Figure V3):** Đã kiểm chứng độ tương quan Spearman ($\rho$) giữa điểm nhu cầu tự tính và số lượt sạc thực tế tại 4 TP lõi để đo lường độ tin cậy.

### B. Spatial Geometry & Siting Mechanics

* **P4 (Bán kính suy biến 500m & không phù hợp với ô tô)**

  * Chuyển bán kính phục vụ $R$ sang khoảng cách lái xe ô tô đô thị: **1.5 km, 2 km và 3 km**.
* **P5 (Candidate set chưa định nghĩa & thiếu lọc land-use hồ/núi/đất cấm):**

### C. Master Data & Entity Resolution

* **P6 (Trùng PK & Số trạm lệch giữa các báo cáo):**
* **P7 (Nhiễm xe máy điện — dùng chung power tier):**
* **P8 (Lọc trạng thái vận hành & access Private vs Public):**
* **P9 (Lệch thời điểm giữa các đợt cào dữ liệu):**

  * Khóa cố định mốc thời điểm cung sạc chính thức là **20/07/2026** và dữ liệu telemetry occupancy **07/2026**.

### D. Covariates & Feature Engineering

* **P10 (WorldPop 2020 lỗi thời 6 năm):**

  * Thừa nhận hạn chế (`DOC`). 
  * **Hiệu chỉnh Pha 5:** Kết hợp WorldPop với số liệu dân số chính thức mới nhất của Tổng cục Thống kê (GSO) cấp tỉnh để tính toán chỉ số `coverage_pop` (% dân số được phủ trạm sạc thực tế).
* **P11 (Model tổng dân số vs Mật độ sở hữu ô tô):**

  * Giả thuyết dữ liêụ mật độ dân số chính là dữ liệu mật độ sở hữu ô tô
