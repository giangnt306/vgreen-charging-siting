# DATASET INVENTORY — Kiểm kê toàn bộ dữ liệu

> Cập nhật: **2026-07-28** · Nhánh `data/giang` · Snapshot raw: `MANIFEST.json` `snapshot_id=2026-07-20`.
>
> Trả lời câu hỏi: *có bao nhiêu bộ dữ liệu, bao nhiêu bảng, bao nhiêu dòng, bao nhiêu cột?*
> Số liệu **đo trực tiếp từ file** (không chép lại từ doc), đọc bằng parser (pandas/pyarrow), không phải `wc -l`.
> Kiến trúc & pipeline: [overview.md](overview.md) · Register vấn đề: [known-issues.md](../known-issues.md).

---

## 0. Đọc nhanh (TL;DR)

| Chỉ số | Giá trị |
| --- | --- |
| **Nguồn dữ liệu (source families)** | **6** — 5 nguồn crawl/tải + 1 nguồn ngoài |
| **Artifact có cấu trúc (bảng/tập file)** | **42** (chưa tính 3 raster/pbf không dạng bảng → **45** tổng) |
| **Tổng số dòng** | **≈ 40,31 triệu** |
| ↳ trong đó time-series occupancy | **18,63 triệu × 2** (raw `load_ts` + bản tách theo trạm) |
| ↳ **dữ liệu phi time-series** | **3,05 triệu** dòng |
| **Tổng số cột (cộng dồn mọi bảng)** | **497** |
| **Số file trên đĩa** | **42.669** file · **2,5 GB** |
| **Bảng "lõi" cho mô hình** | **3** — `stations` (19.507), `connectors` (24.415), `demand_h3` (268.404) |
| **Cung sạch cuối cùng (T0)** | **19.015** trạm (`clean_supply.csv`) |

> ⚠️ **Không có dataset khảo sát (survey).** Từ "khảo sát" trong `problem-analysis.md` chỉ là **phương pháp
> dự kiến** cho OpEx phi-điện / ràng buộc lưới điện (nhóm 2, chưa thu thập). Dữ liệu hiện có = **crawl + tải công khai**.

---

## 1. Sáu nguồn dữ liệu (theo `data/raw/MANIFEST.json`)

| # | Nguồn | Nội dung | Vintage / extent | License | Dung lượng raw |
| - | --- | --- | --- | --- | --- |
| 1 | **evcs.vn** | Catalog trạm sạc + telemetry occupancy | crawl 21–22/07/2026; TS `2026-07-13 20:51` → `2026-07-21 00:32` | Proprietary (public map API) | **500 MB** |
| 2 | **VinFast official** | Store locator first-party (ground truth xác minh) | generation 16, 58.577 locator | Proprietary (public locator) | **268 MB** |
| 3 | **OpenStreetMap** | Đường (.pbf Geofabrik) + POI (Overpass) | replication seq **4852** @ `2026-07-20T20:21Z` | ODbL 1.0 | **318 MB** |
| 4 | **WorldPop** | Dân số 2020 constrained (BSGM), **UNadj** (Σ **97.569.444**) — đổi từ bản UN-unadjusted ngày 29/07 (**E-DQ7e** ☑); bản cũ giữ trong snapshot làm chứng cứ cổng đơn điệu | 2020 | CC-BY 4.0 | **44 MB** (18 + 26) |
| 5 | **ESA WorldCover + OSM exclusion** | Land-cover 10 m (17 tile) + vùng cấm/trạm biến áp | WorldCover v200 / 2021 | CC-BY 4.0 / ODbL 1.0 | **1,03 GB** |
| 6 | **EVN (biểu giá điện)** | Biểu giá điện trạm sạc → OpEx | 2026 | Văn bản pháp lý công khai | 12 KB |

Nguồn 1–5 được **freeze + checksum sha256** (E-DQ10, `make verify-snapshot`); nguồn 6 sinh bằng code
(`opex_electricity.py`), nằm ở `data/external/` nên không nằm trong snapshot raw.

---

## 2. `data/raw/` — nguồn thô, bất biến (2,1 GB)

| Artifact | Format | Dòng | Cột | Khóa / ghi chú |
| --- | --- | ---: | ---: | --- |
| `evcs/catalog/evcs_catalog.csv` | CSV | **28.625** | 16 | `code` — catalog gộp (stations + BSS + other) |
| `evcs/catalog/evcs_stations.csv` | CSV | 19.427 | 15 | Trạm sạc ô tô (`VINFAST_CS`) |
| `evcs/catalog/evcs_bss.csv` | CSV | 9.118 | 11 | Trạm **đổi pin** — mặc định loại khỏi cung |
| `evcs/catalog/evcs_other.csv` | CSV | 80 | 11 | Khác |
| `evcs/load_ts.csv` | CSV | **18.630.532** | 3 | `station_code`, `timestamp`, `n_cars_charging` — **508 MB** |
| `vinfast_official/locators_full.json` | JSON array | **58.576** | 36 | `store_id` — mọi loại store (showroom, xưởng, trạm sạc…) |
| `vinfast_official/details/*.json` | 23.240 file | 23.240 | 34 | 1 file / trạm sạc (chi tiết connector) |
| `osm/poi/{apartments,fuel,mall,parking,retail}.json` | 5 JSON array | **37.362** | 7 | apartments 12.602 · fuel 10.653 · parking 7.121 · retail 5.261 · mall 1.725 |
| `landuse/osm_exclusion/exclusion.json` | JSON array | 1.583 | 5 | Vùng cấm xây (sân bay, quân sự, bảo tồn…) |
| `landuse/osm_exclusion/substations.json` | JSON array | 2.434 | 6 | `power=substation` |
| `osm/vietnam-latest.osm.pbf` | OSM PBF | — | — | 318 MB, stream bằng osmium |
| `worldpop/vnm_ppp_2020_constrained.tif` | GeoTIFF | — | — | raster dân số ~100 m |
| `landuse/worldcover/*.tif` | 17 GeoTIFF | — | — | land-cover 10 m, 1,03 GB |

**Tổng raw dạng bảng: ≈ 18,78 triệu dòng.**

---

## 3. `data/interim/` — đã làm sạch / trung gian (388 MB)

### 3.1 Bảng canonical (nguồn chân lý tầng cung)

| Artifact | Format | Dòng | Cột | Khóa |
| --- | --- | ---: | ---: | --- |
| `canonical/stations/` | Parquet Hive (65 partition `province_code`) | **19.507** | **49** | `station_id` (unique), `station_code` (unique) |
| `canonical/connectors/` | Parquet Hive (64 partition) | **24.415** | **11** | `connector_id`; FK `station_id` — **0 orphan** |
| `canonical/stations_no_connectors.csv` | CSV | 282 | 16 | Trạm không có connector (`vehicle_class=UNKNOWN`) |

> **Lệch so với [overview.md §4](overview.md#4-schema-trạng-thái-thực-tế):** doc ghi `stations` **44 cột** (inspect 23/07),
> file hiện **49** — thêm đúng 5 cột E-DQ1 (`lat_raw`, `lng_raw`, `coord_src`, `coord_fix_dist_m`, `coord_resolved`).
> `connectors` doc ghi 10 cột, file **11** (kèm `province_code` là partition key). Cần đồng bộ lại doc/schema-contract.

**Phân bố cờ trên `stations` (19.507 dòng):**

| Chiều | Phân bố |
| --- | --- |
| `is_primary` (E-DQ2) | True **19.178** · False 329 |
| `op_status` (P8) | OPERATIONAL 16.014 · MAINTENANCE 3.392 · UNKNOWN 59 · OUT_OF_SERVICE 42 |
| `access` (P8) | PUBLIC 19.418 · UNKNOWN 67 · RESTRICTED 22 |
| `coord_resolved` (E-DQ1) | True 19.469 · False **38** |
| `vehicle_class` (P7) | CAR 19.218 · UNKNOWN 282 · UNVERIFIED 7 |
| `has_timeseries` | True 19.218 · False 289 |
| Độ phủ | **65 tỉnh/thành** |

**Công thức cung dùng cho T0/coverage:** `is_operational & access=='PUBLIC' & is_primary & coord_resolved` → **19.015**.

### 3.2 Bảng cầu (demand, khóa `h3_r8` res 8)

| Artifact | Dòng (ô H3) | Cột | Ghi chú |
| --- | ---: | ---: | --- |
| `demand/demand_h3.parquet` | **255.480** | 24 | `pop` + **`pop_adj`** + 5 cột `road_*` (**E-DQ7b**) + **`road_access_nb1_m`/`road_access_nb2_m`/`access_tier`** (**E-DQ8a**) + **10 cột POI theo lớp tag** (**E-DQ7c**: `n_fuel` 4.830 · `n_parking_off` 2.147 · `n_parking_street` 149 · `n_mall` 252 · `n_dept_store` 1.133 · `n_supermarket` 1.386 · `n_market` 1.661 · `n_apartment` 5.157 · `n_apartment_complex` **1.370** · `apartment_levels_sum`) + `pop_pixel_implausible` (**E-DQ7f**) + `cell_state`/`frac_in_vn` (**E-DQ7a**). Σ`pop` = **97.563.106** (**E-DQ7e**, UNadj, bất biến); Σ`pop_adj` = **96.965.852** (**E-DQ7f** người ma + **E-DQ8b** dời dân ô roadless, −0,612%). ⚠️ `n_poi`/`n_parking` **khai tử** |
| `worldpop/worldpop_pop_h3.parquet` | 104.171 | 2 | chỉ ô có dân; Σ = **97.569.444** (**E-DQ7e**) — nguồn `pop` UN-anchored, KHÔNG đụng bởi 7f |
| `worldpop/worldpop_pop_report.json` | — | — | 3 cổng hiệu chuẩn (**E-DQ7e**): tổng khớp file UNadj đã băm · Spearman(cũ, mới) = **1,000000** · tỉ số theo pixel là hằng số (std **2,4e-08**) |
| `worldpop/worldpop_pop_adj_h3.parquet` | 107.942 | 14 | **E-DQ7f**: `pop` (bất biến) + `pop_adj` (đặt lại chỗ theo built-up) + `pop_src`/`pop_pixel_implausible` (139 ô) + chẩn đoán `n_px`/`max_px`/`top3_px_share`/`n_eff`/`pop_per_eff_px`/`pop_lat`/`pop_lon` + `maxa`/`danso`. +3.771 ô nhận (built-up, `pop=0`) |
| `worldpop/worldpop_pop_acc_h3.parquet` | **262.849** | 19 | **E-DQ8b**: `pop_adj` sau CẢ HAI phép đặt lại chỗ (7f dồn cục + 8b dời dân ô roadless) + `access_tier`/`road_access_m`/`road_access_nb*`/`built_ha` + `pop_src` (sổ cái: `MOVED_TO_ACCESSIBLE` **6.244** · `UNREPAIRED_NO_COMMUNE` 222 · `UNREPAIRED_NO_ACCESSIBLE_BUILTUP` 3 → E-DQ8c). Σ`pop_adj` = **96.965.852**; khối lượng ở ô không lối vào **1.241.833 → 42.249** (−96,6%). Đây là bảng `build_demand_h3` ĐANG nạp |
| `worldpop/worldpop_pop_adj_report.json` | — | — | 7 cổng **E-DQ7f**: `pop_bit_invariant`=0 · `retotal_reduces_mass`=486.399 người ma · `global_mass_accounted`=0,000 · drift 0,499% · join 99,84% |
| `vnsdi/communes.parquet` | **3.321** | 10 | **E-DQ7f**: ranh giới + dân số cấp xã (VNSDI 34DVHC, DANSO 2025) — nguồn cấp xã **độc lập** để kiểm chứng phân bổ. `maxa`/`tenxa`/`matinh`/`danso`/`dientich_km2`/`geom_wkb`. Σdanso 113,63 M (đăng ký 2025, +16,5% vs WorldPop) |
| `osm/osm_demand_components_h3.parquet` | 255.054 | 16 | thành phần OSM — cột **suy ra** từ 2 bảng lớp (10 POI + 5 `road_*`) |
| `osm/osm_roads_h3.parquet` | 255.052 | 29 | **bảng LỚP** (E-DQ7b): `m_`/`lane_m_`/`lane_obs_m_` × 9 lớp `highway` + `bridge_m` |
| `osm/osm_poi_h3.parquet` | 6.932 | 20 | **bảng LỚP** (E-DQ7c): `poi_<lớp>` + `poi_<lớp>_restricted` × 8 lớp tag + `poi_apartment_complex`/`_levels`/`_levels_obs` |
| `osm/osm_poi_points.parquet` | 37.349 | 15 | POI dạng điểm — `h3_r8`/`h3_r9`/`in_vn` (E-DQ7a) + `poi_class`/`poi_access`/`poi_physical_id`/`is_poi_primary`/`complex_id`/`levels` (E-DQ7c). **37.014 bản chính + 335 bản trùng** |
| `osm/osm_poi_recall.json` | — | — | độ phủ POI đo bằng nguồn độc lập (E-DQ7c): fuel **35,9%** / parking **8,6%**, kèm tỉ số thiên lệch theo tầng `pop` |

> ⚠️ `demand_h3` từng là bảng **duy nhất chưa có cổng QA** dù nó chính là hàm mục tiêu — đã có 7 cổng từ
> `E-DQ7a`/`E-DQ7b` + 8 cổng từ `E-DQ7c`. Audit 28/07 phát hiện **54,2% POI nằm ngoài lãnh thổ VN** (`E-DQ7a`,
> đã sửa), `road_len` sai ngữ nghĩa (`E-DQ7b`, đã sửa), `n_poi` lẫn đơn vị + POI thiếu/trùng (`E-DQ7c`, đã sửa)
> + proxy cầu chỉ đạt ρ = **0,33** so với trần đo được **0,865** của occupancy thật, **644** ô có sạc thật mà
> mọi input proxy = 0 (`E-DQ7d`, **chưa** — chẩn đoán 29/07, bàn giao **Kỳ**; con số cũ "ρ ≈ 0,30 · 983 ô" đã
> được đính chính).
> ✅ **`E-DQ7e` đã đóng 29/07** — đổi hẳn sang raster **UNadj** (Σ 99,627M → **97,569M**), thêm **3 cổng QA**;
> thứ hạng ô **bất biến** (Spearman cũ↔mới = **1,000000** trên 104.171 ô, tỉ số theo pixel là hằng số 0,979344
> với std 2,4e-08) ⇒ MCLP/`demand_weight` **không** phải chạy lại.
> ✅ **`E-DQ7f` đã xử lý 29/07 — thêm `pop_adj` + cờ `pop_pixel_implausible`.** Đo lại trên artefact UNadj:
> **139 ô / 745.283 dân** bị BSGM dồn vào 1–5 pixel (đỉnh **28.731/pixel**); ngưỡng ">48.000/km²" bắt **61 ô lõi
> TP.HCM có thật** và **0/139** ô hỏng (giao=0). Đối chiếu **VNSDI DANSO** (nguồn cấp xã độc lập): **63% khối
> lượng bị cờ là DỒN THỪA** (WorldPop>1,5×DANSO; đảo Hòn Nghệ 22×) → `pop_adj` rải lại theo built-up (RETOTAL 17
> xã / REPLACE 53 xã); `pop` giữ UN-anchored. Ô bị cờ trong top-500: **16→0**. Consumer XẾP HẠNG (MCLP, T4) dùng
> `pop_adj`; phát biểu tuyệt đối (`coverage_pop`) dùng `pop`.
> ⚠️ **Đọc `n_fuel`/`n_parking_off` như "số cây xăng/bãi đỗ" là SAI**: recall OSM đo được chỉ **35,9%** và
> **8,6%**; riêng parking còn **lệch đô thị** (tỉ số tầng cao/thấp = 2,67). Chúng là tín hiệu **tương đối**.
> **Chưa có cột `demand_weight`.** Xem [known-issues.md](../known-issues.md).

### 3.3 Bảng land-use (bộ lọc khả thi candidate — P5)

| Artifact | Dòng | Cột | Ghi chú |
| --- | ---: | ---: | --- |
| `landuse/landuse_h3.parquet` | **1.419.043** | 11 | Bảng **nhiều dòng nhất** (trừ TS) — WorldCover theo H3 toàn quốc |
| `landuse/buildable_h3.parquet` | **255.480** | 14 | Khớp 1-1 với `demand_h3`. **59.927** ô `buildable` (23%). Loại cứng: `NOT_BUILT_UP` 193.884 · `WATER` 7.262 · `WETLAND` 4.809 · **`ROAD_ACCESS_ISOLATED` 723** (**E-DQ8a** — đổi tên từ `NO_ROAD_ACCESS`, vốn loại 6.350 ô) · OSM MILITARY/PROTECTED/AIRPORT 594. Có cột **`access_tier`** để audit quyết định loại bỏ |
| `landuse/osm_substations.parquet` | 2.432 | 2 | Trạm biến áp (proxy lưới điện) |
| `landuse/exclusion_zones.parquet` | 694 | 2 | Ô H3 bị cấm |

### 3.4 Bảng registry official + xref

| Artifact | Dòng | Cột | Khóa |
| --- | ---: | ---: | --- |
| `vinfast_official/official_stations.parquet` | 23.247 | 18 | `store_id` |
| `vinfast_official/official_connectors.parquet` | **71.174** | 11 | `store_id` + `evse_idx` + `connector_id` |
| `vinfast_official/official_admin.parquet` | 23.240 | 7 | `store_id` → tỉnh/huyện/xã |
| `vinfast_official/official_xref.parquet` | 28.625 | 22 | `station_code` ↔ `official_store_id` (exact 19.427 · fuzzy 13) |

### 3.5 Bảng master, cung sạch & audit trail

| Artifact | Dòng | Cột | Vai trò |
| --- | ---: | ---: | --- |
| `stations_master_evcs.csv` | **28.625** | 33 | Master evcs khóa `station_code` (gồm 22 cột QA time-series) |
| `clean_supply.csv` | **19.015** | 14 | **Cung sạch cuối cùng** — input trực tiếp cho MCLP/coverage |
| `excluded.csv` | 492 | 7 | Dòng bị loại + lý do (xem bên dưới) |
| `crosssource_dedup_groups.csv` | 618 | 10 | E-DQ2 — nhóm trùng chéo nguồn |
| `edq1_suspect_stations.csv` | 796 | 17 | E-DQ1 — trạm nghi toạ độ sai |
| `fix_coords_flagged.csv` | 796 | 9 | E-DQ1 — nhật ký sửa toạ độ |
| `evcs_timeseries/*.csv` | **18.630.532** | 2 | **19.218 file**, 1 file/trạm (`timestamp`, `n_cars_charging`) |

**Đối soát cung: 19.507 − 492 = 19.015** ✓

| Lý do loại (`excluded.csv`) | Số dòng |
| --- | ---: |
| `CROSS_SOURCE_DUP` (E-DQ2) | 329 |
| `ACCESS_UNKNOWN` (P8) | 63 |
| `OUT_OF_SERVICE` (P8) | 42 |
| `COORD_PLACEHOLDER` (E-DQ1) | 38 |
| `RESTRICTED` (P8) | 20 |

---

## 4. `data/processed/` — model-ready (1,3 MB)

| Artifact | Dòng | Cột | Ghi chú |
| --- | ---: | ---: | --- |
| `candidate_sites.parquet` / `.geojson` | **1.711** | 14 / 7 | Candidate MCLP (P5) — `candidate_id`, `tier` T0–T4, `capex_class`, `penalty` |
| `covered0.parquet` / `.geojson` | **2.293** | 13 / 7 | Baseline hiện trạng (P8) — trạm active+public |

> GeoJSON là bản export rút gọn (7 property) của parquet — **không** phải dataset độc lập.
> Còn thiếu ở tầng này: `demand_weight`, bảng coverage/gap theo R, `demand_commune`, load PostGIS.

## 5. `data/external/`

| Artifact | Dòng | Cột |
| --- | ---: | ---: |
| `opex_electricity_tariff.{csv,json}` | 6 | 6 |

---

## 6. Bản đối chiếu đẩy lên Hugging Face

`vgreen-charging-siting-data/` là **bản mirror** của `data/` (không phải dataset thứ hai). Khác biệt duy nhất:
`interim/evcs_timeseries/` (19.218 file) được đóng gói thành **`evcs_timeseries.tar.zst`**, và `clean_supply.csv`
chưa được đồng bộ. Xem memory [[hf-dataset-sync]].

---

## 7. Lưu ý khi đọc số liệu

1. **Đừng dùng `wc -l` để đếm dòng CSV.** `name`/`address` có newline nhúng → `stations_master_evcs.csv` cho
   28.652 dòng (sai) thay vì **28.625** (đúng). Mọi số ở doc này đọc bằng parser.
2. **"Bảng" ≠ "file".** `canonical/stations` là 1 bảng nhưng 65 file parquet (Hive partition theo `province_code`);
   `evcs_timeseries/` là 1 dataset nhưng 19.218 file.
3. **Không cộng dồn dòng giữa các tầng.** Cùng một trạm xuất hiện ở raw → master → canonical → clean_supply;
   tổng 40,31 M là kiểm kê dung lượng, **không** phải số thực thể.
4. **Số cột sẽ trôi.** Mỗi issue E-DQ đóng lại thường thêm cột (E-DQ1 thêm 5 cột vào `stations`).
   Đối chiếu lại `schema-contract.md` khi số cột lệch.
