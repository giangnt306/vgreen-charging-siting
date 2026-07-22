# SCHEMA CONTRACT

*Hợp đồng interop giữa **Data (Giang)** và **Model (Kỳ)**. Giang tự xây toàn bộ tầng dữ liệu; Kỳ tiêu thụ nó cho MCLP. File này là nguồn chân lý về schema, format và điểm bàn giao.*

## 1. Các quyết định đã chốt

| # | Vấn đề                              | Quyết định                                                                                                               | Hệ quả                                                                                                                     |
| - | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1 | **Demand proxy**                 | **Giang xây demand proxy từ nguồn công khai** (WorldPop + OSM + POI) theo lưới H3.                             | Giang sở hữu trọn khâu: crawl/tải nguồn → tính`demand_h3` → định nghĩa trọng số → trực quan hóa (mục 4). |
| 2 | **Tầng `port`**               | **Bỏ.** Mô hình **2 tầng: `station → connector`**. `connector` = đơn vị **súng sạc**.       | PostGIS chỉ có 2 bảng lõi`station` / `connector`. Không tạo bảng `port`.                                        |
| 3 | **Đơn vị lưới không gian** | **H3 res 8** (~0,74 km²) là đơn vị chuẩn cho demand, candidate site và coverage.                               | Mọi join không gian dùng`h3_r8`. `h3_r9` chỉ để tham chiếu chi tiết hơn khi cần.                               |
| 4 | **Format bàn giao**             | **Parquet (Hive-partitioned) là canonical.** Đọc thẳng vào PostGIS / GeoPandas. CSV chỉ để xem nhanh (Excel). | Pipeline load đọc parquet, không phụ thuộc CSV export.                                                                  |

---

## 2. Dataset canonical & bố cục file

---

## 3. Schema theo bảng & vai trò

- 🟢 **Lõi (canonical input)** — Giang load vào PostGIS, dùng trực tiếp.
- 🟡 **Nguồn demand** — đầu vào để Giang dẫn xuất trọng số demand cho MCLP.
- ⚪ **Tham khảo / dẫn xuất** - snapshot tại thời điểm gold; **được tái tính** ở phía Giang/MCLP, không dùng làm chân lý.

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
| `h3_r8`                                              | string                | **Nối lưới** demand/coverage                     |

### ⚪ `nn_distance` — khoảng cách trạm gần nhất (12 cột) · 1–1 với `stations`

Dùng cho **EDA khoảng trống & phân tích cạnh tranh**. Cột chính: `nn_any_m`, `nn_competitor_m`, `nn_same_operator_m`, `n_within_2km`. Là dẫn xuất tại snapshot → nếu Giang thêm/sửa trạm thì phải tính lại.

### 🟡 `demand_h3` — nhu cầu theo ô H3 (11 cột) · key: `h3_r8`

**Nguồn demand chính thức cho MCLP.** Chứa **thành phần thô** theo ô: `pop`, `road_len_m`, `road_len_mt_m`, `n_poi`, `n_parking`, `n_fuel` (+ `admin_l1_code`, `province_name`, `commune_name`, `commune_kind`).

> Bảng này **chưa có một con số "trọng số demand" duy nhất** cho mỗi ô — đó chính là phần Giang bổ sung (mục 4): `demand_weight = f(pop, road, poi, …)`.

### 🟡 `demand_commune` — nhu cầu theo xã/phường (11 cột)

Rollup cấp xã của `demand_h3` (+ `n_cells`). Dùng cho tổng hợp/kiểm tra, không phải đơn vị model.

### ⚪ `coverage_gap` — khoảng trống phủ (18 cột) · key: `h3_r8`

Kế thừa cột demand + `nearest_station_m/id`, `nearest_dc_m`, `has_station_5km`, `is_gap_urban`, `is_gap_highway`, `is_low_confidence`.

> **Quyết định #4:** các cờ này tính với **ngưỡng cố định 5 km tại snapshot**. **Giang tái tính coverage/gap theo bán kính R của MCLP** — bảng này chỉ để đối chiếu/khởi tạo, không dùng làm coverage chính thức.

### ⚪ `agg_h3` — cung×cầu theo ô H3 (15 cột) · ⚪ `agg_admin` — theo tỉnh (7 cột)

Bảng tổng hợp phục vụ EDA/visualization nhanh. `agg_admin` tiện cho bảng KPI theo tỉnh (`n_stations`, `n_connectors`, `total_kw`, `n_dc`, `n_operators`).

### Quan hệ khóa

```
stations.station_id ──< connectors.station_id      (1 — nhiều)
stations.station_id ──  nn_distance.station_id      (1 — 1)
stations.h3_r8 ─┐
demand_h3.h3_r8 ┤
coverage_gap.h3_r8 ┼── nối theo H3 res 8
agg_h3.h3_r8 ───┘
*.admin_l1_code ──── agg_admin.admin_l1_code        (nối theo tỉnh)
```

---

## 4. Phân chia trách nhiệm & luồng dữ liệu

| Ai                                         | Sở hữu / bàn giao                                         | Nội dung                                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------ | ------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Giang** *(toàn bộ data layer)* | Dataset + PostGIS + demand + coverage + GeoJSON hiện trạng | ①**Tự crawl** `stations`/`connectors` (evcs.vn/PlugShare/OSM/Google). ② **Tự xây demand** theo H3 từ WorldPop/OSM/POI → `demand_h3` + `demand_weight` per cell. ③ **Tự tính coverage/gap** theo bán kính R của MCLP. ④ Validate → load PostGIS (`station`/`connector` + bảng H3). ⑤ GeoJSON hiện trạng + heatmap cho map. |
| **Giang → Kỳ**                     | Demand proxy + candidate sites (input MCLP)                  | `h3_r8 → demand_weight` + tập candidate sites — đầu vào MCLP tiêu thụ.                                                                                                                                                                                                                                                                                           |
| **Kỳ** *(model only)*             | MCLP + report                                                | Nhận demand proxy + candidate sites → chạy MCLP →**GeoJSON kết quả** (vị trí đề xuất + coverage theo ngân sách) → report cuối. Không đụng tới tầng dữ liệu.                                                                                                                                                                                    |
| **Kỳ → Giang**                     | GeoJSON kết quả model                                      | Vị trí đề xuất + coverage theo mức ngân sách (Sprint 2–3) để Giang tích hợp lên map.                                                                                                                                                                                                                                                                         |

> **Ranh giới rõ:** **Giang tự chủ toàn bộ tầng dữ liệu** (cung + cầu + coverage), Kỳ chỉ là "người tiêu thụ" schema này để chạy model. Hai điểm chạm duy nhất: (1) **Giang → Kỳ** demand proxy + candidate sites; (2) **Kỳ → Giang** GeoJSON kết quả. Schema ở file này là ngôn ngữ chung cho cả 2 điểm chạm.

---

## 5. Quy ước format

- **Parquet** = canonical (đọc bằng `pandas.read_parquet` / GeoPandas / DuckDB). CSV chỉ để xem.
- **GeoJSON:**
  - *Hiện trạng + heatmap demand* → **Giang** xuất (H3 cell → polygon lục giác qua thư viện `h3`; điểm trạm từ `lat`/`lng`).
  - *Kết quả model* (vị trí đề xuất + coverage) → **Kỳ** xuất theo cấu trúc thống nhất ở [problem-analysis.md](problem-analysis.md) mục 4.
- **Cột list trong CSV** nối bằng `|`.
- **CRS:** EPSG:4326 xuyên suốt.

---

## 6. Việc còn mở (cần theo dõi)

- [X] **Giang:** tự crawl nguồn cung từ evcs.vn → raw `data/raw/evcs/` + master interim `data/interim/stations_master_evcs.csv` (28.417 trạm, 0 orphan, QA PASS/WARN). Code `src/ev_siting/data/evcs/`, xem [crawler-evcs.md](crawler-evcs.md).
- [ ] 🔴 **Giang (chặn mới):** transform master (`station_code`, CSV) → parquet canonical `stations`/`connectors` (`station_id`) đúng schema mục 3 + layout mục 2.1 (H3, tiền tố `vn-`, map cột như trên).
- [X] **Giang:** tầng **OSM POI + road (trắc địa)** của `demand_h3` → `data/interim/osm/osm_demand_components_h3.parquet` (262.054 ô: `n_poi`/`n_parking`/`n_fuel` + `road_len_m`/`road_len_mt_m`, QA PASS). Code `src/ev_siting/data/osm/`, xem [crawler-osm.md](crawler-osm.md).
- [X] **Giang:** ghép `pop` (WorldPop 2020 constrained, ~100m) → `data/interim/worldpop/worldpop_pop_h3.parquet` (99,63M người / 104.171 ô) → **`demand_h3` thô** `data/interim/demand/demand_h3.parquet` (268.404 ô: `pop` + `road_len_*` + `n_poi/parking/fuel`). Code `src/ev_siting/data/worldpop/`, xem [crawler-worldpop.md](crawler-worldpop.md). **Còn lại:** enrich cột admin (`admin_l1_code`, `province_name`, `commune_*`) + chốt tập cột cuối → cập nhật mục 3.
- [ ] **Giang:** chốt công thức `demand_weight = f(pop, road_len_mt_m, n_poi, n_parking, n_fuel, …)` — trọng số từng thành phần (đưa vào Sprint 2).
- [ ] **Giang:** tính coverage với bán kính R = tham số MCLP (thay ngưỡng `has_station_5km` cố định).
- [ ] **Giang + Kỳ:** thống nhất tập **candidate sites** cho MCLP (trạm hiện có `stations` + tâm các ô H3 gap?) — điểm chạm interop.
- [X] **Giang:** viết data documentation mới cho tầng cung → [crawler-evcs.md](crawler-evcs.md) (thay [DATASET_EXPLAINED.md](DATASET_EXPLAINED.md) deprecated). Còn lại: doc cho demand/coverage khi build xong.

*Thay đổi schema sau ngày chốt → cập nhật bảng mục 1 & 3, ghi ngày, báo người còn lại.*
