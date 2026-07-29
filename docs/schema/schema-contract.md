# SCHEMA CONTRACT

*Hợp đồng interop giữa **Data (Giang)** và **Model (Kỳ)**. Giang xây toàn bộ tầng dữ liệu; Kỳ tiêu thụ nó cho MCLP. File này là nguồn chân lý về schema, format và điểm bàn giao.*

## 1. Các quyết định đã chốt

| # | Vấn đề                              | Quyết định                                                                                                                                                                                                                                                                                                                                                | Hệ quả                                                                                                                                                                                                                                                     |
| - | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 | **Demand proxy**                 | **Giang xây demand proxy từ nguồn công khai** (WorldPop + OSM + POI) theo lưới H3.                                                                                                                                                                                                                                                              | Giang sở hữu trọn khâu: crawl/tải nguồn → tính`demand_h3` → định nghĩa trọng số → trực quan hóa (mục 4).                                                                                                                                 |
| 2 | **Đơn vị lưới không gian** | **H3 res 8** — ô ở VN: cạnh (= bán kính ngoại tiếp) **0,56 km**, bán kính nội tiếp 0,49 km, **tâm 2 ô kề nhau cách `d` = 0,98 km**, diện tích 0,83 km² — là đơn vị chuẩn cho demand, candidate site và coverage. *(Xác nhận giữ nguyên 24/07/2026 sau khi thử res 7 và rollback — xem **P4**.)* | Mọi join không gian dùng`h3_r8`. `h3_r9` chỉ để tham chiếu chi tiết hơn khi cần. ⚠️ **Ràng buộc kèm theo: bán kính MCLP `R` phải > `d` = 0,98 km** (chốt **R = 3 km**) — nếu không, MCLP suy biến (**P4**). |
| 3 | **Format bàn giao**             | **Parquet (Hive-partitioned) là canonical.** Đọc thẳng vào PostGIS / GeoPandas. CSV chỉ để xem nhanh (Excel).                                                                                                                                                                                                                                  | Pipeline load đọc parquet, không phụ thuộc CSV export.                                                                                                                                                                                                  |

---

## 2. Schema theo bảng & vai trò

- 🟢 **Lõi (canonical input)** - load vào PostGIS, dùng trực tiếp.
- 🟡 **Nguồn demand** - đầu vào để dẫn xuất trọng số demand cho MCLP.
- ⚪ **Tham khảo / dẫn xuất** - snapshot; không dùng làm chân lý.

### 🟢 `stations`

| Cột                                                           | Kiểu                 | Vai trò trong bài toán                                                             |
| -------------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------- |
| `station_id`                                                 | string                | **PK** (`vn-xxxx`)                                                            |
| `station_code` | string | Khoá nguồn ổn định, dùng đối chiếu registry official |
| `lat`, `lng`                                               | double                | Toạ độ đã resolve — candidate site & tính khoảng cách coverage |
| `lat_raw`, `lng_raw`, `coord_src`, `coord_fix_dist_m`, `coord_resolved` | double/string/bool | Audit E-DQ1: giữ toạ độ crawl, nguồn quyết định (`evcs_raw` / `vinfast_official_exact` / `unresolved`), độ lệch và trạng thái resolve |
| `admin_l1_code`, `province_name`                           | string                | Nối`agg_admin`, lọc theo tỉnh                                                    |
| `commune_name`, `commune_kind`                             | string                | Nối cấp xã                                                                         |
| `operator`                                                   | string                | Phân biệt VGreen vs đối thủ                                                      |
| `vehicle_class`                                              | string                | **`CAR`/`UNVERIFIED`/`UNKNOWN`** — lọc nhiễm xe máy (**P7**); `CAR` = mọi connector là chuẩn ô tô (CCS2/Type2) theo registry chính thức |
| `current_type`                                               | string                | `AC`/`DC`/`MIXED` khi registry official xác nhận; `UNKNOWN` nếu evcs-only — **không suy từ power tier** (P7/F13) |
| `station_type`, `max_power_kw`, `total_power_kw`         | string/double         | Cấu hình công suất                                                                |
| `num_connectors`                                             | int                   | Số súng (đối chiếu với bảng`connectors`)                                     |
| `connector_types`                                            | list<string></string> | Nhãn tier công suất (evcs.vn không lộ chuẩn cắm — xem `connectors.connector_standard`) |
| `status`                                                     | string                | **Nguồn evcs thô** (snapshot telemetry: Available/AllBusy/Maintaining/OutOfService) — dùng `op_status` đã resolve |
| `is_public`                                                  | bool                  | **Nguồn evcs thô** access — dùng `access` đã resolve                            |
| `op_status`                                                  | string                | **`OPERATIONAL`/`MAINTENANCE`/`OUT_OF_SERVICE`/`UNKNOWN`** — trạng thái vận hành resolve **official-first** (**P8**) |
| `access`                                                     | string                | **`PUBLIC`/`RESTRICTED`/`UNKNOWN`** — access resolve **official-first** (**P8**) |
| `is_operational`                                            | bool                  | **Lọc cung cứng (P8):** `False` ⇔ `op_status=OUT_OF_SERVICE` (trạm đã ngừng, loại khỏi cung/anchor T0). MAINTENANCE/UNKNOWN giữ + flag |
| `confidence`, `freshness`, `quality_flags`               | double/list           | **Tín hiệu chất lượng** (P8 flags: `NOT_OPERATIONAL`/`UNDER_MAINTENANCE`/`STATUS_UNKNOWN`/`NON_PUBLIC`/`ACCESS_UNKNOWN`) |
| `verified`, `provenance`, `match_method`, `official_*` | bool/string           | **Đối chiếu nguồn chính thức** (vinfastauto.com) — xác minh + xuất xứ |
| `physical_id`, `is_primary`, `dup_group_id`, `dup_method`, `dup_dist_m` | string/bool/double | Audit E-DQ2: nhận dạng thực thể vật lý; model chỉ dùng `is_primary=True` làm cung incumbent |
| `h3_r8`                                                      | string                | **Nối lưới** demand/coverage                                                 |

### 🟢 `connectors` — tầng 2, 1 dòng/nhóm công suất · FK `station_id`

`connector_id`, `station_id` (FK), `power_kw`, `current_type`, `connector_label`, `count_total`, `count_available` + **2 cột chuẩn cắm (P7):**

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `connector_standard` | string | `CCS2` (`IEC_62196_T2_COMBO`) / `TYPE2` (`IEC_62196_T2`) / `UNKNOWN` (trạm evcs-only) — **chuẩn cắm chính thức** từ `official_connectors.standard`, join `store_id==station_code` |
| `vehicle_class` | string | `CAR` (CCS2/Type2) / `UNVERIFIED` — chống nhiễm xe máy điện (**P7**) |

> **P7 — chuẩn cắm thay power tier:** evcs.vn chỉ lộ **công suất**, không lộ chuẩn cắm → tier `AC/DC` theo ngưỡng 25 kW gán **sai** 20-22 kW thành AC (thực tế DC CCS2). Nguồn sự thật là VinFast official (`official_connectors.standard`); 100% connector khớp là chuẩn **ô tô** (CCS2/Type2) → không còn nhiễm 2 bánh sau khi lọc BSS.

### 🟡 `demand_h3` — nhu cầu theo ô H3 (11 cột) · key: `h3_r8`

**Nguồn demand chính thức cho MCLP.** Chứa **thành phần thô** theo ô: `pop`, `road_len_m`, `road_len_mt_m`, `n_poi`, `n_parking`, `n_fuel` (+ `admin_l1_code`, `province_name`, `commune_name`, `commune_kind`).

> Bảng này **chưa có một con số "trọng số demand" duy nhất** cho mỗi ô — đó chính là phần Giang bổ sung (mục 4): `demand_weight = f(pop, road, poi, …)`.

### 🟢 `candidate_sites` — tập điểm ứng viên cho MCLP (14 cột) · PK: `candidate_id`

**Đầu vào candidate cho MCLP** (`data/processed/candidate_sites.parquet` + `.geojson`). Mỗi dòng = 1 điểm thực,
**unique theo `h3_r8`** (≤1 candidate/ô — tránh tie-degenerate, biến thể ẩn **P4**).

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `candidate_id` | string | **PK** (`cand-<city>-<idx>`) |
| `lat`, `lng` | double | toạ độ thật (explainability) |
| `h3_r8` | string | ô coverage (**unique**) |
| `tier` | string | T0–T4 (nguồn anchor) |
| `anchor_type` | string | `existing_station`/`parking`/`fuel`/`mall`/`retail`/`apartments`/`gapfill_synthetic` |
| `source_ref` | string | `station_id` \| `osm_type/osm_id` \| `synthetic:<h3>` |
| `is_existing` | bool | T0 → CapEx=0 Sprint 3 (incumbent bắt buộc mở) |
| `n_existing_in_cell` | int32 | số trạm đang vận hành trong chính ô (đếm **trước** dedup ≤1/ô) — sức chứa tại-ô cho MCLP Sprint 3 |
| `built_up_frac`, `dist_substation_m`, `penalty`, `penalty_flags` | double/list<string> | tín hiệu/penalty land-use và đấu nối; `NOT_BUILT_UP`/`NO_ROAD_ACCESS` là phạt mềm, không phải loại cứng |
| `capex_class` | string | `low`/`mid`/`high` — ràng buộc ngân sách Sprint 3 |

> Bộ lọc khả thi trung gian: `data/interim/landuse/buildable_h3.parquet`. Chi tiết [candidate-sites.md](../data-layer/candidate-sites.md).

### Quan hệ khóa

---

## 3. Phân chia trách nhiệm & luồng dữ liệu

| Ai                                         | Sở hữu / bàn giao                                         | Nội dung                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------ | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Giang** *(toàn bộ data layer)* | Dataset + PostGIS + demand + coverage + GeoJSON hiện trạng | ①**Tự crawl** `stations`/`connectors` (evcs.vn/PlugShare/OSM/Google). ② **Tự xây demand** theo H3 từ WorldPop/OSM/POI → `demand_h3` + `demand_weight` per cell. ③ **Tự tính coverage/gap** theo bán kính R của MCLP. ④ Validate → load PostGIS (`station`/`connector` + bảng H3). ⑤ GeoJSON hiện trạng + heatmap cho map. |
| **Giang → Kỳ**                     | Demand proxy + candidate sites (input MCLP)                  | `h3_r8 → demand_weight` + tập candidate sites — đầu vào MCLP tiêu thụ.                                                                                                                                                                                                                                                                                           |
| **Kỳ** *(model only)*             | MCLP + report                                                | Nhận demand proxy + candidate sites → chạy MCLP →**GeoJSON kết quả** (vị trí đề xuất + coverage theo ngân sách) → report cuối. Không đụng tới tầng dữ liệu.                                                                                                                                                                                    |
| **Kỳ → Giang**                     | GeoJSON kết quả model                                      | Vị trí đề xuất + coverage theo mức ngân sách (Sprint 2–3) để Giang tích hợp lên map.                                                                                                                                                                                                                                                                         |

## 5. Quy ước format

- **Parquet** = canonical (đọc bằng `pandas.read_parquet` / GeoPandas / DuckDB). CSV chỉ để xem.
- **GeoJSON:**
  - *Hiện trạng + heatmap demand* → xuất (H3 cell → polygon lục giác qua thư viện `h3`; điểm trạm từ `lat`/`lng`).
  - *Kết quả model* (vị trí đề xuất + coverage) → **Kỳ** xuất theo cấu trúc thống nhất ở [problem-analysis.md](../problem-analysis.md) mục 4.

## 6. Việc còn mở (cần theo dõi)

- [X] **Giang:** crawl nguồn cung từ evcs.vn → raw `data/raw/evcs/` + master interim `data/interim/stations_master_evcs.csv` (**28.625** trạm — snapshot 2026-07-21/22, PK `station_code` unique, 0 orphan, QA PASS/WARN). Code `src/ev_siting/data/evcs/`, xem [crawler-evcs.md](../sources/evcs.md). *(Con số cũ 28.417 là snapshot trước — xem **P6**.)*
- [X] **Giang (22/07):** transform master (`station_code`, CSV) → parquet canonical `stations`/`connectors` (`station_id` `vn-`) đúng schema mục 3 (H3 res 8 tính từ lat/lng, `operator`, `connector_types`/`quality_flags` kiểu list, `confidence`/`freshness`). Output Hive-partitioned theo `province_code`: `data/interim/canonical/stations/` (19.507 dòng) + `.../connectors/` (24.415 dòng, tầng 2 nổ từ `evse_powers`). Code `src/ev_siting/data/evcs/transform_canonical.py` (`make canonical`). QA: PK unique, 0 orphan FK, `num_connectors == Σ count_total`. **Phạm vi: chỉ trạm sạc ô tô — MẶC ĐỊNH bỏ `BATTERY_SWAP` (9.118 trạm)**, giữ lại được bằng `--keep-bss`. **Còn lại:** cột admin (`admin_l1_code`/`province_name`/`commune_*`) để trống → enrich ở Step B.
- [X] **Giang:** tầng **OSM POI + road (trắc địa)** của `demand_h3` → `data/interim/osm/osm_demand_components_h3.parquet` (262.054 ô: `n_poi`/`n_parking`/`n_fuel` + `road_len_m`/`road_len_mt_m`, QA PASS). Code `src/ev_siting/data/osm/`, xem [crawler-osm.md](../sources/osm.md).
- [X] **Giang:** ghép `pop` (WorldPop 2020 constrained, ~100m) → `data/interim/worldpop/worldpop_pop_h3.parquet` (99,63M người / 104.171 ô) → **`demand_h3` thô** `data/interim/demand/demand_h3.parquet` (268.404 ô: `pop` + `road_len_*` + `n_poi/parking/fuel`). Code `src/ev_siting/data/worldpop/`, xem [crawler-worldpop.md](../sources/worldpop.md). **Còn lại:** enrich cột admin (`admin_l1_code`, `province_name`, `commune_*`) + chốt tập cột cuối → cập nhật mục 3.
- [X] **Giang (23/07):** crawl **nguồn chính thức VinFast** (vinfastauto.com, first-party) → `data/interim/vinfast_official/` (registry 23.247 trạm + 71.174 connector + admin). Xây **matcher 2 tầng** (`match_official.py`): `exact_code` (`station_code==store_id`, 19.427 trạm khớp tuyệt đối, toạ độ lệch ≤0,3 m) + `spatial_fuzzy` (BallTree haversine + rapidfuzz). Output `official_xref.parquet`. `transform_canonical` join vào `stations`: thêm cột **provenance** (`provenance`/`official_matched`/`match_method`/`official_store_id`/`match_dist_m`/`match_name_sim`/`official_charging_status`/`official_access_type`) + **định nghĩa lại** `verified` (corroboration first-party) và `confidence` (`0.4·completeness + 0.6·verification` cho trạm VinFast; `completeness` cho trạm ngoài phạm vi). Canonical: 19.432/19.507 verified, confidence TB 0,995. Doc [crawler-vinfast-official.md](../sources/vinfast-official.md).
- [ ] **Giang:** chốt công thức `demand_weight = f(pop, road_len_mt_m, n_poi, n_parking, n_fuel, …)` — trọng số từng thành phần (đưa vào Sprint 2). ⚠️ Cân nhắc **calibrate trọng số bằng 18,6M điểm occupancy** thay vì đặt tay (**P1**); weight `pop` theo proxy sở hữu ô tô, không dùng tổng dân số thô (**P11**); giữ demand **ngoại sinh** — không đưa hiện diện trạm vào feature (**P2**). Xem [known-issues.md](../known-issues.md).
- [ ] **Giang:** tính coverage với bán kính **R = 3 km (baseline)**, quét {1,5 · 2 · 3 · 5} km (thay ngưỡng `has_station_5km` cố định). ⚠️ **Gate bắt buộc: FAIL nếu `R ≤ d` (0,98 km) · WARN nếu `R < 2d` (1,95 km)** — dưới ngưỡng đó mỗi candidate chỉ phủ chính ô nó → MCLP suy biến thành `sort top-p`. Xem **P4** trong [known-issues.md](../known-issues.md).
- [X] **Giang (24/07):** tập **candidate sites** cho MCLP → `data/processed/candidate_sites.{parquet,geojson}` (điểm chạm interop thứ 3). Mô hình **lai**: điểm thực nhưng **≤1 candidate/ô H3** (tránh tie-degenerate — biến thể ẩn **P4**); phân tầng **T0 trạm hiện có** (`is_existing=True`, incumbent bắt buộc mở — ràng buộc thiết kế) · T1 parking/fuel · T2 mall/retail/apartments · T4 gap-fill synthetic. Lọc **khả thi** qua `buildable_h3` (ESA WorldCover 10m + OSM military/protected/water + `road_len_m≤0`) — loại hồ/núi/đất cấm/không đường (**P5**, **P9**). QA gate 5 cổng (upper-bound coverage ≥90% · freedom ≥5×p · size ≤3000 · anti-degenerate ≥0,9 · `R>d`). MVP Hà Nội: 1.672 candidate, 5/5 PASS. Schema đầy đủ + cột (`is_existing`/`capex_class` cho ràng buộc ngân sách Sprint 3) → [candidate-sites.md](../data-layer/candidate-sites.md).
- [X] **Giang (24/07):** **chốt xử lý P4** — giữ lưới `H3 res 8`, chốt **R = 3 km**. Đã dựng thử `res 7` (`demand_h3` 54.618 ô) rồi **rollback**: res 7 làm ô to gấp 7× (`d` 0,98 → 2,59 km), đẩy tỷ lệ `R/d` sai hướng và làm **mọi R trong (2,59; 4,48) km cho kết quả y hệt nhau** → mất khả năng quét độ nhạy theo R. Toàn bộ dataset đã rebuild lại ở res 8 và **khớp bit-level** với snapshot gốc (`demand_h3` 268.404 ô · `pop` 99,63M · road 730.718 km); QA OSM PASS. Đồng thời sửa lỗi hình học: "800 m" cũ là do **nhầm bán kính nội tiếp với cạnh** lục giác — giá trị đúng `d = a·√3 = 2r = 0,98 km`.
- [X] **Giang:** viết data documentation mới cho tầng cung → [crawler-evcs.md](../sources/evcs.md). Còn lại: doc cho demand/coverage khi build xong.

*Thay đổi schema sau ngày chốt → cập nhật bảng mục 1 & 3, ghi ngày, báo người còn lại.*
