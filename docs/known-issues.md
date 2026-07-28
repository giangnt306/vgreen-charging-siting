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
| **E-DQ9**  | E     | Grid toàn quốc vs MVP 1 thành phố (`demand_h3` toàn bảng)                                                                            | 🟡   | SIMPLIFY              | Giang       | **2026-07-27** | ☑           |
| **E-DQ2**  | E     | Trùng chéo nguồn (evcs vs official)                                                                                                       | 🟠   | FIX                   | Giang       | **2026-07-27** | ☑           |
| **E-DQ1**  | E     | Toạ độ placeholder / trùng khít                                                                                                         | 🟠   | FIX                   | Giang       | **2026-07-28** | ☑           |
| **E-DQ7a** | E     | **POI ngoài lãnh thổ VN** — Overpass query bằng `VN_BBOX` thô, không clip biên giới → **54,2%** POI nằm ở Campuchia/Lào/Thái/TQ (và **8.934 km road** rò rỉ: Geofabrik cắt bằng polygon **có đệm**) | 🔴   | **FIX (chặn)**  | Giang       | **2026-07-28** | ☑           |
| **E-DQ7b** | E     | **`road_len` sai ngữ nghĩa** — `track`+`service` tính là đường sinh cầu (19,9%); double-count 2 chiều (motorway 96,9% `oneway`); `_MAJOR` gộp cao tốc + quốc lộ + tỉnh lộ | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ7c** | E     | **POI thiếu & lẫn đơn vị** — OSM chỉ phủ ~30% cây xăng; `n_poi` cộng `apartments` (toà nhà) với `mall` (trung tâm) tỉ lệ 1:1; 496 trùng node/way | 🟠   | SIMPLIFY + DOC        | Giang       | —                   | ☐           |
| **E-DQ7e** | E     | **`pop` chưa hiệu chuẩn** — raster UN-**unadjusted** (99,63M, +2,35% so 97,34M); 69 ô > 48.000 người/km² (đỉnh 83.565) | 🟡   | FIX + DOC             | Giang       | —                   | ☐           |
| **E-DQ8**  | E     | Dân cư không có đường (`pop>0 & road=0`) — *số liệu chỉ chốt được sau `E-DQ7a`+`E-DQ7b`*                        | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ7d** | E     | **Proxy cầu chưa kiểm chứng ngoại vi** — ρ(proxy, 18,6M occupancy) ≈ **0,30**; 983 ô có sạc thật nhưng mọi input proxy = 0 | 🔴   | **FIX (chặn)**  | Giang       | —                   | ☐           |
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
(cùng 1 trạm vật lý lệch toạ độ giữa evcs và registry official) là **[E-DQ2](#e-dq2--trùng-chéo-nguồn-evcs--official-bước-2)** —
đã đóng 27/07 (identity resolution `physical_id`, **không** dedup H3 thô).

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

> `E-DQ10` freeze inputs ✅ → `E-DQ9` clip MVP city ✅ → `E-DQ2` dedup chéo nguồn ✅ → `E-DQ1` sửa toạ độ ✅ →
> **`E-DQ7a` clip biên giới VN ✅** → `E-DQ7b` retype road → `E-DQ7c` + `E-DQ7e` → `E-DQ8` dân cư không đường →
> `E-DQ7d` kiểm chứng ngoại vi (**gate của `demand_weight`**) → `E-DQ4` xử lý khuyết →
> `E-DQ5`+`E-DQ6` chuẩn hoá categorical → `E-DQ3` enrich admin (cũng trọng tài `COORD_ADDR_MISMATCH` của E-DQ1).

**Hai ràng buộc thứ tự trong nhóm `E-DQ7`** (lý do tách 5 dòng thay vì 1):

- **`E-DQ7b` phải xong trước `E-DQ8`.** Con số của E-DQ8 (`pop>0 & road=0`) **chưa ổn định** vì bỏ
  `track`+`service` khỏi `road_len_m` (7b) làm **tăng** số ô `road=0`. Đo E-DQ8 trước = phải đo lại lần hai.
  *(Cập nhật 28/07: dự đoán rằng **7a** cũng làm xê dịch E-DQ8 đã **sai** — clip biên giới xoá 14.369 ô nhưng
  gần như không ô nào có dân, nên E-DQ8 chỉ đi từ **6.352 → 6.350 ô / 1,268M người**. Ràng buộc thứ tự vẫn
  đúng, nhưng lý do là **7b**, không phải 7a.)*
- **`E-DQ7a` mở khoá `E-DQ3`.** Để clip POI theo biên giới phải trích **polygon `admin_level=2`** từ chính `.pbf`
  đã freeze — đúng artefact mà `E-DQ3` cần để spatial-join admin, và do đó cũng giải phóng **758 `COORD_ADDR_MISMATCH`**
  mà E-DQ1 cố ý hoãn. Một artefact, ba issue → làm 7a **sớm nhất** dù E-DQ3 nằm cuối hàng. *(Đã xong 28/07:
  `vn_boundary.parquet` chứa sẵn **40 polygon `admin_level=4`**; `in_vn` đã thăng cấp **4/758** mismatch thành
  lỗi toạ độ xác nhận.)*

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

#### E-DQ9 — Grid toàn quốc vs MVP 1 thành phố (bước 1)

`🟡 SIMPLIFY · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** `demand_h3` được build ở **quy mô toàn quốc** (**268.404 ô** res 8 phủ toàn VN), nhưng
MVP chỉ cần chạy trên **1 thành phố**. Nếu mọi bước hạ nguồn (land-use, buildable, candidate, coverage)
đọc thẳng toàn bảng thì (a) chi phí giải MCLP nổ vượt trần 3.000 candidate (**P5** cổng ③), và (b) demand
ở **rìa AOI** bị coi là "chưa phủ" oan vì trạm phủ nó có thể nằm ngoài cửa sổ. Cần một cơ chế **cắt lưới
về đúng vùng nghiên cứu** mà **không** fork code giữa chế độ MVP-thành-phố và toàn-quốc — nếu không, hai
đường chạy sẽ trôi khỏi nhau (biến thể **doc-drift** của **P6**).

**Cách xử lý — một trừu tượng AOI, duck-typed, một đường code cho cả hai chế độ.** Trọn bộ nằm ở
[`src/ev_siting/aoi.py`](../../src/ev_siting/aoi.py):

- **`AOI`** = `tròn(tâm, radius_km) + vành buffer_km` (mặc định 5 km). `radius_km` = **lõi** (nơi đo
  coverage/DoD); `buffer_km` = vành ngoài, candidate **được phép** đặt nhưng gắn cờ `in_core=False`
  (trạm rìa vẫn phủ lõi → không bị tính "chưa phủ" oan). `CITY_PRESETS` chốt sẵn 5 TP
  (hanoi/hcm/danang/haiphong/cantho); `.cells()` sinh đĩa H3 quanh tâm rồi lọc theo bán kính thật.
- **`NationalAOI`** = **cùng giao diện** (`bbox()`/`contains()`/`in_core()`/`cells()`/`to_dict()`) nhưng
  `.cells()` đọc thẳng lưới quốc gia từ `demand_h3`. Nhờ duck-typing, **mọi module hạ nguồn không biết**
  đang chạy city hay national — không có nhánh `if national` rải rác.
- **Một điểm điều phối:** `add_aoi_args`/`aoi_from_args`/`resolve_aoi` cắm cùng nhóm cờ CLI
  (`--city <preset>` ↔ `--national`) vào **mọi** pipeline tiêu thụ AOI: `landuse/worldcover.py`,
  `landuse/build_buildable_h3.py`, `landuse/osm_exclusion.py`, `features/build_covered0.py`,
  `features/build_candidates.py`. Đổi phạm vi = đổi **một cờ**, không đụng logic.
- **Không đụng độ mịn lưới.** Clip chỉ **chọn tập ô**, vẫn giữ `H3 res 8` → **không** phá tỷ lệ `R/d`
  của **P4** (clip ≠ đổi resolution).

**QA gate (đóng E-DQ9 thật, không chỉ "có class AOI"):** ① một đường code chạy được **cả** `--city` lẫn
`--national` trên cùng module (không fork) · ② clip là **hàm tất định của hình học AOI** (mọi consumer
lọc qua cùng `aoi.contains`/`aoi.cells` → không phân kỳ giữa các bước) · ③ tách bạch `in_core` (đo phủ)
vs buffer (được đặt) để demand rìa không bị phạt oan · ④ `|candidate|` sau clip nằm trong trần MCLP của
**P5** · ⑤ metadata AOI (`to_dict()`) ghi vào report/sidecar để truy vết cấu hình mỗi lần chạy.

**Kết quả** (chạy 27/07): cùng một pipeline, hai phạm vi kiểm chứng:

- **MVP Hà Nội:** AOI = lõi 25 km + buffer 5 km (bán kính ngoài 30 km) → **3.141 ô** res 8 (từ
  268.404 ô quốc gia, **~1,2%**). Candidate build trên AOI này ra **1.672 candidate**, **mọi gate P5 PASS**.
- **Toàn quốc:** `--national` chạy trên đủ **268.404 ô** (đã vector hoá/scale — xem **P5**).

**Limitation (`DOC`):** AOI hiện là **tròn(tâm, bán kính)**, **không** phải ranh giới hành chính thật
(cột admin còn null — **E-DQ3**). Bán kính lõi mỗi TP chọn theo phạm vi đô thị hoá liên tục chứ không
theo địa giới, nên rìa AOI là **xấp xỉ**. Khi **E-DQ3** enrich xong, chỉ cần thay `AOI.cells()` bằng
spatial-join với polygon xã/tỉnh — mọi module tiêu thụ AOI **không phải sửa** (đó chính là lý do trừu
tượng hoá duck-typed).

#### E-DQ2 — Trùng chéo nguồn (evcs ↔ official) (bước 2)

`🟠 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán — KHÔNG phải 1 vấn đề, mà là 3** (giống cách mổ **P5**). Đo trên canonical car-only
(19.507) + registry official:

| Loại | Bằng chứng | Xử lý |
| ----- | ------------ | ------- |
| **2a — collapse evcs↔official** (1 trạm VinFast vật lý = nhiều bản ghi: 1 `exact_code` + các `spatial_fuzzy` rơi vào **cùng** `official_store_id`; vd AEON Hà Đông bị 3 app EFASTCHARGE/TIENMAT/evcs liệt kê) | **9** store official bị >1 canonical trỏ vào | collapse (dinh danh first-party trùng khớp) |
| **2b — trùng nội evcs** (station_code khác, không anchor official, cùng điểm vật lý; vd đại lý BYD 2 feed) | **204** cụm toạ độ trùng khít / **478** trạm | merge coord + name |
| **2c — official-only** (chiều ngược: trạm car official vắng khỏi evcs) | **3.486** official-only — nhưng **3.466 `UNAVAILABLE`**, chỉ **~13** live | **DOC**, không merge |

**Tại sao KHÔNG dedup bằng H3 thô** (như register ghi ban đầu): 10.284 trạm chung ô res 8, nhưng ô
0,83 km² → mall/sân bay chứa **nhiều trạm thật**. Dò 1 cụm ramp toạ độ placeholder cho thấy **44 charger
"Tư nhân"** ở **44 tỉnh khác nhau** nhưng toạ độ tăng đều (giả) — dedup theo ô sẽ **phá ~10k trạm thật**.
Phải theo **khoảng cách + định danh**, ô chỉ là khoá blocking.

**Cách xử lý — identity resolution `physical_id`, FLAG không xoá** (nhất quán P6/P8), ở
[`dedup_crosssource.py`](../../src/ev_siting/data/evcs/dedup_crosssource.py):

- **T1 `official_store`:** >1 dòng evcs cùng `official_store_id` → union **không cần ngưỡng** (2a).
- **T2 `coord_name`:** phần còn lại, cặp cách nhau **< 50 m** VÀ tên giống (`token_set_ratio ≥ 82`).
  **Tên bắt buộc** — cùng 1 trạm ở 2 feed thì tên trùng; toạ độ trùng mà tên khác = **trạm khác** dùng
  chung toạ độ placeholder (→ E-DQ1), không phải trùng (2b).
- **GUARD blob:** các trạm nối nhau qua cạnh < 50 m tạo "blob"; blob **≥ 5 thành viên** = cụm toạ độ
  đáng ngờ (chuỗi ramp / stack trùng khít) → **KHÔNG merge**, gắn cờ `DUP_COORD_SUSPECT`, để **E-DQ1**
  phân xử. Chặn chaining bắc cầu thành cụm khổng lồ (bài học cụm 44).
- Mỗi nhóm chọn **1 survivor** (`is_primary=True`; ưu tiên `exact_code` > `official_matched` > confidence
  cao > có telemetry > `station_id` nhỏ). Bản trùng: `is_primary=False` + cờ `CROSS_SOURCE_DUP`.
  Thêm cột `physical_id`/`dup_group_id`/`dup_method`/`dup_dist_m`/`n_dup_members` → **truy vết & đảo ngược được**.
- **Không cộng công suất** giữa bản trùng (nguyên tắc E-DQ2 từ P6). Cung/coverage/anchor **T0** chỉ dùng
  `is_primary` (giống `is_operational` của P8) — [`build_candidates._load_stations`](../../src/ev_siting/features/build_candidates.py)
  lọc `is_primary` để 1 trạm vật lý không thành 2 incumbent "bắt buộc mở" / phủ trùng 2 lần.

**QA gate 5 cổng** (chặn trong `transform_canonical`, FAIL = raise): ① đối soát `input = primary + duplicate` ·
② `physical_id` unique giữa primary · ③ **anti-over-merge** (nhóm `coord_name` < 5 thành viên → blob đậm đặc
đã bị chặn) · ④ primary là `physical_id` của chính nó · ⑤ mọi dup có `dup_group_id` + cờ `CROSS_SOURCE_DUP`.

**Kết quả** (chạy 27/07, car-only 19.507, **giữ nguyên số dòng**): **primary 19.178** · duplicate flag
**329** (`coord_name` 318 · `official_store` 11) · **289 nhóm** (max 4/nhóm) · **214** trạm `DUP_COORD_SUSPECT`
chuyển **E-DQ1**. Cung công khai khả dụng (`is_operational & PUBLIC & is_primary`) = **19.053**. **Mọi gate PASS.**
Inspect độc lập: `python -m ev_siting.data.evcs.dedup_crosssource --dump` → `crosssource_dedup_{report.json,groups.csv}`.

**Limitation (`DOC`):**
- **2c:** 3.486 trạm car official vắng khỏi canonical (canonical dựng từ evcs), nhưng **3.466 là
  `UNAVAILABLE`** (quy hoạch/offline, không phát telemetry) → **đúng khi loại khỏi cung vận hành**; chỉ ~13
  trạm live-và-thiếu (không đáng fork pipeline). Ghi nhận để không ai tưởng canonical âm thầm mất 3.486 trạm.
- Vài merge `coord_name` cho charger **"Tư nhân"** khác tên chủ ở ~40 m là **biên** (địa chỉ trùng lấn át
  `token_set_ratio`); tác động nhỏ (charger hộ gia đình) và **đảo ngược được** qua `dup_group_id`/`dup_dist_m`.
- E-DQ2 chạy **trước E-DQ1** (thứ tự register) nên toạ độ chưa được làm sạch → chọn **bảo thủ**: cụm đáng
  ngờ **không** merge mà **hoãn** sang E-DQ1 (`DUP_COORD_SUSPECT`), thay vì merge nhầm.

#### E-DQ1 — Toạ độ placeholder / trùng khít (bước 3)

`🟠 FIX · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán — đo trên canonical car-only (19.507).** Toạ độ **không thiếu** (0 null · 0 zero · 0 ngoài
bbox VN — mọi điểm "hợp lệ về hình thức") nhưng **sai**: **204 nhóm toạ độ trùng khít** phủ **478 trạm**;
cụm lớn nhất **35 trạm** dồn về **một điểm HCM** `(10.773106, 106.694794)` trong khi địa chỉ toàn **Hà Nội /
Bắc Ninh / Hưng Yên** (charger "Tư nhân"). `lat/lng` là **khoá join của mọi bước hạ nguồn** (`h3_r8`,
coverage/gap, anchor **T0**, demand proxy) → 35 trạm Hà Nội bị tính là **cung HCM** ⇒ phủ ảo ở HCM + gap giả
ở Hà Nội ⇒ MCLP khuyến nghị **sai chỗ**. Đây là poisoning hàm mục tiêu, không phải lỗi cosmetic.

**Phát hiện quyết định (định hình lời giải):** cả **35/35 `official_matched`**, và **registry official cũng
ghi đúng điểm placeholder đó** (111 store official chung 1 điểm, 100% prefix mã `HNO`). ⇒ **"snap về official"
(official-first như P7/P8) KHÔNG cứu được E-DQ1** — official sai ở đúng trường này. Nhưng `province_code`
(rút từ prefix mã `C.HNO…` → HNO, **độc lập toạ độ**) lại là ground-truth tỉnh đáng tin.

**Hai detector — KHÁC nhau về mức độ chắc chắn "toạ độ là trường sai":**

| Detector | Tín hiệu | Chắc chắn | Xử lý |
| --------- | --------- | ---------- | ------- |
| **A `COORD_PLACEHOLDER`** | nhóm exact-coord ≥ `STACK_MIN=5` `physical_id` khác nhau **VÀ** điểm chung **cách centroid-tỉnh của các thành viên > 100 km** (∪ `DUP_COORD_SUSPECT` E-DQ2) | **toạ độ chắc chắn sai** | `coord_resolved=False`, `h3_r8=NULL`, **loại khỏi cung** |
| **B `COORD_ADDR_MISMATCH`** | toạ độ ↔ `province_code` lệch (Voronoi: centroid gần nhất là tỉnh **khác** & gần hơn centroid-gốc ≥ `MARGIN=75 km`) | **không rõ trường nào sai** | **ADVISORY** — giữ toạ độ & `h3_r8` & giữ trong cung; **E-DQ3 trọng tài** (point-in-polygon) |

**Tại sao A kết hợp 2 điều kiện (stack **VÀ** xa tỉnh), không chỉ "trùng toạ độ":** một **venue thật**
(mall/sân bay) cũng dồn nhiều trạm về 1 điểm POI **nhưng điểm đó GẦN tỉnh của nó** → **không** flag. Chỉ khi
≥5 trạm vật lý khác nhau dồn về 1 điểm **XA tỉnh của chúng** thì điểm chung mới là **artifact** (nhiều trạm
không thể cùng ngẫu nhiên sai `province_code` giống hệt). Đã kiểm: 35 trạm mã HNO ở điểm HCM **bị bắt**; **10
trạm thật ở Hải Phòng** (gần tỉnh) được **GIỮ** — detector còn tách đúng **per-station** một điểm vừa chứa 10
trạm thật vừa bị 3 trạm placeholder tỉnh khác dồn lên.

**Tại sao B chỉ ADVISORY, không loại:** trên **324 ca lệch > 300 km**, đối chiếu địa chỉ cho thấy toạ độ khớp
**địa chỉ** (⇒ `province_code` prefix mới là lỗi) **92 lần** vs khớp **`province_code`** (⇒ toạ độ mới là lỗi)
**113 lần** — **~50/50**, B **không thể tự quyết** trường nào sai. Loại nhầm ~92+ trạm toạ-độ-đúng khỏi cung
**hại coverage hơn** là bỏ sót. Trọng tài đúng là **E-DQ3** (spatial-join admin polygon trên toạ độ) — nhất
quán cách E-DQ2 **hoãn** `DUP_COORD_SUSPECT` sang E-DQ1.

**Cách xử lý — cây ground-truth toạ độ, FLAG không xoá** (nhất quán P6/P8/E-DQ2), ở
[`fix_coords.py`](../../src/ev_siting/data/evcs/fix_coords.py), chạy **sau** E-DQ2 (nhận sẵn `DUP_COORD_SUSPECT`):

- **Chỉ detector A điều khiển `coord_resolved`.** (1) không placeholder → `coord_src='evcs'`, giữ toạ độ. (2)
  placeholder nhưng official có toạ độ **tốt** (không placeholder, gần centroid-tỉnh) & đổi điểm → snap
  `coord_src='official'` (thực tế VN = **0** vì official mang cùng placeholder; giữ tier theo nguyên tắc
  official-first & phòng hộ). (3) placeholder không cứu được → `coord_resolved=False`, `h3_r8=NULL`, **loại
  khỏi cung** (không neo phủ ở vị trí chưa biết — giống `is_operational`/`is_primary`).
- **Provenance (đảo ngược & geocode tương lai):** `lat_raw`/`lng_raw` (giữ gốc), `coord_src`,
  `coord_fix_dist_m`, `coord_resolved`; **`h3_r8` tính lại** từ toạ độ đã resolve. Cung/coverage/**T0** thêm
  điều kiện `coord_resolved` ([`build_candidates._load_stations`](../../src/ev_siting/features/build_candidates.py)).

**QA gate 5 cổng** (chặn trong `transform_canonical`, FAIL = raise): ① `provenance_complete` (mọi dòng có
`coord_src` + `lat_raw/lng_raw`; đối soát `input=output` giữ nguyên 19.507 dòng) · ② `unresolved_no_h3`
(placeholder ⇒ `h3_r8` NULL) · ③ `no_unfixed_placeholder_in_supply` (`COORD_PLACEHOLDER & coord_resolved`
chỉ hợp lệ khi đã snap official) · ④ `placeholder_labeled` (placeholder → `coord_src ∈ {placeholder,
official}`) · ⑤ `h3_consistent` (`h3_r8` khớp toạ độ đã resolve).

**Kết quả** (chạy 28/07, **giữ nguyên 19.507 dòng**): **`COORD_PLACEHOLDER` 38** (35 HNO@HCM + 3 TNG) →
`coord_resolved=False`, `h3_r8=NULL`, loại cung · **`COORD_ADDR_MISMATCH` 758** (advisory, giữ toạ độ →
E-DQ3) · snap official **0** · **214 `DUP_COORD_SUSPECT`** của E-DQ2 được **phân xử**: **38 xác nhận
placeholder** (loại) + **176 minh oan** là venue thật (giữ). Cung công khai khả dụng
(`is_operational & PUBLIC & is_primary & coord_resolved`) = **19.015** (= 19.053 − 38). **Mọi gate PASS.**
Inspect độc lập: `python -m ev_siting.data.evcs.fix_coords --dump` → `fix_coords_{report.json,flagged.csv}`.

**Limitation (`DOC`):**
- **Không geocode street-level** (snapshot đóng băng offline + địa chỉ bẩn E-DQ6): placeholder không cứu được
  bằng official → để `coord_resolved=False` (loại cung) + giữ `lat_raw/lng_raw` để **relocate sau** (commune
  centroid khi E-DQ3 có polygon / geocoder roadmap). **Không đoán** toạ độ giả.
- **`COORD_ADDR_MISMATCH` (758) chưa trọng tài** trong scope E-DQ1 — cố ý hoãn sang **E-DQ3** (point-in-polygon
  là trọng tài đúng); B **không** loại trạm khỏi cung để tránh bỏ nhầm ~50% ca toạ-độ-đúng.
- Detector A dùng `STACK_MIN=5` (khớp E-DQ2) → **bảo thủ**: stack 2–4 `physical_id` cùng điểm **không** bị loại
  (có thể co-located thật); đánh đổi recall lấy an toàn cung. `official`-first bị lật **duy nhất** ở trường toạ
  độ cho charger tư nhân (placeholder upstream) — ghi rõ để không mâu thuẫn P7/P8.

#### E-DQ7a — POI ngoài lãnh thổ VN (bước 4)

`🔴 FIX (chặn) · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán.** `overpass_poi.py` query bằng `VN_BBOX = (8, 102, 23.7, 110)` — hộp này chứa **trọn** Phnom Penh,
Viêng Chăn, Nam Ninh/Sùng Tả (Quảng Tây) và Hải Nam → **20.256/37.362 POI (54,2%) không nằm trong lãnh thổ VN**.
Nặng hơn: cổng QA `poi_coords_in_vn` của [`osm/validate.py`](../src/ev_siting/data/osm/validate.py) kiểm "POI
nằm trong `VN_BBOX`" — **kiểm đúng cái hộp sinh ra lỗi** ⇒ PASS suốt từ đầu. Một cổng chỉ có giá trị khi nó
**có thể FAIL**. `demand_h3` là hàm mục tiêu của MCLP nên đây là poisoning, không phải lỗi cosmetic.

**Ba nguồn rò rỉ, ba hình học khác nhau** (đo trên snapshot `2026-07-20`) — lý do không thể dùng một chính sách chung:

| Nguồn | Khối lượng ngoài VN | Hình học rò rỉ | Nguyên nhân |
| --- | --- | --- | --- |
| POI (Overpass) | 20.256 điểm (**54,2%**) | ~99% **sâu** trong nước bạn (chỉ 195 POI trong vòng 10 km quanh biên) | bbox thô, không clip |
| `road_len` (`.pbf`) | **8.934 km** (1,2%) | **96% trong 10 km quanh biên** | Geofabrik cắt bằng polygon **có đệm**, không cắt đúng biên |
| `pop` (WorldPop) | 6.472 người (0,0065%) | 100% trong ~2 km quanh biên | hiệu ứng mép raster |

> ⚠️ **Sửa nhận định cũ.** [overview.md §7](data-layer/overview.md) từng ghi "`road` lấy từ Geofabrik (**đã clip
> theo quốc gia**)" → **sai**. E-DQ7a vì thế xử lý **cả road**, không chỉ POI.

**Hai quyết định thiết kế (đều đo được, không suy đoán):**

1. **Clip POI ở mức ĐIỂM, phân loại lưới ở mức Ô.** Clip POI theo ô sẽ vừa **giữ** POI nước ngoài (ô có tâm rơi
   vào VN) vừa **xoá** POI VN (ô có tâm rơi ra ngoài). Chỉ điểm mới có lãnh thổ xác định.
2. **Test ô = LỤC GIÁC ∩ POLYGON, không phải TÂM Ô ∈ POLYGON.** Ô res 8 có bán kính nội tiếp 0,49 km nên ô vắt
   biên rơi tâm về bên nào cũng được. Đo thật: test theo **tâm ô** xoá mất **74.642 dân VN thật**; test theo
   **giao lục giác** chỉ xoá **6.472** (0,0065%) — cùng một ranh giới, lệch **11 lần**. Ô vắt biên (`BORDER`)
   **giữ** kèm `frac_in_vn` (tỉ lệ diện tích thuộc VN) để `demand_weight` tự quyết chính sách chia tỉ lệ —
   1.391 ô biên có `frac_in_vn < 0,5` và chứa **69.527 dân**, quá lớn để xử lý ngầm bằng một cờ nhị phân.

**Cách xử lý — polygon trích từ chính `.pbf` đã freeze**, ở [`osm/vn_boundary.py`](../src/ev_siting/data/osm/vn_boundary.py):

- **Nguồn:** relation OSM `admin_level=2` **id 49915** trong `vietnam-latest.osm.pbf` (E-DQ10, `snapshot_id=2026-07-20`)
  → **không thêm nguồn thô mới**, không đụng MANIFEST, tái lập được. **Không** re-crawl Overpass bằng bộ lọc
  `(poly:…)`: polygon 614 way làm query cực nặng, và re-crawl là **phá snapshot** — clip là bước **dẫn xuất**
  trên raw bất biến.
- **Tự ráp ring, không dùng `FileProcessor.with_areas()`.** Đã thử: bộ ráp area của osmium trả về **rỗng** cho
  relation 49915 vì **15/614 way outer bị Geofabrik cắt** ở mép extract → ring không khép, assembler bỏ qua
  **im lặng**. `linemerge` + `polygonize` chịu được khuyết đó. Chính vì chế độ lỗi là "im lặng" nên cổng ④ (neo
  điểm) là **bắt buộc**.
- **Cùng một lượt đọc `.pbf` ráp luôn polygon `admin_level=4`** (**40 tỉnh** phía VN) — đúng artefact **E-DQ3**
  cần để spatial-join admin. Một lượt đọc, hai issue.
- **FLAG không xoá** (nhất quán E-DQ1/E-DQ2): `in_vn` (bool, mức điểm) trên `osm_poi_points.parquet` — dòng ngoài
  VN **được giữ**, chỉ **không được đếm** vào `n_poi`/`n_parking`/`n_fuel`. `cell_state ∈ {INSIDE, BORDER,
  OUTSIDE}` + `frac_in_vn` trên `demand_h3`; ô `OUTSIDE` tách sang `demand_h3_clipped_out.parquet` để đối soát
  `input = output + clipped`.
- Không đụng độ mịn lưới (vẫn `H3 res 8`) → **không** phá tỷ lệ `R/d` của **P4**.

**QA gate — 6 cổng ở `vn_boundary.py` + 6 cổng ở `build_demand_h3.py`** (đóng E-DQ7a thật, không chỉ "có file
polygon"): ① `boundary_valid` (bắt chế độ lỗi assembler-trả-rỗng) · ② `boundary_area_km2` trong dải
450–560 nghìn km² · ③ `boundary_mainland_share ≥ 0,9` · ④ **`boundary_anchor_points`** — 6 điểm VN phải **trong**,
5 điểm Phnom Penh/Viêng Chăn/Nam Ninh/Ubon/Savannakhet phải **ngoài** (mọi điểm "ngoài" đều nằm **trong**
`VN_BBOX`, tức cổng này test đúng lỗ hổng) · ⑤ `boundary_ways_resolved` (way khuyết ≤ 5%) · ⑥
`provinces_assembled` (E-DQ3). Phía lưới: ⑦ **đối soát `input = output + clipped`** trên cả 6 đại lượng · ⑧
`demand_unique_h3` · ⑨ non-negative · ⑩ `road_mt_le_total` · ⑪ **`clip_pop_loss_negligible < 0,1%`** (clip ăn vào
dân số ⇒ polygon sai hoặc lỡ dùng test tâm-ô) · ⑫ `no_outside_cell_in_grid`. `osm/validate.py` thay cổng
`poi_coords_in_vn` (vô dụng) bằng `counts_match_in_vn_poi` — số đếm phải **bằng đúng** số POI `in_vn`.

**Kết quả** (chạy 28/07 — `make boundary && make osm && make demand`):

| Đại lượng | Trước | Sau | Ghi chú |
| --- | --- | --- | --- |
| POI được đếm | 37.362 | **17.106** | `n_poi` 19.588→**9.679** · `n_parking` 7.121→**2.463** · `n_fuel` 10.653→**4.964** |
| Ô lưới `demand_h3` | 268.404 | **254.035** | −7.000 ô "ma" chỉ-có-POI (biến mất ở mức điểm) − 7.369 ô `OUTSIDE` |
| `pop` | 99,627 M | **99,621 M** | mất 6.472 người (**0,0065%**) |
| `road_len_m` | 730.719 km | **721.785 km** | −8.934 km (1,2%) |

Polygon: **506.834 km²**, 4 phần, mainland share 0,977, 15/614 way khuyết (2,4%) — **mọi cổng PASS**.
`buildable_h3` national đã dựng lại trên lưới mới (254.035 ô, 59.768 buildable, gate PASS). Ô `BORDER`: **2.977**
(trung vị `frac_in_vn` 0,54).

**Hiệu ứng phụ đã kiểm chứng — thang `penalty` của P5 từng bị ô nước ngoài định đoạt.** `dist_term` trong
[`build_buildable_h3`](../src/ev_siting/data/landuse/build_buildable_h3.py) chuẩn hoá theo `dmax =
max(dist_substation_m)` **trên toàn lưới**; lưới cũ chứa ô sâu trong Campuchia/Lào (rất xa mọi trạm biến áp VN)
nên `dmax` bị thổi phồng ⇒ mọi `penalty` bị nén xuống. Sau clip, candidate Hà Nội **giữ nguyên 1.711 điểm và
nguyên phân bố tier** (T0 1.409 · T4 130 · T1 112 · T2 60, mọi gate PASS) — khác biệt **duy nhất** là `penalty`
nhích lên (vd 0,003 → 0,004), tức thang phạt mềm nay được chuẩn hoá trên lãnh thổ VN thay vì trên ô nước ngoài.

**Kiểm chứng chéo độc lập** (polygon **không** được dựng từ dữ liệu này): chiếu **19.507 trạm canonical** lên
polygon → **19.503 trong VN, 4 ngoài** (0,02%), và cả 4 đều là **lỗi toạ độ có thật** mà **E-DQ1** đã nghi:
`vn-c-hno16032` "xã Bất Bạt, **Hà Nội**" ở `(20.077, 104.771)` = **Lào**; `vn-c-hcm17024` "Xã Hóc Môn, **TP.HCM**"
và `vn-c-hye12380` "**Hưng Yên**" đều rơi sang **Campuchia**; `vn-c-dna10968` "**Đà Nẵng**" rơi ra **vịnh Bắc Bộ**.
⇒ `in_vn` **thăng cấp 4/758 `COORD_ADDR_MISMATCH`** từ advisory lên lỗi xác nhận, và tỉ lệ dương-tính-giả 0,02%
trên tập 19,5k điểm độc lập là bằng chứng polygon đáng tin.

**Limitation (`DOC`):**

- Polygon `admin_level=2` **bao gồm lãnh hải** (506.834 km² so với 331.212 km² đất liền) → mask **rộng có chủ
  đích**: không bao giờ xoá nhầm POI ven biển/hải đảo, nhưng cũng **không** đánh dấu ô ngoài khơi là "không phải
  đất". Lọc đất/nước là việc của WorldCover trong **P5** (`buildable_h3`) — **không gộp hai khái niệm**.
- Mask kế thừa cách OSM thể hiện các vùng biển tranh chấp (relation có ring Hoàng Sa/Trường Sa) → phải mô tả là
  "OSM `admin_level=2` tại snapshot `2026-07-20`", **không** phải tuyên bố chủ quyền chính thức.
- Ô `BORDER` hiện **giữ nguyên giá trị `pop`/`road_len`** (chưa chia tỉ lệ theo `frac_in_vn`) — cố ý hoãn sang
  bước `demand_weight` để chính sách chia tỉ lệ nằm cùng chỗ với công thức trọng số.
- `.pbf` snapshot chứa **cả đơn vị hành chính sau sáp nhập 2025 lẫn bản "cũ"** (`Tỉnh Lào Cai` **và** `Tỉnh Lào
  Cai cũ`, tương tự Quảng Trị / An Giang) → 40 polygon adm4 cần **quy tắc phân định** trước khi dùng cho
  **E-DQ3**; E-DQ7a chỉ dùng adm2 nên không bị ảnh hưởng.
