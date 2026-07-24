# KNOWN ISSUES & LIMITATIONS REGISTER

*Danh sách vấn đề của bài toán tối ưu vị trí trạm sạc VGreen. Đây là **nguồn chân lý để monitor & xử lý** — mỗi vấn đề có: mức độ, phạm vi xử lý trong internship, chủ sở hữu, ngày xử lý, hướng khắc phục, trạng thái. Cập nhật cột **Trạng thái** + **processed_date** khi tiến triển.*

## 1. Chú giải

- **Nhóm:**
  - `A` Demand Target & Data Science
  - `B` Spatial Geometry & Siting Mechanics
  - `C` Master Data & Entity Resolution
  - `D` Covariates & Feature Engineering
  - `E` Data Quality & Cleaning (di chuyển từ `data-layer-overview.md §7` — xem [Task-1 rationale](#0-nguồn-gộp))
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
- **Ngày giải quyết:** ngày chốt/đóng vấn đề (ISO `YYYY-MM-DD`); `—` nếu chưa xử lý.

---

## 2. Bảng tổng hợp vấn đề (đã gộp)

| ID               | Nhóm | Vấn đề                                                                                                                                    | Mức | Phạm vi              | Owner       | ngày giải quyết   | Trạng thái | Ghi chú                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---- | --------------------- | ----------- | -------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P1**     | A     | Heuristic weights thay vì fit model có giám sát trên 18,6M occupancy                                                                    | 🟠   | SIMPLIFY              | Kỳ         | —                   | ☐           | - Công thức tính demand proxy hiện không dùng occupancy polling dataset.<br />- Heuristic weights thủ công thay vì fit model qua ML.                                                                                                                                                                                                                                                               |
| **P2**     | A     | Selection bias: chỉ quan sát demand nơi**đã có** trạm                                                                           | ⚪   | DOC → FUTURE         | Giang/Kỳ   | —                   | ⊘           | Accepted limitation.                                                                                                                                                                                                                                                                                                                                                                                        |
| **P3**     | A     | Cửa sổ 7,15 ngày → bỏ qua mùa vụ/lễ/thời tiết                                                                                      | ⚪   | DOC → FUTURE         | Giang       | —                   | ⊘           | Accepted limitation.                                                                                                                                                                                                                                                                                                                                                                                        |
| **P4**     | B     | **Bán kính suy biến:** R = 500 m < khoảng cách tâm 2 ô kề (0,98 km) → MCLP = sort top-p; 500 m không phải catchment lái xe | 🔴   | **FIX (chặn)** | Kỳ + Giang | **2026-07-24** | ☑           | Lỗi ở**tỷ lệ** `R/d` (d = khoảng cách tâm 2 ô H3 kề). Cấu hình cũ `R=500 m / d=0,98 km` → tỷ lệ **0,51 < 1** ⇒ mỗi trạm chỉ phủ ô chứa nó ⇒ suy biến `sort top-p`. Giữ **H3 res 8**, chốt **R = 3 km** (tỷ lệ 3,07) + quét {1,5 · 2 · 3 · 5} km.                                                                                             |
| **P5**     | B     | Candidate set chưa định nghĩa; thiếu lọc land-use (hồ/núi/đất cấm)                                                                | 🟡   | SIMPLIFY              | Giang       | **2026-07-24** | ☑           | **Đã xử lý 24/07.** Candidate lai (điểm thực, ≤1/ô H3) phân tầng T0–T4 + bộ lọc `buildable_h3` (ESA WorldCover 10m + OSM cấm + road access) + QA gate 5 cổng. Code `data/landuse/` + `features/build_candidates.py`. MVP Hà Nội: 1.672 candidate, mọi gate PASS. Xem [candidate-sites.md](data-layer/candidate-sites.md).                                                     |
| **P6**     | C     | Trùng PK (236 dòng); số trạm lệch giữa doc/report (28.417 vs 28.625)                                                                   | 🟡   | FIX                   | Giang       | —                   | ☐           | Dữ liệu cào từ nhiều nguồn bị trùng ID + số liệu báo cáo cũ không thống nhất. Xem**E-DQ2** (dedup chéo nguồn).                                                                                                                                                                                                                                                                      |
| **P7**     | C     | Nhiễm xe máy điện: dùng power tier chung thay vì chuẩn cắm (CCS2)                                                                    | 🟠   | FIX                   | Giang       | **2026-07-24** | ☑           | **Đã xử lý 24/07.** Dùng chuẩn cắm chính thức (`official_connectors.standard`) thay power tier: thêm `connector_standard`/`vehicle_class`, sửa **1.588 connector 20-22 kW** bị gán nhầm AC→**DC CCS2** (1.079 trạm). 100% connector khớp là chuẩn ô tô (CCS2/Type2) ⇒ không còn nhiễm 2 bánh sau lọc BSS; 7 trạm evcs-only gắn cờ `STD_UNVERIFIED`. |
| **P8**     | C     | Thiếu lọc trạng thái vận hành & access (private vs public)                                                                             | 🟡   | FIX                   | Giang       | —                   | ☐           | ≡ §7#5 cũ (`status` 72 null, `is_public` 80 null). Quyết định tường minh, **không** default ngầm.                                                                                                                                                                                                                                                                                       |
| **P9**     | C     | Lệch thời điểm giữa các đợt crawl (occupancy 2026 · WorldPop 2020 · OSM)                                                           | 🟡   | FIX + DOC             | Giang       | —                   | ☐           | Khóa mốc cung chính thức**2026-07-20**, telemetry occupancy **07/2026**.                                                                                                                                                                                                                                                                                                                    |
| **P10**    | D     | WorldPop 2020 lỗi thời (6 năm)                                                                                                            | 🟡   | DOC                   | Giang       | —                   | ⊘           | Accepted limitation. Dùng WorldPop spatial ratio + GSO province scaling.                                                                                                                                                                                                                                                                                                                                   |
| **P11**    | D     | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ)                                                                | 🟠   | SIMPLIFY              | Giang       | —                   | ☐           | Demand Proxy A/B với POI/Roads + Meta RWI wealth index (robustness r=0,91).                                                                                                                                                                                                                                                                                                                                |
| **E-DQ1**  | E     | Toạ độ placeholder / trùng khít                                                                                                         | 🟠   | FIX                   | Giang       | —                   | ☐           | `lat`/`lng`: 274 toạ độ trùng khít; 35 trạm chồng 1 điểm HCM nhưng địa chỉ ở HN/Bắc Ninh → phủ ảo. Flag `DUP_COORD` / `COORD_ADDR_MISMATCH`. Kế hoạch: [overview §8 bước 4](data-layer/overview.md).                                                                                                                                                                          |
| **E-DQ2**  | E     | Trùng chéo nguồn (evcs vs official)                                                                                                       | 🟠   | FIX                   | Giang       | —                   | ☐           | Cùng 1 trạm lệch toạ độ nhẹ → đếm trùng cung. Dedup không gian bằng H3,**không** cộng dồn công suất. Liên quan **P6**. [overview §8 bước 3](data-layer/overview.md).                                                                                                                                                                                                       |
| **E-DQ3**  | E     | Cột admin trống (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`)                                                 | 🟡   | FIX                   | Giang       | —                   | ☐           | null 100% ở cả`stations` & `demand_h3`. Spatial-join enrich, **kiểm vintage ranh giới 2025** (VN sáp nhập tỉnh, bỏ cấp huyện). [overview §8 bước 8](data-layer/overview.md).                                                                                                                                                                                                          |
| **E-DQ4**  | E     | Cấu hình khuyết (`current_type`, `max_power_kw`, `total_power_kw`, `num_connectors=0`)                                            | 🟡   | FIX                   | Giang       | —                   | ☐           | 282 trạm không có dòng connector. Backfill từ connector rồi flag`INCOMPLETE_CONFIG` (giữ làm điểm coverage, loại khỏi charger-config). [overview §8 bước 6](data-layer/overview.md).                                                                                                                                                                                                        |
| **E-DQ5**  | E     | Trường`operator` bẩn                                                                                                                    | 🟡   | FIX                   | Giang       | —                   | ☐           | Lẫn nhãn không phải operator ("Tiền mặt", "Hỗ trợ cộng đồng"). Vocab kiểm soát + cờ VGreen sạch.[overview §8 bước 7](data-layer/overview.md).                                                                                                                                                                                                                                              |
| **E-DQ6**  | E     | Text tự do bẩn (`name`, `address`)                                                                                                     | ⚪   | SIMPLIFY              | Giang       | —                   | ☐           | Casing lộn xộn, tên operator nằm trong name. Chuẩn hoá, giữ bản`*_raw`. [overview §8 bước 7](data-layer/overview.md).                                                                                                                                                                                                                                                                           |
| **E-DQ7**  | E     | Cầu chưa audit (`pop`, POI/road)                                                                                                         | 🟠   | FIX                   | Giang       | —                   | ☐           | Tổng pop khớp ✓ nhưng**phân bố không gian**/POI chưa kiểm. Hồi quy tổng cấp xã vs **GSO**; kiểm bias OSM. Liên quan **P1/P11** (demand = hàm mục tiêu → rủi ro cao nhất). [overview §8 bước 5](data-layer/overview.md).                                                                                                                                            |
| **E-DQ8**  | E     | Dân cư không có đường (`pop>0 & road=0`)                                                                                            | 🟡   | FIX                   | Giang       | —                   | ☐           | 6.352 ô`pop>0` mà `road=0`. Flag, loại khỏi trọng số road. [overview §8 bước 5](data-layer/overview.md).                                                                                                                                                                                                                                                                                        |
| **E-DQ9**  | E     | Grid toàn quốc vs MVP 1 thành phố (`demand_h3` toàn bảng)                                                                            | 🟡   | SIMPLIFY              | Giang       | —                   | ☐           | 164k ô rỗng, không có admin để cắt. Clip về MVP city + buffer 5 km, đếm lại lỗi trên subset.[overview §8 bước 2](data-layer/overview.md).                                                                                                                                                                                                                                                    |
| **E-DQ10** | E     | Chưa freeze snapshot / provenance                                                                                                           | 🟡   | FIX                   | Giang       | —                   | ☐           | Nguồn raw chưa hash / ghi ngày crawl. Freeze + hash raw, ghi ngày crawl.[overview §8 bước 1](data-layer/overview.md).                                                                                                                                                                                                                                                                                 |

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
  (c) candidate là điểm hay ô H3. Giải chi tiết ở **[candidate-sites.md](data-layer/candidate-sites.md)**; tóm tắt:

  **(c) Granularity — mô hình lai.** Với `R = 3 km`, `d = 0,98 km` → `R/d = 3,07`, hai điểm bất kỳ
  trong cùng ô H3 phủ gần như y hệt tập ô demand → giữ nhiều điểm/ô gây MCLP **tie-degenerate**
  (biến thể ẩn của **P4**). Chốt: candidate = **một điểm thực** (giữ toạ độ để explainability),
  nhưng **tối đa 1 candidate/ô H3 res 8**; coverage tính theo `h3_r8`.

  **(a) Sinh candidate — phân tầng anchor.** T0 trạm hiện có (brownfield, `is_existing=True` —
  ràng buộc thiết kế: incumbent bắt buộc mở) · T1 `parking`/`fuel` · T2 `mall`/`retail`/`apartments` ·
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
  OSM exclusion quadtree + STRtree, substation-dist BallTree, buildable numpy.

  **Limitation (`DOC`):** quy hoạch sử dụng đất chính thức VN không public → WorldCover/OSM chỉ là
  **proxy** (điểm "buildable" vẫn có thể bị cấm theo quy hoạch địa phương); WorldCover 2021 vs 2026
  (lệch vintage như **P10**); bias đô thị OSM giảm nhẹ bằng T4 nhưng không khử; candidate `SYNTHETIC`
  (T4) **không** trình bày như khuyến nghị chốt — phải kèm cảnh báo khảo sát thực địa.

### C. Master Data & Entity Resolution

**P6 (Trùng PK & Số trạm lệch giữa các báo cáo):**

**P7 (Nhiễm xe máy điện - dùng chung power tier)** — *chốt 24/07/2026

**Chẩn đoán:** Gốc vấn đề là **nguồn tín hiệu**: `evse_powers` của evcs.vn
chỉ lộ **công suất (W)**, *không* lộ chuẩn cắm. Code cũ suy `AC/DC` từ một ngưỡng power tier
(`AC_MAX_W = 25 kW`) → hai hệ quả:

1. **Sai AC/DC ở dải 20-22 kW.** Đối chiếu registry chính thức VinFast cho thấy **20/22 kW
   là DC CCS2**, không phải AC. Ngưỡng 25 kW gán nhầm **1.588 connector (1.079 trạm)** thành AC.
2. **Không tách được xe máy/ô tô bằng công suất**

**Cách xử lý - chuẩn cắm là sự thật, không phải power tier.** `official_connectors.standard`
lộ chuẩn cắm IEC: `IEC_62196_T2_COMBO` = **CCS2**, `IEC_62196_T2` = **Type2**. Join theo
`(station_code, power_kw)` khớp **100%** (24.406/24.415 connector). Thêm 2 cột:

- `connectors.connector_standard` ∈ {`CCS2`, `TYPE2`, `UNKNOWN`}
- `connectors.vehicle_class` + roll-up `stations.vehicle_class` ∈ {`CAR`, `UNVERIFIED`, `UNKNOWN`}

`current_type` giờ **suy từ `power_type` chính thức** (AC/DC/MIXED), không từ ngưỡng kW nữa.

**Kết quả.** Sau khi lọc BSS (9.118 trạm đổi pin — hạ tầng 2 bánh thật), **100% connector khớp official đều là chuẩn ô tô** (CCS2 8.641 · Type2 15.765)

**Limitation (`DOC`):** chuẩn cắm chỉ xác minh được cho trạm khớp registry VinFast

* **P8 (Lọc trạng thái vận hành & access Private vs Public):**
* **P9 (Lệch thời điểm giữa các đợt cào dữ liệu):**

  Khóa cố định mốc thời điểm cung sạc chính thức là **20/07/2026** và dữ liệu telemetry occupancy **07/2026**.



### D. Covariates & Feature Engineering

* **P10 (WorldPop 2020 lỗi thời 6 năm):**

  * Thừa nhận hạn chế (`DOC`).
  * **Hiệu chỉnh Pha 5:** Kết hợp WorldPop với số liệu dân số chính thức mới nhất của Tổng cục Thống kê (GSO) cấp tỉnh để tính toán chỉ số `coverage_pop` (% dân số được phủ trạm sạc thực tế).
* **P11 (Model tổng dân số vs Mật độ sở hữu ô tô):**

  * Giả thuyết dữ liêụ mật độ dân số chính là dữ liệu mật độ sở hữu ô tô

### E. Data Quality & Cleaning (từ `data-layer-overview.md §7–§8`)

* Toàn bộ nhóm E chia sẻ **kế hoạch làm sạch có thứ tự** ở [data-layer-overview.md §8](data-layer/overview.md)
  — mỗi bước đã tham chiếu ID `E-DQ*` tương ứng. Nguyên tắc chung: **flag dòng, không xoá**; đối soát
  `input = output + quarantined + merged` ở mọi bước.
