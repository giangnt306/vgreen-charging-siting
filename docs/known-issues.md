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
| **P1** | Heuristic weights thay vì fit model có giám sát trên 18,6M occupancy | ✅      | 🟠   | SIMPLIFY      | Kỳ       | ☐           | - Công thức tính demand proxy hiện không sử dụng occupancy polling dataset.<br />- Heuristic weights thủ công thay vì fit model thông qua ML |
| **P2** | Selection bias: chỉ quan sát demand nơi**đã có** trạm        | ✅      | ⚪   | DOC → FUTURE | Giang/Kỳ | ⊘           |                                                                                                                                                            |
| **P3** | Cửa sổ 7,15 ngày → bỏ qua mùa vụ/lễ/thời tiết                   | ✅      | ⚪   | DOC → FUTURE | Giang     | ⊘           |                                                                                                                                                            |

### B. Spatial Geometry & Siting Mechanics

| ID           | Vấn đề                                                                                                                                                                   | Verdict | Mức | Phạm vi              | Owner       | Trạng thái | Ghi chú                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ---- | --------------------- | ----------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P4** | **- Bán kính suy biến:** R = 500 m < khoảng cách tâm 2 ô kề nhau (0,98 km) → MCLP = sort top-p<br />- 500 m không phải khoảng cách đo đạc cho xe hơi | ✅      | 🔴   | **FIX (chặn)** | Kỳ + Giang | ☑           | Lỗi nằm ở**tỷ lệ** `R / d` (d = khoảng cách tâm 2 ô H3 kề nhau), không phải ở R hay ở lưới riêng lẻ. Cấu hình cũ `R=500 m / d=0,98 km` → tỷ lệ **0,51 < 1** ⇒ mỗi trạm chỉ phủ đúng ô chứa nó ⇒ bài toán suy biến thành "chọn các ô đông nhất từ trên xuống" (`sort top-p`). Ngoài ra 500 m là bán kính **đi bộ**, không phải catchment lái xe.<br /> giữ lưới **H3 res 8**, chốt **R = 3 km** (tỷ lệ 3,07) + quét {1,5 · 2 · 3 · 5} km.  |
| **P5** | Candidate set chưa định nghĩa; thiếu lọc land-use (hồ/núi/đất cấm)                                                                                               | ✅      | 🟡   | SIMPLIFY              | Giang       | ☑           | **Đã xử lý 24/07.** Candidate lai (điểm thực, ≤1/ô H3) phân tầng T0–T4 + bộ lọc khả thi `buildable_h3` (ESA WorldCover 10m + OSM cấm + road access) + QA gate 5 cổng. Code `data/landuse/` + `features/build_candidates.py`. Đã chạy MVP Hà Nội: 1.672 candidate, mọi gate PASS. Xem [candidate-sites.md](candidate-sites.md).                                                                                                                                                                                                          |

### C. Master Data & Entity Resolution

| ID           | Vấn đề                                                                          | Verdict | Mức | Phạm vi  | Owner | Trạng thái | Ghi chú                                                                                                                                                                              |
| ------------ | ---------------------------------------------------------------------------------- | ------- | ---- | --------- | ----- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P6** | Trùng PK (236 dòng); số trạm lệch giữa doc/report (28.417 vs 28.625)         | ✅      | 🟡   | FIX       | Giang | ☐           | Dữ liệu trạm sạc cào từ nhiều nguồn bị trùng ID (cùng 1 trạm nhưng ghi nhận nhiều lần) và số liệu trong các báo cáo cũ không thống nhất (28.417 vs 28.625). |
| **P7** | Nhiễm xe máy điện: dùng power tier chung thay vì chuẩn cắm (CCS2)          | ✅      | 🟠   | FIX       | Giang | ☐           | Xe máy và ô tô cùng dùng loại sạc AC nhưng với công suất khác nhau                                                                                                      |
| **P8** | Thiếu lọc trạng thái vận hành & access (private vs public)                   | ✅      | 🟡   | FIX       | Giang | ☐           |                                                                                                                                                                                       |
| **P9** | Lệch thời điểm giữa các đợt crawl (occupancy 2026 · WorldPop 2020 · OSM) | ✅      | 🟡   | FIX + DOC | Giang | ☐           |                                                                                                                                                                                       |

### D. Covariates & Feature Engineering

| ID            | Vấn đề                                                                     | Verdict | Mức | Phạm vi | Owner | Trạng thái | Ghi chú                                                                     |
| ------------- | ----------------------------------------------------------------------------- | ------- | ---- | -------- | ----- | ------------ | ---------------------------------------------------------------------------- |
| **P10** | WorldPop 2020 lỗi thời (6 năm)                                             | ✅      | 🟡   | DOC      | Giang | ⊘           | Accepted limitation. Dùng WorldPop spatial ratio + GSO province scaling.    |
| **P11** | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ) | ✅      | 🟠   | SIMPLIFY | Giang | ☐           | Demand Proxy A/B với POI/Roads + Meta RWI wealth index (robustness r=0.91). |

---

## 3. Bộ giải pháp triển khai

### A. Demand Target & Data Science

* **P1 (Heuristic weights vs Fit model 18,6M occupancy):**

  * * **Hiện tại (Sprint 1–3):** Dùng 2 công thức Proxy A & B khác nhau để thử nghiệm. Kết quả Pha 3 & 4 cho thấy 2 công thức này cho ra gợi ý vị trí đặt trạm tương đồng tới **91%** ($r = 0.91$), chứng minh công thức heuristic đã rất ổn định.
    * **Lộ trình nâng cấp (D2 / Track A2):** Dùng 18,6M lượt sạc thực tế từ `evcs_vn` để chạy mô hình hồi quy (spatial CV) cân chỉnh lại trọng số.
    * **Thẩm định Pha 5 (Figure V3):** Đã kiểm chứng độ tương quan Spearman ($\rho$) giữa điểm nhu cầu tự tính và số lượt sạc thực tế tại 4 TP lõi để đo lường độ tin cậy.

### B. Spatial Geometry & Siting Mechanics

* **P4 (Bán kính suy biến & không phù hợp với ô tô)** — *chốt 24/07/2026*

  **Chẩn đoán:** lỗi nằm ở **tỷ lệ** giữa bán kính phục vụ và độ mịn lưới, không phải ở một trong hai:

  $$
  \text{tỷ lệ} = \frac{R}{d}, \quad d = \text{khoảng cách giữa tâm 2 ô H3 kề nhau}
  $$

  Tỷ lệ < 1 ⇒ mỗi trạm chỉ phủ đúng ô chứa nó ⇒ mọi trạm trong cùng 1 ô là như nhau ⇒ MCLP suy biến thành
  `sort top-p`. Cấu hình cũ: `R = 500 m`, `d(res 8) = 0,98 km` → **tỷ lệ 0,51**.
  Chỉ có **2 đòn bẩy**: (i) tăng `R`, hoặc (ii) **thu nhỏ ô** (đi xuống res mịn hơn).

  * GIỮ lưới `H3 res 8`

  * Quyết định 2 — CHỐT `R = 3 km` (baseline), quét km
* **P5 (Candidate set chưa định nghĩa & thiếu lọc land-use hồ/núi/đất cấm)** — *chốt 24/07/2026*

  P5 thực chất là **3 câu hỏi độc lập**: (a) candidate sinh từ đâu, (b) điểm nào phải loại,
  (c) candidate là điểm hay ô H3. Giải chi tiết ở **[candidate-sites.md](candidate-sites.md)**; tóm tắt:

  **(c) Granularity — mô hình lai.** Với `R = 3 km`, `d = 0,98 km` → `R/d = 3,07`, hai điểm bất kỳ
  trong cùng ô H3 phủ gần như y hệt tập ô demand → giữ nhiều điểm/ô gây MCLP **tie-degenerate**
  (biến thể ẩn của **P4**). Chốt: candidate = **một điểm thực** (giữ toạ độ để explainability),
  nhưng **tối đa 1 candidate/ô H3 res 8**; coverage tính theo `h3_r8`.

  **(a) Sinh candidate — phân tầng anchor.** T0 trạm hiện có (brownfield, `is_existing=True` — thoả
  **P22** incumbent bắt buộc mở) · T1 `parking`/`fuel` · T2 `mall`/`retail`/`apartments` ·
  **T4 gap-fill tổng hợp** (ô demand cao, buildable, chưa có anchor → centroid `SYNTHETIC`).
  T4 **bắt buộc** để chống thiên vị đô thị của OSM (POI thưa ở vùng ven → nếu không có T4 thì MCLP
  không thể chọn ở đó → mâu thuẫn mục tiêu "phủ công bằng" của Nhà nước). T3 rest_area/nút giao QL
  cần road-class từ `.pbf` → để roadmap.

  **(b) Bộ lọc land-use — 2 mức, `buildable_h3`.** Nền chính **ESA WorldCover 10m v200 (CC-BY)** vì
  OSM land-use ở VN quá thưa ("không có polygon nước" ≠ đất khô). *Loại cứng:* `frac_water≥0,5` ·
  `water+wetland≥0,7` · `built_up_frac<0,05` (núi/rừng/chưa đô thị hoá) · cờ OSM
  MILITARY/PROTECTED/AIRPORT/WATER_OSM · `road_len_m≤0` (không đường vào — dùng `demand_h3` có sẵn).
  *Phạt mềm:* đất nông nghiệp (`frac_crop≥0,6`) · hạ tầng mỏng · `pop>0 & road=0` (§7 #9) ·
  khoảng cách tới `power=substation` (proxy đấu nối lưới — Nhóm 2 #3).

  **QA gate 5 cổng (đóng P5 thật, không chỉ "có file candidate"):**
  ① upper-bound coverage của toàn bộ candidate ≥ 90% demand lõi AOI (fail = candidate set chặn model) ·
  ② `|candidates| ≥ 5×p` (tỷ lệ tự do) · ③ `|candidates| ≤ 3.000` (trần giải MCLP) ·
  ④ **anti-degenerate** `unique(coverage_set)/|candidates| ≥ 0,9` (biến thể ẩn P4) ·
  ⑤ gate lưới↔bán kính `R > d` (P4).

  **Bàn giao Kỳ:** `data/processed/candidate_sites.{parquet,geojson}` — điểm chạm interop thứ 3.
  Cột `is_existing` + `capex_class` phục vụ ràng buộc ngân sách Sprint 3.

  **MVP Hà Nội (24/07):** 1.672 candidate (T0 1.411 · T1 96 · T2 54 · T4 111); 79% ô AOI buildable,
  chỉ 17% ô `pop>0` bị loại (ngưỡng `BUILT_UP_MIN` hợp lý); **mọi gate PASS**.

  **Toàn quốc (national) — đã chạy 24/07:** trên **lưới `demand_h3` quốc gia (268.404 ô)** qua `--national`
  (`make landuse-national && make candidates-national`). Đã vector hoá/scale: WorldCover 16 tile đất + stride 8,
  OSM exclusion quadtree + STRtree, substation-dist BallTree, buildable numpy (~11 s). Kết quả: 60.354 ô
  buildable (22%) · **16.793 candidate** (T0 12.856 · T1 2.133 · T2 877 · T4 927) · **5/5 QA PASS**
  (upper-bound coverage **0,913**). **Một tập candidate duy nhất toàn VN** (per-tỉnh bị chặn vì cột admin
  null 100% — §8 bước 8) → MCLP quốc gia lớn, phía model có thể cần phân rã theo vùng. ⚠️ **~9% dân số
  không phủ được** (nông thôn thưa bị `NOT_BUILT_UP` loại). Chi tiết [candidate-sites.md §11](candidate-sites.md).

  **Limitation (`DOC`):** quy hoạch sử dụng đất chính thức VN không public → WorldCover/OSM chỉ là
  **proxy** (điểm "buildable" vẫn có thể bị cấm theo quy hoạch địa phương); WorldCover 2021 vs 2026
  (lệch vintage như **P10**); bias đô thị OSM giảm nhẹ bằng T4 nhưng không khử; candidate `SYNTHETIC`
  (T4) **không** trình bày như khuyến nghị chốt — phải kèm cảnh báo khảo sát thực địa.

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
