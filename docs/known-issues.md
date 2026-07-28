# KNOWN ISSUES & LIMITATIONS REGISTER

*Danh sách vấn đề của bài toán tối ưu vị trí trạm sạc VGreen. Đây là **nguồn chân lý để monitor & xử lý** — mỗi vấn đề có: mức độ, phạm vi xử lý trong internship, chủ sở hữu, ngày xử lý, hướng khắc phục, trạng thái. Cập nhật cột **Trạng thái** + **processed_date** khi tiến triển.*

## 1. Chú giải

- **Nhóm:**
  - `A` Demand Target & Data Science
  - `B` Spatial Geometry & Siting Mechanics
  - `C` Master Data & Entity Resolution
  - `D` Covariates & Feature Engineering
  - `E` Data Quality & Cleaning (di chuyển từ `data-layer-overview.md §7` — xem [Task-1 rationale](#0-nguồn-gộp))
  - `F` Pipeline Integrity & Handoff (từ review 2026-07-28 — bằng chứng đầy đủ ở [sprint-reviews/data-pipeline-review-2026-07-28.md](sprint-reviews/data-pipeline-review-2026-07-28.md))
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
| **E-DQ1**  | E     | Toạ độ placeholder / trùng khít                                                                                                         | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ7**  | E     | Cầu chưa audit (`pop`, POI/road)                                                                                                         | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ8**  | E     | Dân cư không có đường (`pop>0 & road=0`)                                                                                            | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ4**  | E     | Cấu hình khuyết (`current_type`, `max_power_kw`, `total_power_kw`, `num_connectors=0`)                                            | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ5**  | E     | Trường`operator` bẩn                                                                                                                    | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **E-DQ6**  | E     | Text tự do bẩn (`name`, `address`)                                                                                                     | ⚪   | SIMPLIFY              | Giang       | —                   | ☐           |
| **E-DQ3**  | E     | Cột admin trống (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`)                                                 | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **F1**     | F     | HF dataset public (license Unknown, push lại 28/07) — rủi ro pháp lý ToS/vault                                                       | 🔴   | **FIX (chặn)**  | Giang       | —                   | ☐           |
| **F2**     | F     | `split_timeseries` ghi đè khi resume → mất telemetry vĩnh viễn                                                                        | 🔴   | FIX                   | Giang       | **2026-07-28** | ☑           |
| **F3**     | F     | Race listener Socket.IO → time-series gán nhầm trạm (không hậu kiểm được)                                                            | 🔴   | FIX                   | Giang       | **2026-07-28** | ☑           |
| **F4**     | F     | Bộ lọc dirty-coord chết (2 cờ không ai sinh); `DUP_COORD_SUSPECT` không ai tiêu thụ; T0 bypass buildable                             | 🔴   | FIX                   | Giang       | **2026-07-28** | ☑           |
| **F5**     | F     | `covered0` bỏ qua P8/E-DQ2 (status/is_public thô, thiếu `is_primary`) → baseline lệch hệ quy chiếu với T0                            | 🟠   | FIX                   | Giang       | **2026-07-28** | ☑           |
| **F6**     | F     | Telemetry mất im lặng: timeout→null→`.done` không retry; enrich lỗi→`seen` vĩnh viễn                                                 | 🟠   | FIX                   | Giang       | **2026-07-28** | ☑           |
| **F7**     | F     | `match_official`: NaN distance→`verified=True`; matcher không được wire vào pipeline                                                  | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **F8**     | F     | Enumerate resume mất force-seed → under-coverage cụm dày đặc                                                                          | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **F9**     | F     | Overpass trả 200 + kết quả cụt (`remark`) không kiểm → POI thiếu ở ô dày                                                             | 🟠   | FIX                   | Giang       | —                   | ☐           |
| **F10**    | F     | Bàn giao 21/07 = snapshot mồ côi (hash ≠ MANIFEST, cùng nhãn 07-20, thiếu mọi fix P6–E-DQ2) → cần re-handoff                        | 🟠   | FIX                   | Kỳ+Giang   | —                   | ◐           |
| **F11**    | F     | `evcs_new_supply` (phía Kỳ) không dedup nội tập + chứa 46 OOS/659 Maintaining → nhiễm ground truth T1 (B4)                          | 🔴   | **FIX (chặn B4)** | Kỳ         | **2026-07-28** | ☑           |
| **F12**    | F     | Không atomic/fail-fast: `run_pipeline.sh` chạy tiếp khi crawl fail; ckpt ghi thẳng; `transform_canonical` rmtree                      | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **F13**    | F     | Ngưỡng 25kW còn 4 chỗ (master + fallback canonical); `num_ports`=totalCharging (74% max-concurrent > tot)                            | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **F14**    | F     | `penalty` chuẩn hoá per-AOI trên file dùng chung; `built_up<0.05`/`road=0` hard-exclude (liên E-DQ7/E-DQ8)                           | 🟡   | SIMPLIFY              | Giang       | —                   | ☐           |
| **F15**    | F     | Docs/config trôi: schema-contract thiếu 6 cột E-DQ2 + QA ảo; `params.yaml` mồ côi (R=500m); cột chết trong candidate                 | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **F16**    | F     | Test né logic rủi ro: không test `_load_stations`/`_gapfill`/`_qa_gate`/covered0                                                      | 🟡   | FIX                   | Giang       | —                   | ☐           |
| **F17**    | F     | `_tos_firewall` (phía Kỳ) chỉ bọc bảng `stations`, các bảng dist khác không qua firewall                                              | 🟡   | FIX                   | Kỳ         | —                   | ☐           |
| **F18**    | F     | Gộp Low: `fetch_locators` không so `meta.count`; PBF/TIF thiếu check `got<total`; manifest hỏng→WARN; `merge_catalog` ghi vào raw/   | ⚪   | FIX                   | Giang       | —                   | ☐           |
| **F19**    | F     | Occupancy sampling theo sự kiện không đều (median 0,9' · max gap 71h) → calibrate P1/A2 bắt buộc duration-weight                     | 🟡   | FIX + DOC             | Kỳ         | —                   | ☐           |
| **F20**    | F     | Code sinh snapshot HF 28/07 **mới hơn git HEAD** (cột `coord_*`, cờ `COORD_PLACEHOLDER`/`COORD_ADDR_MISMATCH`, h3 null) — E-DQ1 làm ngoài repo | 🟠   | FIX                   | Giang       | —                   | ☐           |

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

### F. Pipeline Integrity & Handoff (review 2026-07-28)

*Nguồn: [data-pipeline-review-2026-07-28.md](sprint-reviews/data-pipeline-review-2026-07-28.md) — ở đó có đầy đủ bằng chứng, con số đo trực tiếp và bảng ưu tiên. Dưới đây chỉ ghi vị trí + hướng fix để tick dần. Thứ tự xử lý đề xuất: **F1 → F2+F3+F6 (trước mọi lần crawl tiếp theo) → F4+F5 (mở khoá feature) → F10+F11 (trước B4 30–31/07) → F7 → F8+F9+F12 → F13–F19**.*

#### 🔴 Chặn

- **F1 — HF public.** `Wanderer210w/vgreen-charging-siting-data` vẫn public, license Unknown, **push lại 28/07** (raw + 19.218 series occupancy + 23.240 JSON VinFast, 47 download/tháng). Xử lý: chuyển private hoặc gỡ `raw/` + occupancy + JSON; thêm license + `SOURCES_AND_LICENSES.md`. *Không việc gì được demo/publish trước khi đóng mục này.*
  - *Re-check 28/07 (lần 2, sau khi đã kéo snapshot về local):* **vẫn public, không đổi.** Toàn bộ snapshot đã nằm ở `aGiang-evcs/data/` (verify `HASHES=1` PASS) → **private repo ngay không còn chi phí gì với team** — dữ liệu fix lỗi không phụ thuộc HF nữa. Việc còn lại thuần quyết định con người (Giang + mentor).
- **F2 — split_timeseries overwrite.** `split_timeseries.py:26,48-51`: `flush()` mode `"w"` + giả định mỗi station là khối liền → crash-resume ghi đè file cũ. Fix: buffer dict toàn cục theo code, hoặc merge-union với file hiện có khi flush; sửa docstring.
  - **☑ Fix 28/07:** raw telemetry mỗi run nằm riêng ở `raw/evcs/timeseries_runs/load_ts_<run-id>.csv`; `split_timeseries --input <run>` merge-union vào duy nhất `interim/evcs_timeseries/<station_code>.csv`, raw run mới thắng timestamp trùng, sort và ghi atomically bằng `os.replace()`. Canonical vẫn đúng tên station code nên master/QA giữ contract 1:1. Test `test_timeseries_integrity.py::test_split_merges_discontiguous_blocks_and_new_run_wins`.
  - *Hệ quả cần theo dõi:* canonical `<code>.csv` giờ là **union nhiều run**, nên "cửa sổ 168h" không còn là bất biến của file — mọi phân tích theo cửa sổ (P3/F19) phải tự cắt theo `timestamp`, và `run_pipeline.sh` sinh run-id mới mỗi lần chạy nên resume xuyên phiên cần `EVCS_TS_RUN=<run-id>`.
- **F3 — Socket.IO listener race.** `evcs_scrape.py:53-60`: trạm timeout không gỡ listener `once('history_data')` → reply muộn của trạm A resolve promise trạm B (time-series gán nhầm danh tính). Fix: `socket.off('history_data', done)` trong nhánh timeout + validate `stationId` trong payload nếu có.
  - **☑ Fix 28/07:** mỗi station history request mở/đóng **socket riêng**, nên payload không có correlation id cũng không thể chảy sang listener station khác. (Chỉ `socket.off` trong nhánh timeout là **chưa đủ**: listener của B được đăng ký *sau* khi A timeout, nên reply muộn của A vẫn resolve B — cô lập theo socket mới là điều kiện đủ.) Timeout/socket lỗi ghi `<run>.failed` và không vào `.done`; chỉ response hợp lệ mới hoàn tất resume.
  - *Chi phí cần đo:* 1 handshake/trạm thay vì 1/lô-50 → wall-clock crawl có thể tăng đáng kể trên 19.218 trạm. Nếu thành nút thắt: chạy song song vài socket (`Promise.all` theo chunk) — vẫn giữ được cô lập danh tính.
- **F4 — bộ lọc dirty-coord chết.** `build_candidates.py:53` & `build_covered0.py:47` lọc `{DUP_COORD, COORD_ADDR_MISMATCH}` — không producer nào sinh. Cờ thật đang tồn tại: `DUP_COORD_SUSPECT` (214 trạm, `dedup_crosssource.py:199-201`) không ai đọc; T0 còn bypass buildable (`build_candidates.py:225`). Fix tối thiểu: thêm `DUP_COORD_SUSPECT` (+cân nhắc `COORD_INVALID`) vào `_DIRTY_COORD_FLAGS` cả 2 file; sửa `candidate-sites.md` đang tuyên bố lớp lọc này hoạt động.
  - **☑ Fix 28/07:** tập cờ dùng chung `features/paths.py:DIRTY_COORD_FLAGS = {COORD_INVALID, COORD_ADDR_MISMATCH, COORD_PLACEHOLDER, DUP_COORD_SUSPECT}` (khớp từ vựng thật của snapshot 07-20, gồm cả cờ E-DQ1 mới) + helper `has_dirty_coord` — cả 2 consumer import chung, hết drift. Test `test_covered0.py::test_dirty_flags_exist_in_producer_vocabulary` chặn cờ ma tái phát; `test_t0_drops_every_dirty_coordinate_flag` xác nhận T0 loại **mọi** cờ trong tập. **Bonus:** fix này đồng thời sửa crash `candidates-national` (38 trạm `COORD_PLACEHOLDER` mang `h3_r8=null` → `grid_disk` TypeError). Kết quả national: T0 18.374→18.168 anchor (loại 206 toạ độ bẩn), 16.412 candidate, mọi gate PASS (coverage 0,9105). *T0 bypass buildable giữ nguyên có chủ đích (brownfield đã có điện).*
- **F11 — new_supply phía Kỳ nhiễm (chặn B4).** `evcs-dataset/src/evcs/transform/evcs_vn_new_supply.py`: không dedup nội tập NEW (121/3.797 row là cặp <50m; **40/1.544 tier HIGH** — chính ground truth T1); 46 OutOfService + 659 Maintaining pass `ever_active==1`. Fix trước B4: dedup nội tập (coord<50m + name-sim + blob-guard, mượn `dedup_crosssource`) + cờ trạng thái từ canonical mới của Giang qua `station_code`.
  - **☑ 28/07 (repo `evcs-dataset`):** đóng phía Kỳ, dùng bundle handoff `2026-07-28-v2` cho status gate. Bằng chứng nằm ở repo kia — commit này chỉ ghi nhận trạng thái.

#### 🟠 Cao

- **F5 — covered0 lệch hệ quy chiếu.** `build_covered0.py:44-52,73-76` dùng `status`/`is_public` thô, không đọc `op_status`/`access`/`is_operational`/`is_primary` → 329 dup đếm 2 lần, trạm official-ACTIVE bị loại oan, T0 ⊄ covered0. Fix: filter = `is_operational & access=='PUBLIC' & is_primary` (công thức 19.053 của P8/E-DQ2); lý tưởng dùng chung `_load_stations` với candidates.
  - **☑ Fix 28/07:** filter viết lại đúng công thức + sạch-toạ-độ (F4), tách `_baseline_mask` thuần để test; export đổi `status`/`is_public` → `op_status`/`access` (P8 resolve). Kết quả national: 15.451 → **18.105** trạm baseline (= 19.053 − 948 toạ độ bẩn; MAINTENANCE 3.052 giữ theo quyết định P8, model tự loại qua `op_status`); 329 dup không còn đếm đôi. Hanoi: 2.271 → 2.638. Khác biệt T0 giữ access-UNKNOWN vs baseline strict-PUBLIC là **có chủ đích**, doc trong docstring — đo được **63 trạm** (T0 18.168 ⊅ covered0 18.105, ~0,35%): các trạm này bị MCLP ép mở với CapEx=0 nhưng không nằm trong baseline, nên coverage biên của chúng bị tính hơi rộng. Đóng hẳn khi E-DQ4 quyết được `access=UNKNOWN`.
  - **F5 update 28/07:** `covered0` là planning baseline (giữ `MAINTENANCE`); đồng thời xuất `covered0_operational` chỉ gồm `OPERATIONAL + PUBLIC + primary + clean_coord` để đo sensitivity của coverage hiện tại.
- **F6 — telemetry mất im lặng.** `evcs_scrape.py:189-197` (null vẫn `.done`), `evcs_enumerate.py:225-226` (lỗi → `seen`). Fix: chỉ done khi `series is not None`; danh sách fail ra file riêng + retry pass 2.
- **F7 — match_official.** (a) `match_official.py:249-250`: `pd.isna(dist) or ...` → sửa thành `pd.notna(dist) and ...`, thiếu toạ độ = mức "code-only" riêng; (b) không có `make match`, transform fallback im lặng khi thiếu xref (`transform_canonical.py:246-249`) → thêm target + FAIL/WARN khi xref thiếu/stale (mất xref = E-DQ2 T1 biến mất im lặng).
- **F8 — resume mất force-seed.** `evcs_enumerate.py:296-299,364-377`: resume không tái tạo force-seed cho trạm đã phát hiện → cụm >50 trạm không được mở rộng tiếp. Fix: khi resume, re-seed mọi trạm trong `found` chưa nằm trong đĩa phủ.
- **F9 — Overpass truncation.** `overpass_poi.py:71-72`: HTTP 200 + `remark` "runtime error/timed out" được nhận nguyên. Fix: check `remark` → ép tách bbox như nhánh ≥40k.
- **F10 — re-handoff snapshot chuẩn.** Bản trong `evcs-dataset/00_raw/source=evcs_vn` (28.417, copy 21/07) khác sha256 với MANIFEST frozen (28.625, crawl 21-22/07) — cùng nhãn `2026-07-20`, thiếu mọi fix P6–E-DQ2. *Cập nhật 28/07: snapshot HF (bit-identical với MANIFEST, verify `--hashes` PASS) đã tải về `aGiang-evcs/data/` → re-handoff từ đây: catalog frozen + canonical (`op_status`/`is_primary`/`physical_id`/`connector_standard`), drop cột bẫy `gold_station_id` (NN không ngưỡng, p99 6,6km).*

  - **◐ Re-handoff 28/07:** đã export bundle bất biến `handoff=2026-07-28-v2` vào consumer, gồm catalog 28.625 dòng, canonical stations 19.507 và connectors 24.415, `HANDOFF.json` chứa source-manifest hash + tree hash. F11 verify tree hash trước khi dùng. F10 giữ **Partial** tới khi consumer thay toàn bộ raw/bronze cũ bằng bundle này; hiện bundle mới đã được F11 dùng cho status gate.

#### 🟡 / ⚪ Trung bình & thấp

- **F12 — atomicity/fail-fast.** `run_pipeline.sh:13` thêm `set -e` cho bước 1–3 (hoặc gate đếm tối thiểu); ckpt `evcs_enumerate.py:311-313` ghi `.tmp` + `os.replace` + validate regex mã khi resume; `transform_canonical.py:369-377` ghi thư mục tạm rồi swap.
- **F13 — tàn dư ngưỡng 25kW + cột đánh lừa.** `build_master_evcs.py:26,57` (master CSV vẫn tier-derived), `transform_canonical.py:56,199,346` (fallback không cờ riêng — thêm `CURRENT_TYPE_TIER_DERIVED`); `num_ports`=totalCharging (`build_master_evcs.py:224`): **đo thật 74% trạm max-concurrent > tot, 14.537 cs tot=0** → rename `n_charging_snapshot` hoặc drop.
- **F14 — hard-exclude & chuẩn hoá.** `build_buildable_h3.py:110,118` (`built_up<0.05` trên ước lượng nhiễu stride-8; national loại 47% ô pop>0), `:87-90,111` (`road=0` từ độ phủ OSM; mọi class trừ đi bộ đều tính), `:125-126` (`penalty` chia `dmax` per-AOI trên file dùng chung → `capex_class` đổi theo lần chạy). Fix: soft-penalty + mẫu số vật lý cố định + WARN→FAIL có ngưỡng.
- **F15 — docs/config trôi.** `schema-contract.md` thiếu 6 cột E-DQ2 và mô tả QA không tồn tại trong code (orphan chỉ print — thêm assert); `config/params.yaml` mồ côi `radius_m: 500` mâu thuẫn `R_BASELINE_KM=3.0` (xoá hoặc đồng bộ); `candidate_sites.province_code`/`exclusion_flags` chết 100%; `data-dictionary.md` chỉ có tariff.
- **F16 — test gap.** Bổ sung 4 test: `_load_stations` (cờ lọc lấy từ producer thật — bắt được F4), `_gapfill` AOI-clip (regression cho 495b0c3), `_qa_gate` 5 cổng, `build_covered0` filter.
- **F17 — firewall phía Kỳ.** `evcs-dataset/src/evcs/publish/export.py:102-155`: wrap mọi `write_*` vào dist qua `_tos_firewall` (hiện chỉ `stations`).
- **F18 — gộp Low.** `fetch_locators.py:93-99` so `len(items)` vs `meta.count` + parse gate `.done` đủ; `roads_pbf.py:105-119`/`worldpop_pop.py:34-47` thêm check `got<total` (mẫu: `worldcover.py:97-98`); `validate.py:122-124` manifest corrupt → CRITICAL thay vì WARN; `merge_catalog.py:11-12` chuyển output khỏi `data/raw/`; `R_cov=1.05R` (`evcs_enumerate.py:360`) + đo coverage vs registry official.
- **F20 — code sinh data mới hơn git HEAD (phát hiện 28/07 khi fix F4).** Canonical parquet trong snapshot HF 28/07 chứa cột/cờ mà code tại HEAD `495b0c3` **không sinh ra**: `lat_raw`/`lng_raw`/`coord_src`/`coord_fix_dist_m`/`coord_resolved`, cờ `COORD_PLACEHOLDER` (38, `coord_resolved=False`, **`h3_r8=null`**) và `COORD_ADDR_MISMATCH` (758) — tức E-DQ1 đã được Giang làm một phần **ngoài repo**. Hệ quả: (a) không review/tái lập được bước coord-fix; (b) semantics `h3_r8=null` làm consumer HEAD crash (đã chắn ở F4). Xử lý: Giang push code E-DQ1 + cập nhật schema-contract (cột `coord_*`); tới lúc đó coi các cột `coord_*` là **chưa kiểm chứng**.
- **F19 — phương pháp dùng occupancy.** Đo thật trên 18,63M điểm: sampling theo sự kiện (median gap 0,9', p99 41', max 71h; 513 trạm <50 obs; 129 trạm span <3 ngày; 3.417 trạm zero suốt 7 ngày; `n_cars_charging` max 109 > tot 45 — ngữ nghĩa chưa xác nhận). Mọi calibrate P1/A2 phải **duration-weight/resample lưới đều**, không mean-of-samples; câu hỏi ngữ nghĩa counter gửi Giang (report §5).
