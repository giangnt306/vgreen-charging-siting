# DATASET INVENTORY — Kiểm kê toàn bộ dữ liệu

> **Số đo 2026-07-30 trên `integrate/final` (snapshot 2026-07-30).** Cập nhật: **2026-07-30** (rebuild toàn pipeline từ raw) · Snapshot raw: `MANIFEST.json` `snapshot_id=2026-07-30` (re-freeze 30/07).
>
> Trả lời câu hỏi: *có bao nhiêu bộ dữ liệu, bao nhiêu bảng, bao nhiêu dòng, bao nhiêu cột?*
> Số liệu **đo trực tiếp từ file** (không chép lại từ doc), đọc bằng parser (pandas/pyarrow), không phải `wc -l`.
> Kiến trúc & pipeline: [overview.md](overview.md) · Register vấn đề: [known-issues.md](../known-issues.md).

---

## 0. Đọc nhanh (TL;DR)

| Chỉ số | Giá trị |
| --- | --- |
| **Nguồn dữ liệu (source families)** | **7** — 6 nguồn snapshot raw (thêm **VNSDI** 30/07) + 1 nguồn ngoài (EVN) |
| **Artifact có cấu trúc (bảng/tập file)** | **53** (chưa tính 5 raster/pbf không dạng bảng → **58** tổng) |
| **Tổng số dòng (đo trực tiếp)** | **≈ 80,11 triệu** — chưa cộng bản tách 720h theo trạm (chưa đo lại, nguồn 38,26 M dòng) |
| ↳ trong đó time-series occupancy | raw **56,89 triệu** (168h 18,63 M + 720h 38,26 M + pilot 2 K) + bản tách theo trạm 168h **18,63 M**; bản tách **720h chưa đo lại** (tầng mới) |
| ↳ **dữ liệu phi time-series** | **4,59 triệu** dòng |
| **Tổng số cột (cộng dồn mọi bảng)** | **745** |
| **Số file trên đĩa** | **63.023** file · **5,6 GB** (`data/`) |
| **Bảng "lõi" cho mô hình** | **3** — `stations` (19.805 × **61 cột**), `connectors` (24.787), `demand_h3` (**314.934 × 32 cột**) |
| **Cung sạch cuối cùng (T0)** | **19.086** trạm trên **12.744 ô** (rebuild 30/07). `clean_supply.csv` **đã đồng bộ** — sinh bởi `make export-supply`, 6/6 cổng QA PASS (xem §3.5) |
| **Tầng hành chính (E-DQ3)** | `admin/` — `cell_commune` (**395.276** cặp) · **`demand_commune`** (3.321 xã × **30**) · `province_crosswalk.csv` (64) · 6,2 MB |

> ⚠️ **Không có dataset khảo sát (survey).** Từ "khảo sát" trong `problem-analysis.md` chỉ là **phương pháp
> dự kiến** cho OpEx phi-điện / ràng buộc lưới điện (nhóm 2, chưa thu thập). Dữ liệu hiện có = **crawl + tải công khai**.

---

## 1. Bảy nguồn dữ liệu (theo `data/raw/MANIFEST.json`, snapshot 2026-07-30)

| # | Nguồn | Nội dung | Vintage / extent | License | Dung lượng raw |
| - | --- | --- | --- | --- | --- |
| 1 | **evcs.vn** | Catalog trạm sạc + telemetry occupancy | crawl 21–22/07 (168h) **+ 29/07 (720h)**; TS `2026-06-29 11:40` → `2026-07-29 14:20` | Proprietary (public map API) | **1,5 GB** |
| 2 | **VinFast official** | Store locator first-party (ground truth xác minh) | **generation 210, 61.333 locator** (meta; file array 61.332) | Proprietary (public locator) | **338 MB** |
| 3 | **OpenStreetMap** | Đường (.pbf Geofabrik) + POI (Overpass) | replication seq **4852** @ `2026-07-20T20:21Z` | ODbL 1.0 | **318 MB** |
| 4 | **WorldPop** | Dân số 2020 constrained (BSGM) **UNadj** (Σ **97.569.444**, E-DQ7e ☑) + **2025 R2024B CN 100m** (P10; Σ H3 hoá **101.300.081**); bản UN-unadjusted 2020 giữ trong snapshot làm chứng cứ cổng đơn điệu | 2020 + 2025 | CC-BY 4.0 | **113 MB** (3 raster) |
| 5 | **ESA WorldCover + OSM exclusion** | Land-cover 10 m (17 tile) + vùng cấm/trạm biến áp | WorldCover v200 / 2021 | CC-BY 4.0 / ODbL 1.0 | **1,1 GB** |
| 6 | **VNSDI 34DVHC** | Ranh giới + dân số đăng ký cấp xã (layer 2, 1000N) — nguồn cấp xã độc lập | retrieved `2026-07-30`, **3.321 xã / 34 trang** | Open (cổng VNSDI) | **33 MB** |
| 7 | **EVN (biểu giá điện)** | Biểu giá điện trạm sạc → OpEx | 2026 | Văn bản pháp lý công khai | 8 KB |

Nguồn 1–6 được **freeze + checksum sha256** (E-DQ10, `make verify-snapshot`); nguồn 7 sinh bằng code
(`opex_electricity.py`), nằm ở `data/external/` nên không nằm trong snapshot raw.

---

## 2. `data/raw/` — nguồn thô, bất biến (3,3 GB · 23.333 file)

| Artifact | Format | Dòng | Cột | Khóa / ghi chú |
| --- | --- | ---: | ---: | --- |
| `evcs/catalog/evcs_catalog.csv` | CSV | **28.625** | 16 | `code` — catalog gộp đợt 21–22/07 (stations + BSS + other) |
| `evcs/catalog/evcs_stations.csv` | CSV | 19.427 | 15 | Trạm sạc ô tô (`VINFAST_CS`) |
| `evcs/catalog/evcs_bss.csv` | CSV | 9.118 | 11 | Trạm **đổi pin** — mặc định loại khỏi cung |
| `evcs/catalog/evcs_other.csv` | CSV | 80 | 11 | Khác |
| `evcs/catalog/evcs_stations_2026-07-29-new.csv` | CSV | **298** | 16 | Trạm mới phát hiện đợt probe 29/07 — nạp vào master (28.625 + 298 = 28.923) |
| `evcs/load_ts.csv` | CSV | **18.630.532** | 3 | `station_code`, `timestamp`, `n_cars_charging` — 168h, **485 MB** (đo lại 30/07: không đổi) |
| `evcs/timeseries_runs/load_ts_2026-07-29-full.csv` | CSV | **38.255.343** | 3 | Đợt **720h** (29/07) — 997 MB cả thư mục |
| `evcs/timeseries_runs/PILOT_2026-07-29.csv` | CSV | 1.978 | 3 | Pilot đợt 720h |
| `vinfast_official/locators_full.json` | JSON array | **61.332** | 37 | `store_id` — mọi loại store (showroom, xưởng, trạm sạc…); meta ghi count 61.333 |
| `vinfast_official/details/*.json` | 23.240 file | 23.240 | 25 | 1 file / trạm sạc (union khóa payload `data`, đo 30/07) |
| `osm/poi/{apartments,fuel,mall,parking,retail}.json` | 5 JSON array | **37.362** | 7 | apartments 12.602 · fuel 10.653 · parking 7.121 · retail 5.261 · mall 1.725 |
| `landuse/osm_exclusion/exclusion.json` | JSON array | 1.583 | 5 | Vùng cấm xây (sân bay, quân sự, bảo tồn…) |
| `landuse/osm_exclusion/substations.json` | JSON array | 2.434 | 6 | `power=substation` |
| `vnsdi/pages/*.json` | 34 JSON page | 3.321 | — | ESRI JSON, 3.321 xã (34DVHC layer 2) — nguồn của `interim/vnsdi/communes.parquet` |
| `osm/vietnam-latest.osm.pbf` | OSM PBF | — | — | 318 MB, stream bằng osmium |
| `worldpop/vnm_ppp_2020_UNadj_constrained.tif` (+ bản unadjusted legacy + `vnm_pop_2025_CN_100m_R2024B_v1.tif`) | 3 GeoTIFF | — | — | raster dân số ~100 m, 113 MB |
| `landuse/worldcover/*.tif` | 17 GeoTIFF | — | — | land-cover 10 m, 1,1 GB |

**Tổng raw dạng bảng: ≈ 57,07 triệu dòng** (trong đó 56,89 M là time-series).

---

## 3. `data/interim/` — đã làm sạch / trung gian (2,2 GB · 38.985 file)

### 3.1 Bảng canonical (nguồn chân lý tầng cung)

| Artifact | Format | Dòng | Cột | Khóa |
| --- | --- | ---: | ---: | --- |
| `canonical/stations/` | Parquet Hive (65 partition `province_code`) | **19.805** | **61** | `station_id` (unique), `station_code` (unique) |
| `canonical/connectors/` | Parquet Hive (64 partition) | **24.787** | **11** | `connector_id`; FK `station_id` — **0 orphan** |

> `stations_no_connectors.csv` (282 dòng ở thế hệ trước) **không còn được sinh** ở bản rebuild 30/07 —
> trạm không connector nay nhận diện qua `vehicle_class=UNKNOWN` (283) ngay trong `stations`.
>
> **Đã đồng bộ 30/07** — [overview.md §4](overview.md#4-schema-trạng-thái-thực-tế-đo-2026-07-30) ghi đúng
> `stations` **61 cột** / `connectors` **11 cột** (kèm `province_code` là partition key). Lịch sử số cột của
> `stations`: 34 (bản gửi collaborator) → 44 (23/07) → 49 (+5 cột **E-DQ1**) → **61** (+8 cột ASSET của
> **E-DQ4** + 8 cột nhãn/provenance hành chính của **E-DQ3**).

**Phân bố cờ trên `stations` (19.805 dòng, đo 2026-07-30):**

| Chiều | Phân bố |
| --- | --- |
| `is_primary` (E-DQ2) | True **19.654** · False 151 |
| `op_status` (P8) | OPERATIONAL 15.827 · MAINTENANCE 3.488 · OUT_OF_SERVICE **432** · UNKNOWN 58 |
| `access` (P8) | PUBLIC 19.717 · UNKNOWN 66 · RESTRICTED 22 |
| `coord_resolved` (E-DQ1 + **E-DQ3**) | True **19.749** · False **56** (= 38 `COORD_PLACEHOLDER` + **18 `COORD_OUTSIDE_ADMIN`**) |
| `admin_src` (**E-DQ3**) | inside **19.736** · nearest 13 · unresolved 56 — nhãn hành chính phủ **34 tỉnh · 2.700 xã** |
| `admin_verdict` (**E-DQ3**) | NOT_FLAGGED 18.987 · **COORD_CONFIRMED 562** · UNRESOLVED 200 · NO_COORD 38 · **COORD_BAD 18** |
| `vehicle_class` (P7) | CAR 19.304 · UNKNOWN 283 · UNVERIFIED 218 |
| `has_timeseries` | True 19.426 · False 379 |
| Độ phủ | **65** `province_code` (hệ 63 tỉnh **CŨ** — prefix mã evcs, gồm 2 mã không phải tỉnh) → **34** `admin_l1_code` (**E-DQ3**, niên đại 2025-06-16) |

**Công thức cung dùng cho T0/coverage:** `is_operational & access=='PUBLIC' & is_primary & coord_resolved` →
**19.086** trên **12.744 ô** (rebuild 30/07, master nhận thêm 298 trạm crawl 29/07; lịch sử: 19.015/12.811 →
18.999/12.801 (E-DQ3) → **19.086/12.744**).

### 3.2 Bảng cầu (demand, khóa `h3_r8` res 8)

| Artifact | Dòng (ô H3) | Cột | Ghi chú |
| --- | ---: | ---: | --- |
| `demand/demand_h3.parquet` | **314.934** | **32** | Lưới 30/07 (trước: 255.480 ô) — `cell_state` INSIDE **311.447** · BORDER **3.487**. `pop` + **`pop_adj`** + **`pop_2025`** (P10) + 5 cột `road_*` (**E-DQ7b**) + **`road_access_nb1_m`/`road_access_nb2_m`/`access_tier`** (**E-DQ8a**) + **10 cột POI theo lớp tag** (**E-DQ7c**: `n_fuel` 4.830 · `n_parking_off` 2.147 · `n_parking_street` 149 · `n_mall` 252 · `n_dept_store` 1.133 · `n_supermarket` 1.386 · `n_market` 1.661 · `n_apartment` 5.157 · `n_apartment_complex` **1.370** · `apartment_levels_sum` 34.691) + `pop_pixel_implausible` (**E-DQ7f**) + `cell_state`/`frac_in_vn` (**E-DQ7a**) + **7 cột nhãn hành chính** (**E-DQ3** — **314.608/314.934** ô có nhãn). Σ`pop` = **97.563.106** (**E-DQ7e**, UNadj, bất biến); Σ`pop_adj` = **96.941.979** (−0,64%: 7f người ma + 8b dời dân roadless + cắt biên); Σ`pop_2025` = **101.299.971**. ⚠️ `n_poi`/`n_parking` **khai tử** |
| `demand/settlement_h3.parquet` | **314.934** | **26** | **MỚI (P10)** — phân lớp định cư kiểu GHSL: `settlement_class` RURAL **262.298** · URBAN_CLUSTER **41.161** · URBAN_CENTRE **11.475**; kèm bộ cột `*_2025` song song trên raster 2025 |
| `demand/demand_h3_clipped_out.parquet` | 7.375 | 25 | Ô OUTSIDE bị cắt khỏi lưới cầu — audit **E-DQ7a** |
| `worldpop/worldpop_pop_h3.parquet` | 104.171 | 2 | chỉ ô có dân; Σ = **97.569.444** (**E-DQ7e**) — nguồn `pop` UN-anchored, KHÔNG đụng bởi 7f |
| `worldpop/worldpop_pop_report.json` | — | — | 3 cổng hiệu chuẩn (**E-DQ7e**): tổng khớp file UNadj đã băm · Spearman(cũ, mới) = **1,000000** · tỉ số theo pixel là hằng số (std **2,4e-08**) |
| `worldpop/worldpop_pop_2025_h3.parquet` | **303.319** | 2 | **MỚI (P10)** — raster 2025 R2024B CN 100m; Σ = **101.300.081** |
| `worldpop/worldpop_pop_adj_h3.parquet` | **107.880** | 14 | **E-DQ7f**: `pop` (bất biến) + `pop_adj` (đặt lại chỗ theo built-up) + `pop_src` (WORLDPOP 103.902 · REDISTRIBUTED 2.987 · RETOTALED_DANSO 991) + cờ `pop_pixel_implausible` (139 ô) + chẩn đoán `n_px`/`max_px`/`top3_px_share`/`n_eff`/`pop_per_eff_px`/`pop_lat`/`pop_lon` + `maxa`/`danso`. +3.771 ô nhận (built-up, `pop=0`). Σ`pop_adj` = **97.083.046** (−0,499%) |
| `worldpop/worldpop_pop_acc_h3.parquet` | **262.849** | 19 | **E-DQ8b**: `pop_adj` sau CẢ HAI phép đặt lại chỗ (7f dồn cục + 8b dời dân ô roadless) + `access_tier`/`road_access_m`/`road_access_nb*`/`built_ha` + `pop_src` (sổ cái 30/07: `MOVED_TO_ACCESSIBLE` **6.466** · unrepaired **225 ô** / 42.576 người, trong đó 3 ô `UNREPAIRED_NO_ACCESSIBLE_BUILTUP` → E-DQ8c). Σ`pop_adj` = **96.972.190**; khối lượng ở ô không lối vào **1.183.197 → 1.001** (−99,9%). Đây là bảng `build_demand_h3` ĐANG nạp |
| `worldpop/worldpop_pop_adj_report.json` | — | — | 7 cổng **E-DQ7f**: `pop_bit_invariant`=0 · `retotal_reduces_mass`=486.399 người ma · `global_mass_accounted`=0,000 · drift 0,499% · join 99,84% |
| `vnsdi/communes.parquet` | **3.321** | 10 | **E-DQ7f**: ranh giới + dân số cấp xã (VNSDI 34DVHC, DANSO 2025; re-fetch **30/07**) — nguồn cấp xã **độc lập** để kiểm chứng phân bổ. `maxa`/`tenxa`/`matinh`/`danso`/`dientich_km2`/`geom_wkb`. Σdanso **113.625.653** (đăng ký 2025, +16,5% vs WorldPop) |
| `osm/osm_demand_components_h3.parquet` | 255.054 | 16 | thành phần OSM — cột **suy ra** từ 2 bảng lớp (10 POI + 5 `road_*`) |
| `osm/osm_roads_h3.parquet` | 255.052 | 29 | **bảng LỚP** (E-DQ7b): `m_`/`lane_m_`/`lane_obs_m_` × 9 lớp `highway` + `bridge_m` |
| `osm/osm_poi_h3.parquet` | 6.932 | 20 | **bảng LỚP** (E-DQ7c): `poi_<lớp>` + `poi_<lớp>_restricted` × 8 lớp tag + `poi_apartment_complex`/`_levels`/`_levels_obs` |
| `osm/osm_poi_points.parquet` | **17.102** | 15 | POI dạng điểm **chỉ trong VN** (30/07 tách hẳn phần ngoài biên): **16.848 bản chính + 254 bản trùng**, `in_vn` = True 100% |
| `osm/osm_poi_outside_vn.parquet` | **20.247** | 15 | **MỚI** — POI Overpass rơi ngoài biên giới VN, giữ riêng làm chứng cứ E-DQ7a (17.102 + 20.247 = 37.349) |
| `osm/vn_boundary.parquet` (+ `.geojson`) | 41 | 8 | **MỚI** — biên giới VN adm2 (506.834 km², 4 phần) + 40 polygon adm4; report riêng `vn_boundary_report.json` (6 cổng PASS) |
| `osm/osm_quality_report.json` | — | — | 28 cổng (27 PASS · 1 WARN, đo 30/07) — gồm recall POI bằng nguồn độc lập: fuel **35,9%** / parking **8,8%**, bias theo tầng `pop`: fuel 1,13 · parking **2,44** (WARN) |

> ⚠️ `demand_h3` từng là bảng **duy nhất chưa có cổng QA** dù nó chính là hàm mục tiêu — đã có 7 cổng từ
> `E-DQ7a`/`E-DQ7b` + 8 cổng từ `E-DQ7c`. Audit 28/07 phát hiện **54,2% POI nằm ngoài lãnh thổ VN** (`E-DQ7a`,
> đã sửa), `road_len` sai ngữ nghĩa (`E-DQ7b`, đã sửa), `n_poi` lẫn đơn vị + POI thiếu/trùng (`E-DQ7c`, đã sửa)
> + proxy cầu chỉ đạt ρ = **0,33** so với trần đo được **0,865** của occupancy thật, **644** ô có sạc thật mà
> mọi input proxy = 0 (`E-DQ7d`, **chưa** — chẩn đoán 29/07, bàn giao **Kỳ**; con số cũ "ρ ≈ 0,30 · 983 ô" đã
> được đính chính).
> ✅ **`E-DQ7e` đã đóng 29/07** — đổi hẳn sang raster **UNadj** (Σ 99,627M → **97,569M**), thêm **3 cổng QA**;
> thứ hạng ô **bất biến** (Spearman cũ↔mới = **1,000000** trên 104.171 ô, tỉ số theo pixel là hằng số 0,979344
> với std 2,4e-08) ⇒ MCLP/`demand_weight` **không** phải chạy lại.
> ✅ **`E-DQ7f` đã xử lý 29/07 — thêm `pop_adj` + cờ `pop_pixel_implausible`.** Đo lại trên artefact UNadj
> (khớp lại 30/07): **139 ô / 745.283 dân** bị BSGM dồn vào 1–5 pixel; ngưỡng ">48.000/km²" từng bắt **61 ô lõi
> TP.HCM có thật** và **0/139** ô hỏng (giao=0). Đối chiếu **VNSDI DANSO** (nguồn cấp xã độc lập): phần lớn khối
> lượng bị cờ là DỒN THỪA (đảo Hòn Nghệ 22×) → `pop_adj` rải lại theo built-up (RETOTAL 17 xã / REPLACE 53 xã);
> `pop` giữ UN-anchored. Consumer XẾP HẠNG (MCLP, T4) dùng `pop_adj`; phát biểu tuyệt đối (`coverage_pop`) dùng `pop`.
> ⚠️ **Đọc `n_fuel`/`n_parking_off` như "số cây xăng/bãi đỗ" là SAI**: recall OSM đo được chỉ **35,9%** và
> **8,8%** (đo 30/07); riêng parking còn **lệch đô thị** (tỉ số tầng cao/thấp = **2,44**). Chúng là tín hiệu
> **tương đối**. **Chưa có cột `demand_weight`.** Xem [known-issues.md](../known-issues.md).

### 3.3 Bảng land-use (bộ lọc khả thi candidate — P5)

| Artifact | Dòng | Cột | Ghi chú |
| --- | ---: | ---: | --- |
| `landuse/landuse_h3.parquet` | **1.419.043** | 11 | Bảng **nhiều dòng nhất** (trừ TS) — WorldCover theo H3 toàn quốc |
| `landuse/buildable_h3.parquet` | **314.934** | 14 | Khớp 1-1 với `demand_h3`. **59.926** ô `buildable` (**19,0%**). **255.008** ô bị loại; phân rã theo cờ `exclusion_flags` (một ô có thể mang nhiều cờ — chính sách hợp nhất 30/07): `NOT_BUILT_UP` **253.338** · `WATER` 9.459 · **`ROAD_ACCESS_ISOLATED` 7.874** (**E-DQ8a**) · `WETLAND` 7.286 · OSM `MILITARY` 313 / `PROTECTED` 246 / `AIRPORT` 162. Có `access_tier` để audit (DIRECT 247.685 · ADJACENT 48.575 · NEAR 10.800 · ISOLATED 7.874) + `penalty_flags`/`penalty` (LOW_BUILTUP 289.562 · NEEDS_ACCESS_ROAD 59.375 · CROP 39.407 · ROAD_ACCESS_INFORMAL 27.828 · POP_NO_ROAD 6.350 · ROAD_BRIDGE_ONLY 50) |
| `landuse/osm_substations.parquet` | 2.432 | 2 | Trạm biến áp (proxy lưới điện) |
| `landuse/exclusion_zones.parquet` | **720** | 2 | Ô H3 bị cấm |

### 3.4 Bảng registry official + xref

Registry snapshot `2026-07-29` · **generation 210** · 61.333 locator (meta).

| Artifact | Dòng | Cột | Khóa |
| --- | ---: | ---: | --- |
| `vinfast_official/official_stations.parquet` | **22.983** | 18 | `store_id` — chỉ trạm sạc ô tô |
| `vinfast_official/official_connectors.parquet` | **71.174** | 11 | `store_id` + `evse_idx` + `connector_id` |
| `vinfast_official/official_admin.parquet` | 23.240 | 7 | `store_id` → tỉnh/huyện/xã |
| `vinfast_official/official_xref.parquet` | **28.923** | **25** | `station_code` ↔ `official_store_id` — `match_method`: **exact_code 19.706 · spatial_fuzzy 3.744 · none 5.473** → matched **23.450**, verified **22.936** (report 30/07) |

### 3.5 Bảng master, cung sạch & audit trail

| Artifact | Dòng | Cột | Vai trò |
| --- | ---: | ---: | --- |
| `stations_master_evcs.csv` | **28.923** | 33 | Master evcs khóa `station_code` (gồm 22 cột QA time-series); 28.625 + 298 trạm mới 29/07 |
| `clean_supply.csv` | **19.086** | 14 | **Cung sạch (T0/coverage)** — sinh bởi `export_supply.py` (`make export-supply`), tái sinh 30/07, 6/6 cổng QA PASS |
| `excluded.csv` | **719** | 7 | Dòng bị loại + **đúng một** lý do/dòng (xem bên dưới) |
| `export_supply_report.json` | — | — | Lineage của 2 file trên: `generated_at` 2026-07-30T16:41Z, mẫu số, 6 cổng QA |
| `crosssource_dedup_groups.csv` | **306** | 10 | E-DQ2 — nhóm trùng chéo nguồn |
| `edq1_suspect_stations.csv` | 796 | 17 | E-DQ1 — trạm nghi toạ độ sai |
| `fix_coords_flagged.csv` | 796 | 9 | E-DQ1 — nhật ký sửa toạ độ |
| `evcs_timeseries/*.csv` | **18.630.532** | 2 | **19.218 file**, 1 file/trạm (`timestamp`, `n_cars_charging`) — tầng 168h; nguồn `load_ts.csv` đo lại 30/07 không đổi |
| `evcs_timeseries_720h/*.csv` | chưa đo lại (tầng 720h mới) | 2 | **19.426 file**, 1 file/trạm; nguồn `load_ts_2026-07-29-full.csv` = **38.255.343** dòng (đo 30/07) |

**Đối soát cung: 19.805 − 719 = 19.086** ✓ — là **cổng QA ① `reconciles_input`** của
`export_supply.py` (report 30/07 PASS), không phải phép cộng làm bằng tay trong doc.

> ✅ **30/07 — hai file đã có producer.** Trước đó chúng là **ảnh chụp không ai sinh ra**
> (`grep clean_supply src/` → 0 hit) nên đứng yên ở bản 28/07 trong khi canonical đi tiếp (từng lệch đúng
> 16 dòng `COORD_OUTSIDE_ADMIN`). Nay `make export-supply` sinh lại cả hai từ `canonical/stations` + công thức
> §3.1, kèm **6 cổng QA** và `export_supply_report.json` cho lineage. Sau rebuild 30/07: `clean_supply` 19.086 /
> `excluded` 719 — **khớp canonical**. Nguồn chân lý **vẫn là** `canonical/stations` — hai CSV chỉ là bản xuất
> cho người đọc / công cụ ngoài.
>
> ⚠️ **Một thay đổi định dạng có ý:** `connector_types` bản cũ ghi `['A' 'B']` (`str` của ndarray —
> **thiếu dấu phẩy**, không `literal_eval` được); bản mới ghi `['A', 'B']` (xác nhận trong
> `export_supply_report.json`). Consumer nào đang split theo dấu cách thì phải sửa.

| Lý do loại (`excluded.csv`, đo 30/07) | Số dòng |
| --- | ---: |
| `OUT_OF_SERVICE` (P8) | **429** |
| `CROSS_SOURCE_DUP` (E-DQ2) | 151 |
| `ACCESS_UNKNOWN` (P8) | 62 |
| `COORD_PLACEHOLDER` (E-DQ1) | 38 |
| `RESTRICTED` (P8) | 21 |
| `COORD_OUTSIDE_ADMIN` (E-DQ3) | 18 |

---

## 4. `data/processed/` — model-ready (41 MB)

| Artifact | Dòng | Cột | Ghi chú |
| --- | ---: | ---: | --- |
| `candidate_sites.parquet` / `.geojson` | **16.659** | 14 / 7 | Candidate MCLP (P5) — `candidate_id`, `tier` (**T0 12.769 · T1 2.104 · T2 866 · T4 920**), `capex_class`, `penalty` |
| `covered0.parquet` / `.geojson` | **18.928** | 19 / 11 | Baseline hiện trạng (P8) — **mức trạm** (không còn mức ô): active + public + primary + clean coord; kèm 8 cột ASSET (E-DQ4) |
| `covered0_operational.parquet` / `.geojson` | **15.552** | 19 | **MỚI** — tập con `op_status=OPERATIONAL` (loại 3.376 MAINTENANCE) |

> GeoJSON là bản export rút gọn của parquet — **không** phải dataset độc lập.
> Còn thiếu ở tầng này: `demand_weight`, bảng coverage/gap theo R, load PostGIS
> (`demand_commune` đã có ở `data/interim/admin/` — 3.321 xã × 30 cột).

## 5. `data/external/`

| Artifact | Dòng | Cột |
| --- | ---: | ---: |
| `opex_electricity_tariff.{csv,json}` | 6 | 6 |

---

## 6. Bản đối chiếu đẩy lên Hugging Face

`vgreen-charging-siting-data/` là **bản mirror** của `data/` (không phải dataset thứ hai). Khác biệt duy nhất:
`interim/evcs_timeseries/` (19.218 file) được đóng gói thành **`evcs_timeseries.tar.zst`** (92 MB, có sẵn trong
`data/interim/`). ⚠️ Trạng thái mirror **chưa kiểm lại sau rebuild 30/07** (thư mục mirror không có trên máy đo)
— cần đồng bộ lại toàn bộ, kể cả tầng 720h mới. Xem memory [[hf-dataset-sync]].

---

## 7. Lưu ý khi đọc số liệu

1. **Đừng dùng `wc -l` để đếm dòng CSV.** `name`/`address` có newline nhúng → `stations_master_evcs.csv` cho
   28.951 dòng (sai) thay vì **28.923** (đúng). Mọi số ở doc này đọc bằng parser.
2. **"Bảng" ≠ "file".** `canonical/stations` là 1 bảng nhưng 65 file parquet (Hive partition theo `province_code`);
   `evcs_timeseries/` là 1 dataset nhưng 19.218 file (+ 19.426 file ở tầng `evcs_timeseries_720h/`).
3. **Không cộng dồn dòng giữa các tầng.** Cùng một trạm xuất hiện ở raw → master → canonical → clean_supply;
   tổng ≈ 80,11 M là kiểm kê dung lượng, **không** phải số thực thể.
4. **Số cột sẽ trôi.** Mỗi issue E-DQ đóng lại thường thêm cột (E-DQ1 thêm 5 cột vào `stations`).
   Đối chiếu lại `schema-contract.md` khi số cột lệch.
