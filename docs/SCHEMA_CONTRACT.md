# SCHEMA CONTRACT

*Hợp đồng interop giữa **Data (Giang)** và **Model (Kỳ)**. Giang xây toàn bộ tầng dữ liệu; Kỳ tiêu thụ nó cho MCLP. File này là nguồn chân lý về schema, format và điểm bàn giao.*

## 1. Các quyết định đã chốt

| # | Vấn đề                              | Quyết định                                                                                                               | Hệ quả                                                                                                                     |
| - | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Demand proxy**                 | **Giang xây demand proxy từ nguồn công khai** (WorldPop + OSM + POI) theo lưới H3.                             | Giang sở hữu trọn khâu: crawl/tải nguồn → tính`demand_h3` → định nghĩa trọng số → trực quan hóa (mục 4). |
| 2 | **Đơn vị lưới không gian** | **H3 res 8** (~0,74 km²) là đơn vị chuẩn cho demand, candidate site và coverage.                               | Mọi join không gian dùng`h3_r8`. `h3_r9` chỉ để tham chiếu chi tiết hơn khi cần.                               |
| 3 | **Format bàn giao**             | **Parquet (Hive-partitioned) là canonical.** Đọc thẳng vào PostGIS / GeoPandas. CSV chỉ để xem nhanh (Excel). | Pipeline load đọc parquet, không phụ thuộc CSV export.                                                                  |

---

## 2. Schema theo bảng & vai trò

- 🟢 **Lõi (canonical input)** - load vào PostGIS, dùng trực tiếp.
- 🟡 **Nguồn demand** - đầu vào để dẫn xuất trọng số demand cho MCLP.
- ⚪ **Tham khảo / dẫn xuất** - snapshot; không dùng làm chân lý.

### 🟢 `stations`

| Cột                                                   | Kiểu                 | Vai trò trong bài toán                                 |
| ------------------------------------------------------ | --------------------- | --------------------------------------------------------- |
| `station_id`                                         | string                | **PK** (`vn-xxxx`)                                |
| `lat`, `lng`                                       | double                | Vị trí — candidate site & tính khoảng cách coverage |
| `admin_l1_code`, `province_name`                   | string                | Nối`agg_admin`, lọc theo tỉnh                        |
| `commune_name`, `commune_kind`                     | string                | Nối cấp xã                                             |
| `operator`                                           | string                | Phân biệt VGreen vs đối thủ                          |
| `current_type`                                       | string                | `AC`/`DC`                                             |
| `station_type`, `max_power_kw`, `total_power_kw` | string/double         | Cấu hình công suất                                    |
| `num_connectors`                                     | int                   | Số súng (đối chiếu với bảng`connectors`)         |
| `connector_types`                                    | list<string></string> | Chuẩn cắm                                               |
| `status`                                             | string                | Lọc trạm đang hoạt động                             |
| `confidence`, `freshness`, `quality_flags`       | double/list           | **Tín hiệu chất lượng**                        |
| `verified`, `provenance`, `match_method`, `official_*` | bool/string     | **Đối chiếu nguồn chính thức** (vinfastauto.com) — xác minh + xuất xứ |
| `h3_r8`                                              | string                | **Nối lưới** demand/coverage                     |

### 🟡 `demand_h3` — nhu cầu theo ô H3 (11 cột) · key: `h3_r8`

**Nguồn demand chính thức cho MCLP.** Chứa **thành phần thô** theo ô: `pop`, `road_len_m`, `road_len_mt_m`, `n_poi`, `n_parking`, `n_fuel` (+ `admin_l1_code`, `province_name`, `commune_name`, `commune_kind`).

> Bảng này **chưa có một con số "trọng số demand" duy nhất** cho mỗi ô — đó chính là phần Giang bổ sung (mục 4): `demand_weight = f(pop, road, poi, …)`.

### 🟡 `demand_commune` — nhu cầu theo xã(11 cột)/phường

Rollup cấp xã của `demand_h3` (+ `n_cells`). Dùng cho tổng hợp/kiểm tra, không phải đơn vị model.

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
  - *Kết quả model* (vị trí đề xuất + coverage) → **Kỳ** xuất theo cấu trúc thống nhất ở [problem-analysis.md](problem-analysis.md) mục 4.

## 6. Việc còn mở (cần theo dõi)

- [X] **Giang:** crawl nguồn cung từ evcs.vn → raw `data/raw/evcs/` + master interim `data/interim/stations_master_evcs.csv` (28.417 trạm, 0 orphan, QA PASS/WARN). Code `src/ev_siting/data/evcs/`, xem [crawler-evcs.md](crawler-evcs.md).
- [X] **Giang (22/07):** transform master (`station_code`, CSV) → parquet canonical `stations`/`connectors` (`station_id` `vn-`) đúng schema mục 3 (H3 res 8 tính từ lat/lng, `operator`, `connector_types`/`quality_flags` kiểu list, `confidence`/`freshness`). Output Hive-partitioned theo `province_code`: `data/interim/canonical/stations/` (19.507 dòng) + `.../connectors/` (24.415 dòng, tầng 2 nổ từ `evse_powers`). Code `src/ev_siting/data/evcs/transform_canonical.py` (`make canonical`). QA: PK unique, 0 orphan FK, `num_connectors == Σ count_total`. **Phạm vi: chỉ trạm sạc ô tô — MẶC ĐỊNH bỏ `BATTERY_SWAP` (9.118 trạm)**, giữ lại được bằng `--keep-bss`. **Còn lại:** cột admin (`admin_l1_code`/`province_name`/`commune_*`) để trống → enrich ở Step B.
- [X] **Giang:** tầng **OSM POI + road (trắc địa)** của `demand_h3` → `data/interim/osm/osm_demand_components_h3.parquet` (262.054 ô: `n_poi`/`n_parking`/`n_fuel` + `road_len_m`/`road_len_mt_m`, QA PASS). Code `src/ev_siting/data/osm/`, xem [crawler-osm.md](crawler-osm.md).
- [X] **Giang:** ghép `pop` (WorldPop 2020 constrained, ~100m) → `data/interim/worldpop/worldpop_pop_h3.parquet` (99,63M người / 104.171 ô) → **`demand_h3` thô** `data/interim/demand/demand_h3.parquet` (268.404 ô: `pop` + `road_len_*` + `n_poi/parking/fuel`). Code `src/ev_siting/data/worldpop/`, xem [crawler-worldpop.md](crawler-worldpop.md). **Còn lại:** enrich cột admin (`admin_l1_code`, `province_name`, `commune_*`) + chốt tập cột cuối → cập nhật mục 3.
- [X] **Giang (23/07):** crawl **nguồn chính thức VinFast** (vinfastauto.com, first-party) → `data/interim/vinfast_official/` (registry 23.247 trạm + 71.174 connector + admin). Xây **matcher 2 tầng** (`match_official.py`): `exact_code` (`station_code==store_id`, 19.427 trạm khớp tuyệt đối, toạ độ lệch ≤0,3 m) + `spatial_fuzzy` (BallTree haversine + rapidfuzz). Output `official_xref.parquet`. `transform_canonical` join vào `stations`: thêm cột **provenance** (`provenance`/`official_matched`/`match_method`/`official_store_id`/`match_dist_m`/`match_name_sim`/`official_charging_status`/`official_access_type`) + **định nghĩa lại** `verified` (corroboration first-party) và `confidence` (`0.4·completeness + 0.6·verification` cho trạm VinFast; `completeness` cho trạm ngoài phạm vi). Canonical: 19.432/19.507 verified, confidence TB 0,995. Doc [crawler-vinfast-official.md](crawler-vinfast-official.md).
- [ ] **Giang:** chốt công thức `demand_weight = f(pop, road_len_mt_m, n_poi, n_parking, n_fuel, …)` — trọng số từng thành phần (đưa vào Sprint 2).
- [ ] **Giang:** tính coverage với bán kính R = tham số MCLP (thay ngưỡng `has_station_5km` cố định).
- [ ] **Giang + Kỳ:** thống nhất tập **candidate sites** cho MCLP (trạm hiện có `stations` + tâm các ô H3 gap?) — điểm chạm interop.
- [X] **Giang:** viết data documentation mới cho tầng cung → [crawler-evcs.md](crawler-evcs.md). Còn lại: doc cho demand/coverage khi build xong.

*Thay đổi schema sau ngày chốt → cập nhật bảng mục 1 & 3, ghi ngày, báo người còn lại.*
