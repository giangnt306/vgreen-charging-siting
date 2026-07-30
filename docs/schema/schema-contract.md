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
| `lat`, `lng`                                               | double                | Vị trí — candidate site & tính khoảng cách coverage                             |
| `admin_l1_code`, `province_name`                           | string                | Nối`agg_admin`, lọc theo tỉnh — **E-DQ3** (VNSDI, niên đại **2025-06-16**, 34 tỉnh). ⚠️ **KHÁC `province_code`** (hệ 63 tỉnh CŨ, prefix mã evcs) — giữ cả hai, xem `admin/province_crosswalk.csv` |
| `commune_code`, `commune_name`, `commune_kind`             | string                | Nối cấp xã (`commune_code` = `MAXA` VNSDI = **khoá join thật**); `commune_kind` ∈ `PHUONG`/`XA`/`DAC_KHU` |
| `admin_src`, `admin_dist_m`, `admin_verdict`               | string/double         | **E-DQ3** provenance & trọng tài: `admin_src` ∈ `inside`/`nearest`/`unresolved`; `admin_verdict` ∈ `NOT_FLAGGED`/`COORD_CONFIRMED`/`COORD_BAD`/`UNRESOLVED`/`NO_COORD`. **Bất biến: có nhãn ⟺ `coord_resolved`** |
| `operator`                                                   | string                | Phân biệt VGreen vs đối thủ                                                      |
| `vehicle_class`                                              | string                | **`CAR`/`UNVERIFIED`/`UNKNOWN`** — lọc nhiễm xe máy (**P7**); `CAR` = mọi connector là chuẩn ô tô (CCS2/Type2) theo registry chính thức |
| `current_type`                                               | string                | **Tầng LIVE.** `AC`/`DC`/`MIXED` — suy từ chuẩn cắm chính thức, không từ power tier (**P7**: 20-22 kW là DC CCS2). ⚠️ Sai ở **531** trạm khi cả một loại dòng bị tắt khỏi mảng sống → dùng `current_type_asset` để **phân tầng** (**E-DQ4**) |
| `station_type`, `max_power_kw`, `total_power_kw`         | string/double         | **Tầng LIVE** — cấu hình ĐANG BÁO CÁO. `total_power_kw` = Σ nameplate **từng súng** ⇒ **phóng đại 1,82×** so với công suất điểm; dùng `site_power_kw` cho công suất điểm (**E-DQ4**) |
| `num_connectors`                                             | int                   | **Tầng LIVE** — số súng **ĐANG BÁO CÁO** (đối chiếu bảng `connectors`). ⚠️ **KHÔNG** phải số súng lắp đặt: `evsePowers` là mảng trạng thái sống ⇒ đọc thiếu ở **1.568** trạm, `0` ở **282** trạm. Dùng `n_guns_installed` (**E-DQ4**) |
| `connector_types`                                            | list<string></string> | Nhãn tier công suất (evcs.vn không lộ chuẩn cắm — xem `connectors.connector_standard`) |
| `n_guns_installed`                                           | Int64 (nullable)      | **Tầng ASSET (E-DQ4).** Số súng **LẮP ĐẶT** = hợp `max(registry, evcs Σ totalEvse, ts_val_max)` — cả ba nguồn đều là **chặn DƯỚI**. `NULL` ⇔ `config_src=UNKNOWN` |
| `max_power_kw_asset`, `nameplate_power_kw`                | double                | **Tầng ASSET.** Súng nhanh nhất · Σ nameplate **từng súng** (đối chứng cho `site_power_kw`) |
| `site_power_kw`                                              | double                | **Tầng ASSET — công suất ĐIỂM sạc:** Σ theo **tủ** (`physical_reference`), vì hai hồng trên một tủ 180 kW cấp 180 kW chứ không phải 360. **Số công bố được** cho công suất lắp đặt (**~1,73 GW** toàn quốc). ⚠️ Cần 1 lần đối chiếu spec phần cứng trước khi công bố |
| `current_type_asset`                                         | string                | **Tầng ASSET.** `AC`/`DC`/`MIXED` suy từ registry — **cột phân tầng ĐÚNG cho E-DQ7d** (`occ_mean` trên tập cung: AC 0,121 · DC 1,556 · MIXED 1,898 — so với tầng LIVE 0,122 / 1,652 / 1,831) |
| `config_src`                                                 | string                | `OFFICIAL` 19.243 / `EVCS_LIVE` 7 / `TELEMETRY_BOUND` 1 (chỉ có nhân chứng telemetry = chặn dưới) / `UNKNOWN` 256 |
| `config_resolved`                                            | bool                  | **Cổng của mọi mẫu số CÓ TRỌNG SỐ CÔNG SUẤT** (E-DQ4): `True` ⇔ `config_src ∈ {OFFICIAL, EVCS_LIVE}`. `False` ⇒ giữ làm điểm phủ/T0 nhưng **loại khỏi kế toán công suất** và **công bố số bị loại** |
| `n_guns_imputed`                                             | Int64 (nullable)      | Median theo tỉnh × loại trạm cho dòng `UNKNOWN` — **CHỈ** để phân tích độ nhạy, **không bao giờ** là giá trị mặc định |
| `status`                                                     | string                | **Nguồn evcs thô** (snapshot telemetry: Available/AllBusy/Maintaining/OutOfService) — dùng `op_status` đã resolve |
| `is_public`                                                  | bool                  | **Nguồn evcs thô** access — dùng `access` đã resolve                            |
| `op_status`                                                  | string                | **`OPERATIONAL`/`MAINTENANCE`/`OUT_OF_SERVICE`/`UNKNOWN`** — trạng thái vận hành resolve **official-first** (**P8**) |
| `access`                                                     | string                | **`PUBLIC`/`RESTRICTED`/`UNKNOWN`** — access resolve **official-first** (**P8**) |
| `is_operational`                                            | bool                  | **Lọc cung cứng (P8):** `False` ⇔ `op_status=OUT_OF_SERVICE` (trạm đã ngừng, loại khỏi cung/anchor T0). MAINTENANCE/UNKNOWN giữ + flag |
| `confidence`, `freshness`, `quality_flags`               | double/list           | **Tín hiệu chất lượng** (P8 flags: `NOT_OPERATIONAL`/`UNDER_MAINTENANCE`/`STATUS_UNKNOWN`/`NON_PUBLIC`/`ACCESS_UNKNOWN`; **E-DQ4** flags: `CONFIG_TRUNCATED` 1.568 / `CURRENT_TYPE_CORRECTED` 531 / `POWER_CABINET_SHARED` 4.317 / `CONFIG_UNKNOWN` 256 / `CONFIG_LOWER_BOUND` 1) |
| `verified`, `provenance`, `match_method`, `official_*` | bool/string           | **Đối chiếu nguồn chính thức** (vinfastauto.com) — xác minh + xuất xứ |
| `h3_r8`                                                      | string                | **Nối lưới** demand/coverage                                                 |

### 🟢 `connectors` — tầng 2, 1 dòng/nhóm công suất · FK `station_id`

`connector_id`, `station_id` (FK), `power_kw`, `current_type`, `connector_label`, `count_total`, `count_available` + **2 cột chuẩn cắm (P7):**

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `connector_standard` | string | `CCS2` (`IEC_62196_T2_COMBO`) / `TYPE2` (`IEC_62196_T2`) / `UNKNOWN` (trạm evcs-only) — **chuẩn cắm chính thức** từ `official_connectors.standard`, join `store_id==station_code` |
| `vehicle_class` | string | `CAR` (CCS2/Type2) / `UNVERIFIED` — chống nhiễm xe máy điện (**P7**) |

> **P7 — chuẩn cắm thay power tier:** evcs.vn chỉ lộ **công suất**, không lộ chuẩn cắm → tier `AC/DC` theo ngưỡng 25 kW gán **sai** 20-22 kW thành AC (thực tế DC CCS2). Nguồn sự thật là VinFast official (`official_connectors.standard`); 100% connector khớp là chuẩn **ô tô** (CCS2/Type2) → không còn nhiễm 2 bánh sau khi lọc BSS.

### 🟡 `demand_h3` — nhu cầu theo ô H3 (16 cột) · key: `h3_r8`

**Nguồn demand chính thức cho MCLP.** Chứa **thành phần thô** theo ô: `pop`, `road_access_m`, `road_len_m`, `road_lane_mw_m`, `road_lane_ar_m`, `road_bridge_m`, **10 cột POI theo lớp tag** — `n_fuel`, `n_parking_off`, `n_parking_street`, `n_mall`, `n_dept_store`, `n_supermarket`, `n_market`, `n_apartment`, `n_apartment_complex`, `apartment_levels_sum` (**E-DQ7c**; `n_poi`/`n_parking` **khai tử**).

**Nhãn hành chính (E-DQ3, 30/07):** `admin_l1_code`, `province_name`, `commune_code`, `commune_name`, `commune_kind`
+ `admin_frac` (tỉ lệ diện tích của xã thắng) + `n_communes` (số xã ô chạm) — **255.298/255.480** ô.
⚠️ **NHÃN ≠ PHÂN BỔ.** Nhãn = **argmax diện tích**, dùng để lọc/hiển thị. **Cấm** `groupby(commune_name).sum()`:
**61.648 ô (40,0% dân số)** vắt qua ≥ 2 xã (tối đa 6). Cộng khối lượng phải đi qua bảng phân bổ có trọng số
`data/interim/admin/cell_commune.parquet` (Σw = 1 mỗi ô) — hoặc dùng thẳng rollup `admin/demand_commune.parquet`.

**Clip lãnh thổ (E-DQ7a, 28/07):** bảng chỉ chứa ô **thuộc lãnh thổ VN** (268.404 → **254.035** ô) với 2 cột kèm theo:

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `cell_state` | string | `INSIDE` (lục giác nằm trọn trong VN) \| `BORDER` (vắt biên — **giữ**, 2.977 ô) |
| `frac_in_vn` | double | tỉ lệ diện tích ô thuộc VN (1,0 với `INSIDE`) — để `demand_weight` chia tỉ lệ ô biên |

**Bậc lối vào (E-DQ8a, 30/07)** — 3 cột nữa, và chúng **thay** `road_access_m <= 0` làm bộ lọc lối vào:

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `road_access_nb1_m` | double | Σ `road_access_m` của **vành 1** (6 ô kề, **trừ** chính ô) |
| `road_access_nb2_m` | double | Σ `road_access_m` của **vành 2** (đĩa k=2, trừ chính ô) |
| `access_tier` | string | `DIRECT` (đường trong ô) \| `ADJACENT` (vành 1, **4.939 ô**) \| `NEAR` (vành 2, 940 ô) \| `ISOLATED` (không có, **595 ô**) |

> ⚠️ **Consumer phải đổi:** `buildable_h3` loại cứng theo `access_tier == 'ISOLATED'`, **không** theo
> `road_access_m <= 0` — bộ lọc cũ loại 6.350 ô mà **4.862 ô trong đó có đường ở ô KỀ** (tâm 2 ô res 8 cách
> 0,98 km). Neo ngoại vi: **15 trạm đang vận hành** nằm ở ô `ADJACENT`. `NO_ROAD_ACCESS` → đổi tên
> `ROAD_ACCESS_ISOLATED` (đổi tên thay vì đổi nghĩa ngầm — cùng nguyên tắc `road_len_mt_m` của E-DQ7b).
> `access_tier` cũng được xuất ra `buildable_h3` để audit được quyết định loại bỏ.

> ✅ **`E-DQ8b` (30/07) — `pop_adj` nay đã qua HAI phép đặt lại chỗ.** Nguồn của `pop`/`pop_adj` là
> `worldpop_pop_acc_h3.parquet` (7f dồn cục **+** 8b dời dân ô roadless); `build_demand_h3` nạp theo thang
> **8b → 7f → 7e** và in cảnh báo ở mỗi bậc lùi. Khối lượng ở ô không lối vào: **1.241.833 → 42.249**
> (−96,6%). Σ`pop_adj` quốc gia **96.965.852** (−0,612% so `pop`, có cổng canh <1%); Σ`pop` **bất biến từng
> bit** ở **97.563.106**. Cột `pop_src` trong artefact nguồn là **sổ cái** của mọi lần dời
> (`MOVED_TO_ACCESSIBLE` 6.244 ô · `UNREPAIRED_*` 225 ô → E-DQ8c).

> Ô `OUTSIDE` tách sang `data/interim/demand/demand_h3_clipped_out.parquet` (cách ly, không xoá) để đối soát `input = output + clipped`. Các cột POI chỉ đếm điểm có `in_vn=True` (clip ở mức điểm, **E-DQ7a**) **và** `is_poi_primary=True` (khử trùng node/way, **E-DQ7c**). ⚠️ Recall OSM đo được: fuel **35,9%**, parking **8,6%** — đây là tín hiệu **tương đối**, không phải số đếm thực địa.

> ✅ **`E-DQ7e` đã đóng 29/07 — `pop` nay dẫn từ raster UNadj.** Σ`pop` (`demand_h3`) **99.620.916 → 97.563.106**
> (−2,07%). Thứ hạng ô **bất biến từng bit** (Spearman cũ↔mới = **1,000000** trên 104.171 ô; tỉ số theo pixel là
> hằng số 0,979344, std 2,4e-08) ⇒ mọi consumer **xếp hạng** (MCLP, `demand_weight`) **không** bị ảnh hưởng; mọi
> consumer **tuyệt đối** (`coverage_pop`, đối chiếu GSO) phải dùng con số mới.
>
> ✅ **`E-DQ7f` đã xử lý 29/07 — thêm `pop_adj` + cờ `pop_pixel_implausible`.** BSGM dồn cả xã vào 1–5 pixel
> (đo lại trên artefact UNadj: **139 ô / 745.283 dân**, KHÔNG phải 146/792k của bản pre-7e). Đối chiếu **VNSDI
> DANSO** (nguồn dân số cấp xã độc lập, `data/vnsdi/`): **63% khối lượng bị cờ là DỒN THỪA** (WorldPop > 1,5×
> DANSO; 16 ô có 1 ô nhiều dân hơn cả xã — cụm đảo Hòn Nghệ/Sơn Hải 22×), **không** phải chỉ sai chỗ.

| Cột (E-DQ7f) | Kiểu | Vai trò |
| --- | --- | --- |
| `pop` | double | **GIỮ NGUYÊN** — WorldPop UNadj, UN-anchored. Dùng cho phát biểu **tuyệt đối** (`coverage_pop`, đối chiếu GSO). Cổng `pop_total_matches_unadj` của E-DQ7e còn xanh. |
| `pop_adj` | double | pop **đã đặt lại chỗ** theo built-up WorldCover trong ranh giới xã (RETOTAL hạ về 0,859·DANSO khi WorldPop>1,5×DANSO; REPLACE giữ tổng, chỉ đổi chỗ). Dùng cho consumer **XẾP HẠNG** (MCLP `demand_weight`, T4 gap-fill). Σ quốc gia thấp hơn `pop` **0,499%** (người ma gỡ khỏi đảo). |
| `pop_pixel_implausible` | bool | cờ ô dồn cục (139 ô). T4 gap-fill LOẠI ô này nếu không có đường trục/POI xác nhận. |

> Chi tiết + 7 cổng QA: [known-issues.md — E-DQ7f](../known-issues.md#e-dq7f--pop-phân-bổ-sai-chỗ-trong-ô-dasymetric-spike-bước-9).
> Ô đảo Hòn Nghệ `8865a30cd5f…`: `pop` 28.731 → `pop_adj` 493 (xã chỉ 2.546 dân); ô bị cờ trong top-500 quốc
> gia: **16 → 0** theo `pop_adj`.

> Bảng này **chưa có một con số "trọng số demand" duy nhất** cho mỗi ô — đó chính là phần Giang bổ sung (mục 4): `demand_weight = f(pop, road, poi, …)`.

### 🟢 `candidate_sites` — tập điểm ứng viên cho MCLP (14 cột) · PK: `candidate_id`

**Đầu vào candidate cho MCLP** (`data/processed/candidate_sites.parquet` + `.geojson`). Mỗi dòng = 1 điểm thực,
**unique theo `h3_r8`** (≤1 candidate/ô — tránh tie-degenerate, biến thể ẩn **P4**).

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `candidate_id` | string | **PK** (`cand-<city>-<idx>`) |
| `lat`, `lng` | double | toạ độ thật (explainability) |
| `h3_r8` | string | ô coverage (**unique**) |
| `province_code` | string | null trên candidate không phải trạm — nhãn hành chính lấy từ `demand_h3` qua `h3_r8` (**E-DQ3**, 30/07) |
| `tier` | string | T0–T4 (nguồn anchor) |
| `anchor_type` | string | `existing_station`/`parking`/`fuel`/`mall`/`retail`/`apartments`/`gapfill_synthetic` |
| `source_ref` | string | `station_id` \| `osm_type/osm_id` \| `synthetic:<h3>` |
| `is_existing` | bool | T0 → CapEx=0 Sprint 3 (incumbent bắt buộc mở) |
| `built_up_frac`, `dist_substation_m`, `penalty` | double | tín hiệu land-use / đấu nối lưới |
| `capex_class` | string | `low`/`mid`/`high` — ràng buộc ngân sách Sprint 3 |
| `exclusion_flags` | list | audit (rỗng — đã loại ô cấm) |

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
- [X] **Giang (22/07):** transform master (`station_code`, CSV) → parquet canonical `stations`/`connectors` (`station_id` `vn-`) đúng schema mục 3 (H3 res 8 tính từ lat/lng, `operator`, `connector_types`/`quality_flags` kiểu list, `confidence`/`freshness`). Output Hive-partitioned theo `province_code`: `data/interim/canonical/stations/` (19.507 dòng) + `.../connectors/` (24.415 dòng, tầng 2 nổ từ `evse_powers`). Code `src/ev_siting/data/evcs/transform_canonical.py` (`make canonical`). QA: PK unique, 0 orphan FK, `num_connectors == Σ count_total`. **Phạm vi: chỉ trạm sạc ô tô — MẶC ĐỊNH bỏ `BATTERY_SWAP` (9.118 trạm)**, giữ lại được bằng `--keep-bss`. **E-DQ3 (30/07):** cột admin **đã enrich** từ ranh giới xã VNSDI (19.453/19.507 có nhãn) + trọng tài toạ độ — xem `src/ev_siting/data/admin/`.
- [X] **Giang:** tầng **OSM POI + road (trắc địa)** của `demand_h3` → `data/interim/osm/osm_demand_components_h3.parquet` (255.054 ô: 10 cột POI theo lớp tag — **E-DQ7c** + 5 cột `road_*` — **E-DQ7b**; cả hai **suy ra** từ bảng lớp `osm_poi_h3`/`osm_roads_h3`, QA PASS). Code `src/ev_siting/data/osm/`, xem [crawler-osm.md](../sources/osm.md).
- [X] **Giang:** ghép `pop` (WorldPop 2020 constrained **UNadj**, ~100m — **E-DQ7e** 29/07) → `data/interim/worldpop/worldpop_pop_h3.parquet` (**97,57M** người / 104.171 ô) → **`demand_h3` thô** `data/interim/demand/demand_h3.parquet` (254.035 ô sau clip lãnh thổ: `pop` + 5 cột `road_*` + 10 cột POI). Code `src/ev_siting/data/worldpop/`, xem [crawler-worldpop.md](../sources/worldpop.md). **E-DQ3 (30/07):** nhãn admin **đã enrich** cho lưới (`make admin-grid`) + rollup `demand_commune` (3.321 xã / 34 tỉnh).
- [X] **Giang (23/07):** crawl **nguồn chính thức VinFast** (vinfastauto.com, first-party) → `data/interim/vinfast_official/` (registry 23.247 trạm + 71.174 connector + admin). Xây **matcher 2 tầng** (`match_official.py`): `exact_code` (`station_code==store_id`, 19.427 trạm khớp tuyệt đối, toạ độ lệch ≤0,3 m) + `spatial_fuzzy` (BallTree haversine + rapidfuzz). Output `official_xref.parquet`. `transform_canonical` join vào `stations`: thêm cột **provenance** (`provenance`/`official_matched`/`match_method`/`official_store_id`/`match_dist_m`/`match_name_sim`/`official_charging_status`/`official_access_type`) + **định nghĩa lại** `verified` (corroboration first-party) và `confidence` (`0.4·completeness + 0.6·verification` cho trạm VinFast; `completeness` cho trạm ngoài phạm vi). Canonical: 19.432/19.507 verified, confidence TB 0,995. Doc [crawler-vinfast-official.md](../sources/vinfast-official.md).
- [ ] **Giang:** chốt công thức `demand_weight = f(pop, road_lane_mw_m, road_lane_ar_m, n_fuel, n_parking_off, n_mall, n_dept_store, n_supermarket, n_market, n_apartment_complex, …)` — trọng số từng thành phần (đưa vào Sprint 2). ⚠️ Cân nhắc **calibrate trọng số bằng 18,6M điểm occupancy** thay vì đặt tay (**P1**); weight `pop` theo proxy sở hữu ô tô, không dùng tổng dân số thô (**P11**); giữ demand **ngoại sinh** — không đưa hiện diện trạm vào feature (**P2**). Xem [known-issues.md](../known-issues.md).
- [ ] **Giang:** tính coverage với bán kính **R = 3 km (baseline)**, quét {1,5 · 2 · 3 · 5} km (thay ngưỡng `has_station_5km` cố định). ⚠️ **Gate bắt buộc: FAIL nếu `R ≤ d` (0,98 km) · WARN nếu `R < 2d` (1,95 km)** — dưới ngưỡng đó mỗi candidate chỉ phủ chính ô nó → MCLP suy biến thành `sort top-p`. Xem **P4** trong [known-issues.md](../known-issues.md).
- [X] **Giang (24/07):** tập **candidate sites** cho MCLP → `data/processed/candidate_sites.{parquet,geojson}` (điểm chạm interop thứ 3). Mô hình **lai**: điểm thực nhưng **≤1 candidate/ô H3** (tránh tie-degenerate — biến thể ẩn **P4**); phân tầng **T0 trạm hiện có** (`is_existing=True`, incumbent bắt buộc mở — ràng buộc thiết kế) · T1 `PARKING_OFF`/`FUEL` · T2 `MALL`/`DEPT_STORE`/`SUPERMARKET`/`MARKET`/`APARTMENT` (**E-DQ7c**: 1 anchor/khu chung cư, bỏ đỗ ven đường + bãi đỗ `RESTRICTED`) · T4 gap-fill synthetic. Lọc **khả thi** qua `buildable_h3` (ESA WorldCover 10m + OSM military/protected/water + `road_access_m≤0` — **E-DQ7b**) — loại hồ/núi/đất cấm/không đường (**P5**, **P9**). QA gate 5 cổng (upper-bound coverage ≥90% · freedom ≥5×p · size ≤3000 · anti-degenerate ≥0,9 · `R>d`). MVP Hà Nội: 1.672 candidate, 5/5 PASS. Schema đầy đủ + cột (`is_existing`/`capex_class` cho ràng buộc ngân sách Sprint 3) → [candidate-sites.md](../data-layer/candidate-sites.md).
- [X] **Giang (24/07):** **chốt xử lý P4** — giữ lưới `H3 res 8`, chốt **R = 3 km**. Đã dựng thử `res 7` (`demand_h3` 54.618 ô) rồi **rollback**: res 7 làm ô to gấp 7× (`d` 0,98 → 2,59 km), đẩy tỷ lệ `R/d` sai hướng và làm **mọi R trong (2,59; 4,48) km cho kết quả y hệt nhau** → mất khả năng quét độ nhạy theo R. Toàn bộ dataset đã rebuild lại ở res 8 và **khớp bit-level** với snapshot gốc (`demand_h3` 268.404 ô · `pop` 99,63M · road 730.718 km); QA OSM PASS. Đồng thời sửa lỗi hình học: "800 m" cũ là do **nhầm bán kính nội tiếp với cạnh** lục giác — giá trị đúng `d = a·√3 = 2r = 0,98 km`.
- [X] **Giang:** viết data documentation mới cho tầng cung → [crawler-evcs.md](../sources/evcs.md). Còn lại: doc cho demand/coverage khi build xong.

*Thay đổi schema sau ngày chốt → cập nhật bảng mục 1 & 3, ghi ngày, báo người còn lại.*
