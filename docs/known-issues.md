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

| ID               | Nhóm | Vấn đề                                                                                                                                    | Mức | Phạm vi              | Owner       | ngày giải quyết   | Trạng thái |
| ---------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---- | --------------------- | ----------- | -------------------- | ------------ |
| **P1**     | A     | Heuristic weights thay vì fit model có giám sát trên 18,6M occupancy                                                                    | 🟠   | SIMPLIFY              | Kỳ         | —                   | ☐           |
| **P2**     | A     | Selection bias: chỉ quan sát demand nơi**đã có** trạm                                                                           | ⚪   | DOC → FUTURE         | Giang/Kỳ   | —                   | ⊘           |
| **P3**     | A     | Cửa sổ 7,15 ngày → bỏ qua mùa vụ/lễ/thời tiết                                                                                      | ⚪   | DOC → FUTURE         | Giang       | —                   | ⊘           |
| **P4**     | B     | **Bán kính suy biến:** R = 500 m < khoảng cách tâm 2 ô kề (0,98 km) → MCLP = sort top-p; 500 m không phải catchment lái xe | 🔴   | **FIX (chặn)** | Kỳ + Giang | **2026-07-24** | ☑           |
| **P5**     | B     | Candidate set chưa định nghĩa; thiếu lọc land-use (hồ/núi/đất cấm)                                                                | 🟡   | SIMPLIFY              | Giang       | **2026-07-24** | ☑           |
| **P6**     | C     | Trùng PK (236 dòng); số trạm lệch giữa doc/report (28.417 vs 28.625)                                                                   | 🟡   | FIX                   | Giang       | **2026-07-24** | ☑           |
| **P7**     | C     | Nhiễm xe máy điện: dùng power tier chung thay vì chuẩn cắm (CCS2)                                                                    | 🟠   | FIX                   | Giang       | **2026-07-24** | ☑           |
| **P8**     | C     | Thiếu lọc trạng thái vận hành & access (private vs public)                                                                             | 🟡   | FIX                   | Giang       | **2026-07-27** | ☑           |
| **P9**     | C     | Lệch thời điểm giữa các đợt crawl (occupancy 2026 · WorldPop 2020 · OSM)                                                           | 🟡   | FIX + DOC             | Giang       | —                   | ☐           |
| **P10**    | D     | WorldPop 2020 lỗi thời (6 năm)                                                                                                            | 🟡   | DOC                   | Giang       | —                   | ⊘           |
| **P11**    | D     | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ)                                                                | 🟠   | SIMPLIFY              | Giang       | —                   | ☐           |
| **E-DQ10** | E     | Chưa freeze snapshot / provenance                                                                                                           | 🟡   | FIX                   | Giang       | **2026-07-27** | ☑           |
| **E-DQ9**  | E     | Grid toàn quốc vs MVP 1 thành phố (`demand_h3` toàn bảng)                                                                            | 🟡   | SIMPLIFY              | Giang       | —                   | ☐           |
| **E-DQ2**  | E     | Trùng chéo nguồn (evcs vs official)                                                                                                       | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ1**  | E     | Toạ độ placeholder / trùng khít                                                                                                         | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ7**  | E     | Cầu chưa audit (`pop`, POI/road)                                                                                                         | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ8**  | E     | Dân cư không có đường (`pop>0 & road=0`)                                                                                            | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ4**  | E     | Cấu hình khuyết (`current_type`, `max_power_kw`, `total_power_kw`, `num_connectors=0`)                                            | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ5**  | E     | Trường`operator` bẩn                                                                                                                    | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ6**  | E     | Text tự do bẩn (`name`, `address`)                                                                                                     | ⚪   | SIMPLIFY              | Giang       | —                   | ☐           |
| **E-DQ3**  | E     | Cột admin trống (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`)                                                 | 🟡   | FIX                   | Giang       | —                   | ☐           |

---

## 3. Bộ giải pháp triển khai

### A. Demand Target & Data Science

#### P1 — Heuristic weights vs fit model 18,6M occupancy

`🟠 SIMPLIFY · ☐ Open · Owner: Kỳ`

- **Hiện tại (Sprint 1–3):** Dùng 2 công thức Proxy A & B khác nhau để thử nghiệm. Kết quả Pha 3 & 4 cho thấy 2 công thức này cho ra gợi ý vị trí đặt trạm tương đồng tới **91%** ($r = 0.91$), chứng minh công thức heuristic đã rất ổn định.
- **Lộ trình nâng cấp (D2 / Track A2):** Dùng 18,6M lượt sạc thực tế từ `evcs_vn` để chạy mô hình hồi quy (spatial CV) cân chỉnh lại trọng số.
- **Thẩm định Pha 5 (Figure V3):** Đã kiểm chứng độ tương quan Spearman ($\rho$) giữa điểm nhu cầu tự tính và số lượt sạc thực tế tại 4 TP lõi để đo lường độ tin cậy.

### B. Spatial Geometry & Siting Mechanics

#### P4 — Bán kính suy biến & không phù hợp với ô tô

`🔴 FIX (chặn) · ☑ chốt 2026-07-24 · Owner: Kỳ + Giang`

**Chẩn đoán:** lỗi nằm ở **tỷ lệ** giữa bán kính phục vụ và độ mịn lưới, không phải ở một trong hai:

$$
\text{tỷ lệ} = \frac{R}{d}, \quad d = \text{khoảng cách giữa tâm 2 ô H3 kề nhau}
$$

Tỷ lệ < 1 ⇒ mỗi trạm chỉ phủ đúng ô chứa nó ⇒ mọi trạm trong cùng 1 ô là như nhau ⇒ MCLP suy biến thành `sort top-p`. Cấu hình cũ: `R = 500 m`, `d(res 8) = 0,98 km` → **tỷ lệ 0,51**. Chỉ có **2 đòn bẩy**: (i) tăng `R`, hoặc (ii) **thu nhỏ ô** (đi xuống res mịn hơn).

**Cách xử lý:**

- GIỮ lưới `H3 res 8`.
- CHỐT `R = 3 km` (baseline), quét dải {1,5 · 2 · 3 · 5} km.

#### P5 — Candidate set chưa định nghĩa & thiếu lọc land-use (hồ/núi/đất cấm)

`🟡 SIMPLIFY · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:** P5 thực chất là **3 câu hỏi độc lập**: (a) candidate sinh từ đâu, (b) điểm nào phải loại, (c) candidate là điểm hay ô H3. Giải chi tiết ở **[candidate-sites.md](data-layer/candidate-sites.md)**; tóm tắt bên dưới.

**Cách xử lý:**

- **(c) Granularity — mô hình lai.** Với `R = 3 km`, `d = 0,98 km` → `R/d = 3,07`, hai điểm bất kỳ trong cùng ô H3 phủ gần như y hệt tập ô demand → giữ nhiều điểm/ô gây MCLP **tie-degenerate** (biến thể ẩn của **P4**). Chốt: candidate = **một điểm thực** (giữ toạ độ để explainability), nhưng **tối đa 1 candidate/ô H3 res 8**; coverage tính theo `h3_r8`.
- **(a) Sinh candidate — phân tầng anchor.** T0 trạm hiện có (brownfield, `is_existing=True` — ràng buộc thiết kế: incumbent bắt buộc mở) · T1 `parking`/`fuel` · T2 `mall`/`retail`/`apartments` · **T4 gap-fill tổng hợp** (ô demand cao, buildable, chưa có anchor → centroid `SYNTHETIC`). T4 **bắt buộc** để chống thiên vị đô thị của OSM (POI thưa ở vùng ven → nếu không có T4 thì MCLP không thể chọn ở đó → mâu thuẫn mục tiêu "phủ công bằng" của Nhà nước). T3 rest_area/nút giao QL cần road-class từ `.pbf` → để roadmap.
- **(b) Bộ lọc land-use — 2 mức, `buildable_h3`.** Nền chính **ESA WorldCover 10m v200 (CC-BY)** vì OSM land-use ở VN quá thưa ("không có polygon nước" ≠ đất khô). *Loại cứng:* `frac_water≥0,5` · `water+wetland≥0,7` · `built_up_frac<0,05` (núi/rừng/chưa đô thị hoá) · cờ OSM MILITARY/PROTECTED/AIRPORT/WATER_OSM · `road_len_m≤0` (không đường vào — dùng `demand_h3` có sẵn). *Phạt mềm:* đất nông nghiệp (`frac_crop≥0,6`) · hạ tầng mỏng · `pop>0 & road=0` (§7 #9) · khoảng cách tới `power=substation` (proxy đấu nối lưới — Nhóm 2 #3).

**QA gate 5 cổng** (đóng P5 thật, không chỉ "có file candidate"): ① upper-bound coverage của toàn bộ candidate ≥ 90% demand lõi AOI (fail = candidate set chặn model) · ② `|candidates| ≥ 5×p` (tỷ lệ tự do) · ③ `|candidates| ≤ 3.000` (trần giải MCLP) · ④ **anti-degenerate** `unique(coverage_set)/|candidates| ≥ 0,9` (biến thể ẩn P4) · ⑤ gate lưới↔bán kính `R > d` (P4).

**Bàn giao Kỳ:** `data/processed/candidate_sites.{parquet,geojson}` — điểm chạm interop thứ 3. Cột `is_existing` + `capex_class` phục vụ ràng buộc ngân sách Sprint 3.

**Kết quả:**

- **MVP Hà Nội (24/07):** 1.672 candidate (T0 1.411 · T1 96 · T2 54 · T4 111); 79% ô AOI buildable, chỉ 17% ô `pop>0` bị loại (ngưỡng `BUILT_UP_MIN` hợp lý); **mọi gate PASS**.
- **Toàn quốc (national) — đã chạy 24/07:** trên **lưới `demand_h3` quốc gia (268.404 ô)** qua `--national` (`make landuse-national && make candidates-national`). Đã vector hoá/scale: WorldCover 16 tile đất + stride 8, OSM exclusion quadtree + STRtree, substation-dist BallTree, buildable numpy.

**Limitation (`DOC`):** quy hoạch sử dụng đất chính thức VN không public → WorldCover/OSM chỉ là **proxy** (điểm "buildable" vẫn có thể bị cấm theo quy hoạch địa phương); WorldCover 2021 vs 2026 (lệch vintage như **P10**); bias đô thị OSM giảm nhẹ bằng T4 nhưng không khử; candidate `SYNTHETIC` (T4) **không** trình bày như khuyến nghị chốt — phải kèm cảnh báo khảo sát thực địa.

### C. Master Data & Entity Resolution

#### P6 — Trùng PK & số trạm lệch giữa các báo cáo

`🟡 FIX · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:**

1. **Trùng PK (236 dòng).** Catalog evcs gộp từ 3 tab (`cs`/`other`/`bss`); enumerate quét lưới
   chồng lấn → cùng `station_code` xuất hiện nhiều lần.
2. **Số trạm lệch (28.417 vs 28.625).** Không phải lỗi dữ liệu mà là **doc-drift**: tài liệu ghi
   snapshot cũ **28.417**, còn file thực tế là snapshot chốt **28.625** (crawl lại 2026-07-21/22).

**Cách xử lý:**

- **Dedup có kiểm soát.** `merge_catalog.py` giữ **first-wins** (ưu tiên `cs > other > bss`),
  **đếm rõ** số dòng trùng bị bỏ (tách trong-tab vs chéo-tab) và in ra — **không bao giờ gộp/cộng
  công suất** giữa các bản trùng (nguyên tắc E-DQ2). `validate.py` có **cổng CRITICAL** bắt buộc
  `station_code` unique → pipeline **fail** nếu trùng PK tái xuất. Master hiện: **0 trùng**.
- **Đối soát số trạm về một snapshot chốt.** Neo **28.625** (snapshot 2026-07-21/22) là con số chính
  thức; chênh **+208** so với 28.417 = crawl lại tab `cs` (19.219 → 19.427). Đồng bộ mọi tài liệu
  ([evcs.md](sources/evcs.md), [schema-contract.md](schema/schema-contract.md)) + neo **chuỗi đối soát tầng**
  để dứt điểm câu hỏi "số nào đúng":

  $$
  \underbrace{28.625}_{\text{raw catalog}} \;-\; \underbrace{9.118}_{\text{BSS (lọc, --keep-bss để giữ)}}
  \;=\; \underbrace{19.507}_{\text{canonical car-only}} \;=\; \underbrace{19.427}_{cs} + \underbrace{80}_{other}
  $$

**Kết quả.** Master 28.625 trạm, PK `station_code` **unique** (0 CRITICAL), lineage ghi ở
`quality_report.json`. `by_station_type`: VINFAST_CS 19.427 · BATTERY_SWAP 9.118 · OTHER 80.

**Limitation (`DOC`):** đây chỉ giải **trùng PK nội bộ evcs** + đối soát số. Trùng **chéo nguồn**
(cùng 1 trạm vật lý lệch toạ độ giữa evcs và registry official) vẫn là **E-DQ2** (dedup không gian
bằng H3) — **chưa** đóng.

#### P7 — Nhiễm xe máy điện (dùng chung power tier)

`🟠 FIX · ☑ chốt 2026-07-24 · Owner: Giang`

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

#### P8 — Lọc trạng thái vận hành & access (private vs public)

`🟡 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** pipeline **chưa bao giờ lọc** trạm theo trạng thái vận hành hay quyền truy cập
→ trạm **đã ngừng** (OutOfService) vẫn tính là cung, trạm **tư nhân** (Restricted) vẫn tính là cung
công khai, và null (`status` 72 · `is_public` 80) bị **giữ ngầm** không tường minh. Hai trục **độc lập**:
(1) trạng thái vận hành, (2) access public/private.

**Cách xử lý — resolve official-first, tường minh, không xoá dòng.** Registry VinFast là
ground-truth ([[vinfast-official-join-key]]); `status` của evcs chỉ là **snapshot telemetry**
(trạng thái tức thời lúc polling occupancy) nên **không** lật ngược registry (vd evcs `Available`
một khoảnh khắc vs official `INACTIVE` → theo official). Thêm 3 cột canonical vào `stations`:

- **`op_status`** ∈ {`OPERATIONAL`, `MAINTENANCE`, `OUT_OF_SERVICE`, `UNKNOWN`} — official-first,
  fallback evcs khi trạm evcs-only. Gom telemetry occupancy (ACTIVE/BUSY ← Available/AllBusy) về
  `OPERATIONAL`; INACTIVE ← Maintaining → `MAINTENANCE`; OUTOFSERVICE/UNAVAILABLE → `OUT_OF_SERVICE`.
- **`access`** ∈ {`PUBLIC`, `RESTRICTED`, `UNKNOWN`} — official-first (Public/Restricted), fallback `is_public`.
- **`is_operational`** (bool) — **lọc cứng DUY NHẤT:** loại `OUT_OF_SERVICE` (trạm đã ngừng, không
  còn là cung thực). **MAINTENANCE + UNKNOWN GIỮ** (có hạ tầng vật lý / không có ground-truth) — chỉ
  flag để model quyết loc thêm (**chạy 2 chiều** ở bước xử lý khuyết, `E-DQ4`).

Cờ tường minh gắn vào `quality_flags`: `NOT_OPERATIONAL` · `UNDER_MAINTENANCE` · `STATUS_UNKNOWN` ·
`NON_PUBLIC` · `ACCESS_UNKNOWN`. `build_candidates._load_stations` loại **OUT_OF_SERVICE ∪ RESTRICTED**
khỏi anchor **T0** (T0 = incumbent *bắt buộc mở*, CapEx=0 → không được ép mở trạm đã ngừng/tư nhân).

**Kết quả** (19.507 trạm car-only). `op_status`: OPERATIONAL **16.014** · MAINTENANCE **3.392** ·
UNKNOWN **59** · OUT_OF_SERVICE **42**. `access`: PUBLIC **19.418** · UNKNOWN **67** · RESTRICTED **22**.
Cung công khai khả dụng (`is_operational & access=PUBLIC`) = **19.377**. T0 national loại **63 trạm**
(OUT_OF_SERVICE ∪ RESTRICTED) → **19.444**; candidate national **mọi gate PASS**.

**Limitation (`DOC`):** `MAINTENANCE` (3.392, ~17%) là quyết định giữ-làm-cung (siting chiến lược đa
năm coi hạ tầng bảo trì là brownfield hiện hữu); model có thể loại qua cờ `UNDER_MAINTENANCE`. UNKNOWN
(evcs-only, không khớp registry) không có ground-truth → giữ + flag, không suy đoán.

#### P9 — Lệch thời điểm giữa các đợt cào dữ liệu

`🟡 FIX + DOC · ☐ Open · Owner: Giang`

**Cách xử lý:** khóa cố định mốc thời điểm cung sạc chính thức là **2026-07-20** và dữ liệu telemetry occupancy **07/2026**.

### D. Covariates & Feature Engineering

#### P10 — WorldPop 2020 lỗi thời (6 năm)

`🟡 DOC · ⊘ Won't-fix · Owner: Giang`

- Thừa nhận hạn chế (`DOC`).
- **Hiệu chỉnh Pha 5:** Kết hợp WorldPop với số liệu dân số chính thức mới nhất của Tổng cục Thống kê (GSO) cấp tỉnh để tính toán chỉ số `coverage_pop` (% dân số được phủ trạm sạc thực tế).

#### P11 — Model tổng dân số vs mật độ sở hữu ô tô

`🟠 SIMPLIFY · ☐ Open · Owner: Giang`

- Giả thuyết: dữ liệu mật độ dân số chính là proxy cho dữ liệu mật độ sở hữu ô tô.

### E. Data Quality & Cleaning (từ `data-layer-overview.md §7`)

Các dòng **E-DQ** trong [Bảng tổng hợp §2](#2-bảng-tổng-hợp-vấn-đề-đã-gộp) đã được **sắp theo thứ tự xử lý** (trên → dưới) — mỗi bước làm nhỏ tập lỗi cho bước sau:

> `E-DQ10` freeze inputs → `E-DQ9` clip MVP city → `E-DQ2` dedup chéo nguồn → `E-DQ1` sửa toạ độ → `E-DQ7`+`E-DQ8` audit cầu → `E-DQ4` xử lý khuyết → `E-DQ5`+`E-DQ6` chuẩn hoá categorical → `E-DQ3` enrich admin.

Thứ tự này thay cho *kế hoạch làm sạch §8* trước đây ở `data-layer-overview.md` (đã gỡ — thứ tự nay nằm ngay ở bảng). Nguyên tắc chung không đổi: **flag dòng, không xoá**; đối soát `input = output + quarantined + merged` ở mọi bước.

#### E-DQ10 — Freeze snapshot & provenance (bước 0)

`🟡 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** provenance có nhưng **rời rạc & không tái lập được** — `.pbf` mang tên
`vietnam-**latest**` (không phải phiên bản), không có checksum nào chứng minh một file thô
là **bất biến**, mốc thời gian chỉ nằm rải trong `quality_report.json`/`locators_meta.json`, và
**không sản phẩm dẫn xuất nào ghi nó dựng từ snapshot nào**. Vì `E-DQ10` là **bước 0**
(`freeze → clip → dedup → …`), mọi bước phía sau giả định input bên dưới không đổi; nếu nguồn âm
thầm đổi giữa sprint, đối soát `input = output + quarantined + merged` trở nên **vô nghĩa** và
không thể tái lập "28.625 trạm" hay số coverage. Đây cũng là chỗ **vận hành hoá [P9](#p9--lệch-thời-điểm-giữa-các-đợt-cào-dữ-liệu)**:
P9 *quyết* ngày freeze, E-DQ10 làm nó **có checksum & tái lập**.

**Cách xử lý — một snapshot bất biến, content-addressed, có cổng chặn drift.**

- **`snapshot_id = 2026-07-20`** (neo P9). Trùng khớp `osmosis_replication_timestamp` của bản `.pbf`
  (`2026-07-20T20:21:16Z`, seq **4852**) → chính mốc này **pin** nguồn OSM "latest" về một phiên bản
  cụ thể (giải quyết lỗ hổng tái lập lớn nhất mà **không** cần đổi tên file / churn `roads_pbf.py`).
- **`data/raw/MANIFEST.json`** — khai báo tập trung **mọi nguồn thô** + provenance (URL, giấy phép,
  vintage/version, phạm vi không/thời gian). File đơn băm `sha256` nội dung; thư mục nhiều file
  (details 23.240 file, worldcover 17 tile…) cuộn thành **1 bản ghi** `tree_sha256` để manifest gọn
  (9,5 KB) mà vẫn content-addressed. Version tự rút từ nguồn: official `generation 16 · count 58.577`,
  WorldCover `v200/2021`, WorldPop `2020 constrained`.
- **Lineage version-hoá trong git.** Blob thô vẫn `.gitignore`, nhưng `.gitignore` được sửa để
  **re-include đúng `MANIFEST.json`** → checksum + provenance **được commit** dù dữ liệu thì không.
- **Khoá read-only.** `freeze_snapshot` bỏ cờ ghi trên **23.280 file** thô (chống sửa vô tình; re-crawl
  = snapshot mới, phải unlock có chủ đích).
- **Cổng chặn drift 2 tầng.** `validate.py` (cổng QA evcs, đã chặn pipeline) nạp manifest và đối chiếu
  *nhanh* (tồn tại + bytes + số file, không đọc nội dung) mỗi lần chạy → **drift = CRITICAL**; chưa
  freeze = WARN (không chặn pipeline cũ). Đối chiếu *đầy đủ* (băm lại nội dung / `tree_sha256`) chạy
  theo yêu cầu: `make verify-snapshot HASHES=1`. Mọi `quality_report.json` nay mang `snapshot_id` +
  `snapshot_integrity`.

**QA gate (đóng E-DQ10 thật, không chỉ "có file manifest"):** ① mọi nguồn có `version/vintage` non-null
(không còn `latest`/undated) · ② `retrieved`/`bytes`/`sha256` đầy đủ · ③ re-hash on-disk == manifest
(lệch = FAIL) · ④ `snapshot_id` xuất hiện trên `quality_report.json` dẫn xuất · ⑤ manifest được git track
dù `/data/` bị ignore.

**Kết quả** (chạy 27/07): snapshot **2026-07-20**, **5 nguồn / 10 member / ~2,19 GB** đóng băng; verify
nhanh **PASS**, verify content-hash **PASS**, drift test (thêm 1 file lạ) bắt đúng **FAIL**, lock read-only
xác nhận (ghi vào file thô → *Permission denied*). Lệnh: `make freeze` / `make verify-snapshot`.

**Limitation (`DOC`):** git giữ **manifest + checksum**, không giữ blob (WorldPop/OSM hàng trăm MB) → tái
lập đảm bảo *khi có cùng file nguồn*; nếu upstream (Geofabrik, WorldPop) xoay URL thì re-fetch là
best-effort — chính vì thế phải chốt `retrieved_at` + hash **ngay bây giờ**. Cổng ở tầng nhanh soát
bytes/số file (không đọc nội dung) để không làm chậm mỗi lần chạy; đổi nội dung mà **giữ nguyên kích
thước** chỉ bị bắt ở `--hashes` (CI/theo yêu cầu).
