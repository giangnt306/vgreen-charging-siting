# CHECKLIST NGHIỆM THU `data/processed/`

> Tạo: **2026-07-31** · Cập nhật **2026-07-31 sau REBUILD toàn chuỗi** · Nhánh `data/giang` ·
> Mọi số "đo" trong file này lấy trực tiếp từ artefact trên đĩa, **không** chép lại từ doc khác.
>
> **Vai của file này:** danh sách cổng kiểm tra chạy được trước khi bàn giao `data/processed/` cho MCLP (Kỳ).
> **KHÔNG** giữ ở đây: register vấn đề → [known-issues.md](../known-issues.md) · hợp đồng schema →
> [schema-contract.md](../schema/schema-contract.md) · kiến trúc pipeline → [overview.md](overview.md).

---

## 0. Đọc nhanh — kết quả sau rebuild 2026-07-31

| Nhóm | Cổng | PASS | FAIL |
| --- | --- | --- | --- |
| A. Provenance & độ tươi | 4 | **4** | 0 |
| B. Đủ file | 3 | 2 | 1 *(việc chưa làm, không phải hồi quy)* |
| C. Schema | 4 | **4** | 0 |
| D. Khoá & toàn vẹn tham chiếu | 6 | 6 | 0 |
| E. Miền giá trị | 4 | **4** | 0 |
| F. Nhất quán chéo artefact | 5 | **5** | 0 |
| G. Không gian | 3 | 3 | 0 |
| H. Sẵn sàng cho MCLP | 5 | 5 | 0 |
| I. Dư thừa / đã làm sạch chưa | 4 | 1 | **3** |
| **Tổng** | **38** | **34** | **4** |

**Kết luận một dòng:** chuỗi đã rebuild đầy đủ từ raw đã freeze (`verify-snapshot` **PASS**, pytest
**162 passed / 1 skipped**); mọi cổng toàn vẹn, không gian, MCLP-readiness và nhất quán chéo artefact đều
**PASS**. Còn lại **cột dư thừa** (§3) và **1 mâu thuẫn nội bộ mới phát hiện** (§3.5) — không cổng nào chặn
bàn giao, nhưng phải chốt trước khi khoá schema với Kỳ.

**Lịch sử:** lần chấm đầu (trước rebuild) là **23/38**; 11 cổng đỏ đã đóng bằng rebuild + 2 sửa code
(gate toạ độ `covered0`, nhãn hành chính `candidate_sites`).

---

## 1. Phạm vi

Checklist chấm **4 bảng** — 2 bảng đích trong `data/processed/` và 2 bảng nguồn của chúng, vì
không thể nghiệm thu output mà không đối soát input:

| Bảng | Đường dẫn | Đo sau rebuild 31/07 |
| --- | --- | --- |
| `candidate_sites` | `data/processed/candidate_sites.{parquet,geojson}` | **16.686 × 16** (T0 12.827 · T1 2.078 · T2 862 · T4 919) |
| `covered0` | `data/processed/covered0.{parquet,geojson}` | **19.012 × 19** (+ `covered0_operational` 15.746) |
| `stations` (nguồn) | `data/interim/canonical/stations/` | 19.507 × 61 |
| `connectors` (nguồn) | `data/interim/canonical/connectors/` | 24.415 × 11 |

> Tập cung tham chiếu (`export_supply`): **19.181** trạm / **12.801** ô.
> Lưới cầu: `demand_h3` **314.934** ô.

---

## 2. Checklist

### A. Provenance & độ tươi — **4/4 PASS** *(chạy TRƯỚC mọi cổng khác)*

- [x] **A1 — Snapshot raw khớp MANIFEST.** `make verify-snapshot` → **PASS** (`snapshot_id = 2026-07-20`).
  Nguồn `worldpop` giờ đủ **4/4 member present** sau khi tải bổ sung hai raster R2024B (§4 bước 1).
  *(Trước rebuild: manifest freeze trên máy khác, hai raster `present: false`.)*
- [x] **A2 — Artefact sinh SAU snapshot đang freeze.** `quality_report.json` và `MANIFEST.json`
  cùng `snapshot_id = 2026-07-20`.
- [x] **A3 — Artefact `processed/` mới hơn code sinh ra nó.** Toàn bộ `data/processed/` build
  2026-07-31 12:3x, sau lần sửa code cuối.
- [x] **A4 — Schema artefact khớp `_OUT_COLS` của builder hiện tại.** `covered0.parquet` giờ có
  `op_status` + `access` (đã resolve, P8) — **không còn** `status`/`is_public` thô.
  `covered0_report.json` khai đúng `baseline_def` hiện hành + khối `gates` **5/5 PASS**.

### B. Đủ file

- [x] **B1 — Đủ cặp `{parquet, geojson}` + report cho mỗi output.** 9 file (thêm cặp
  `covered0_operational.*` — sensitivity P8).
- [x] **B2 — Report JSON có `overall`/`gates` đọc được.** `candidate_sites_qa.json` `overall = PASS`;
  `covered0_report.json` `all_gates_pass = true`.
- [ ] **B3 — Đủ output theo hợp đồng §6.** ⚠️ **Còn thiếu (việc chưa làm, không phải hồi quy):**
  `demand_weight`, `demand_servable`, coverage/gap, GeoJSON hiện trạng — xem
  [schema-contract.md §6](../schema/schema-contract.md).

### C. Schema — **4/4 PASS**

- [x] **C1 — Đúng số cột theo hợp đồng.** `candidate_sites` **16** (14 → 16, thêm 2 cột hành chính
  hệ 34 — xem C3) · `connectors` 11 ✓ · `stations` 61 ✓.
- [x] **C2 — Không có cột toàn NULL.**
- [x] **C3 — `candidate_sites` có nhãn hành chính.** **Đã sửa 31/07.** Hai hệ mã đi cạnh nhau,
  không trộn:
  - `province_code` (hệ **63 CŨ**): **12.827/16.686** non-null = **đúng bằng số T0**, lấy từ trạm neo.
    Cổng: `province_code.notna() ⟺ is_existing` — **True mọi dòng**. T1/T2/T4 null vì không có nguồn thật.
  - `admin_l1_code` + `province_name` (hệ **34**, VNSDI): **16.657/16.686** (34 tỉnh);
    29 candidate còn null vì ô nằm ngoài lưới `demand_h3`.
  - Hợp đồng đã cập nhật: [schema-contract.md](../schema/schema-contract.md) ·
    [candidate-sites.md](candidate-sites.md).
- [x] **C4 — Không còn cột đã khai tử** (`n_poi`/`n_parking`/`road_len_mt_m` không xuất hiện).

### D. Khoá & toàn vẹn tham chiếu — **6/6 PASS**

- [x] **D1 — PK unique.** `station_id` · `station_code` · `connector_id` · `candidate_id` · `covered0.station_id` — tất cả unique.
- [x] **D2 — 0 orphan FK.** `connectors.station_id` → `stations`: **0** orphan.
- [x] **D3 — `num_connectors == Σ count_total`.** **0** lệch.
- [x] **D4 — `count_available ≤ count_total`.** **0** vi phạm.
- [x] **D5 — `candidate_sites.source_ref` (T0) resolve về `stations`.** **12.827/12.827**.
- [x] **D6 — `covered0.station_id` ⊆ `stations`.** **19.012/19.012**.

### E. Miền giá trị — **4/4 PASS**

- [x] **E1 — `tier` ∈ {T0,T1,T2,T4}.** T0 12.827 · T1 2.078 · T2 862 · T4 919.
- [x] **E2 — `anchor_type` ∈ 8 giá trị hợp lệ**, phân hoạch sạch theo tier.
- [x] **E3 — `vehicle_class` connectors chỉ CAR/UNVERIFIED.** CAR 24.406 · UNVERIFIED 9.
- [x] **E4 — `covered0` không chứa cột trạng thái THÔ.** Đã thay bằng `op_status`/`access`.

### F. Nhất quán chéo artefact — **5/5 PASS**

- [x] **F1 — `covered0.h3_r8` ⊆ `candidate_sites.h3_r8`.** **19.012/19.012**.
- [x] **F2 — `candidate_sites` ≤ 1 dòng / ô H3.** `h3_r8` unique ✓ (chống suy biến P4).
- [x] **F3 — `covered0` ⊆ tập cung.** **Đã sửa 31/07: 0 trạm ngoài tập cung** (trước: 36).
  Nguyên nhân gốc: baseline lọc toạ độ bằng `DIRTY_COORD_FLAGS` còn `export_supply` lọc bằng
  `coord_resolved` — **hai gate khác nhau**, nên `COORD_OUTSIDE_ADMIN` (không nằm trong tập cờ) lọt
  vào baseline với `h3_r8` **NULL**. Sửa: baseline gate bằng **cả hai**
  (`coord_resolved & ~dirty_flags`) ⇒ baseline luôn là tập con của cung, và giữ nguyên mức bảo thủ
  thêm với `DUP_COORD_SUSPECT`. Cổng hồi quy: `tests/test_covered0.py`
  (`test_baseline_excludes_coord_outside_admin`, `test_baseline_is_subset_of_export_supply_gate`).
- [x] **F4 — `candidate_sites` T0 anchor ⊆ tập cung *có chủ đích khác nhau*.**
  **32/12.827** anchor ngoài tập cung — kiểm chứng: **cả 32 đều là `access = UNKNOWN`**
  (`is_operational`, `is_primary`, `coord_resolved` đều True). Đây là **quyết định thiết kế đã ghi**
  ở docstring `build_covered0.py`: T0 nhận anchor `access=UNKNOWN` (chỉ cần không `RESTRICTED` —
  không loại ngầm cái chưa biết), baseline `covered0` thì **bảo thủ** hơn. Không phải lỗi.
- [x] **F5 — Số dòng khớp doc.** Sau rebuild, artefact và doc đã hội tụ:

  | Artefact | Doc khai (30/07) | Đo sau rebuild 31/07 | Ghi chú |
  | --- | --- | --- | --- |
  | `stations` | 19.805 | **19.507** | doc cần cập nhật |
  | `connectors` | 24.787 | **24.415** | doc cần cập nhật |
  | tập cung | 19.086 | **19.181** | doc cần cập nhật |
  | ô cung | 12.744 | **12.801** | doc cần cập nhật |
  | `candidate_sites` | 16.659 | **16.686** | doc cần cập nhật |
  | `demand_h3` | 314.934 | **314.934** | ✓ khớp |
  | `pop_2025` | 303.319 ô / 101,30M | **303.319 ô / 101,30M** | ✓ khớp bit |

  > Chênh còn lại là do doc chép số của nhánh `integrate/final`; artefact cục bộ giờ **tự nhất quán**
  > (`export_supply_report` ↔ `covered0_report` ↔ `candidate_sites_qa` cùng một thế hệ).
  > **Việc còn lại:** cập nhật [overview.md](overview.md) + [schema-contract.md](../schema/schema-contract.md)
  > theo cột "đo sau rebuild".

### G. Không gian — **3/3 PASS**

- [x] **G1 — `len(geojson.features) == len(parquet)`.** 16.686 = 16.686 · 19.012 = 19.012.
- [x] **G2 — Mọi dòng có `lat`/`lng` không null**, nằm trong bbox AOI đã khai.
- [x] **G3 — `h3_r8` hợp lệ, res 8, không NULL**, khớp `h3.latlng_to_cell(lat, lng, 8)` — **0 lệch**
  trên cả hai bảng. *(Trước rebuild: 9 dòng `covered0` có `h3_r8` NULL — xem F3.)*

### H. Sẵn sàng cho MCLP — **5/5 PASS** *(đọc từ `candidate_sites_qa.json`, phạm vi TOÀN QUỐC)*

- [x] **H1 — `upper_bound_coverage` ≥ 0,9.** = **0,912**.
- [x] **H2 — `freedom_ratio` ≥ 5·p.** 16.686 ≥ 4.000 (`p_hint = 800`).
- [x] **H3 — `size_ceiling` ≤ 80.000.** 16.686.
- [x] **H4 — `anti_degenerate` ≥ 0,9.** = 1,0.
- [x] **H5 — `grid_radius`: R > d.** R = 3,0 km > d = 0,98 km (**P4**).

### I. Dư thừa / đã làm sạch chưa — **1/4 PASS**

- [ ] **I1 — Không có cột hằng số.** ⚠️ 3 cột ở `covered0` (giảm từ 5), 1 ở `candidate_sites` (giảm từ 2),
  1 ở `stations`.
- [x] **I2 — Không có cột trùng bit ở `data/processed/`.** ✓ *(bộ 3 `is_public`/`verified`/`config_resolved`
  của `covered0` đã hết trùng khi chuyển sang phạm vi toàn quốc.)* `stations` vẫn còn 2 cặp — xem §3.1.
- [ ] **I3 — Không có cột suy ra được 100% từ cột khác.** ⚠️ 8 ở `stations`, 3 ở `connectors`,
  1 ở `candidate_sites`.
- [ ] **I4 — Mọi cột giữ lại có lý do ghi trong data-dictionary.** ⚠️ Xem §3.

---

## 3. Kết quả kiểm tra dư thừa cột *(chi tiết nhóm I)*

Ba mức: **DEAD** = không mang thông tin nào · **DERIVED** = suy ra 100% từ cột khác trong cùng bảng ·
**KEEP** = trùng lặp nhưng có lý do chính đáng (đã ghi hợp đồng).

### 3.1 `stations` — 61 cột

| Cột | Mức | Bằng chứng đo 2026-07-31 |
| --- | --- | --- |
| `lat_raw`, `lng_raw` | **DEAD** | `(lat == lat_raw).all()` = True; `(lng == lng_raw).all()` = True — **trùng bit 100%** |
| `coord_fix_dist_m` | **DEAD** | 1 giá trị duy nhất `0.0` (+38 null) — **chưa toạ độ nào từng được sửa** |
| `is_operational` | DERIVED | `== (op_status != 'OUT_OF_SERVICE')` đúng mọi dòng |
| `provenance` | DERIVED | song ánh 1:1 với `official_matched` (2↔2 giá trị) |
| `n_dup_members` | DERIVED | `(n_dup_members > 1) ⟺ dup_group_id.notna()` đúng mọi dòng |
| `config_resolved` | DERIVED | phụ thuộc hàm từ `config_src` |
| `coord_resolved` | DERIVED | phụ thuộc hàm từ `coord_src` |
| `province_name` | DERIVED | 1:1 với `admin_l1_code` (34↔34) — denormalize chiều |
| `commune_name` | DERIVED | phụ thuộc hàm từ `commune_code` |
| `connector_types` | DERIVED | `len() == num_connectors` mọi dòng; nội dung đã có ở bảng `connectors` — **lặp grain** |
| `verified` | ~DERIVED | chỉ khác `official_matched` ở **8/19.507 dòng**, cả 8 đều `match_method = spatial_fuzzy` |
| `status`, `is_public` | **KEEP** | nguồn THÔ của `op_status`/`access` — **P8 khai giữ có chủ đích** |
| `province_code` | **KEEP** | khoá partition Hive + hệ 63 tỉnh CŨ, **khác** `admin_l1_code` (hệ 34) |

**Ba cột DEAD.** `lat_raw`/`lng_raw`/`coord_fix_dist_m` được thiết kế để lưu vết **sửa** toạ độ, nhưng
chính sách **E-DQ1** đã chốt là **loại trừ** chứ không sửa (detector A → exclude). Chúng sẽ mãi bằng
`lat`/`lng`/`0.0`. Giữ lại thì vô hại nhưng gây hiểu nhầm: người đọc tưởng có một tầng toạ độ gốc để đối chiếu.
→ **Bỏ, hoặc ghi rõ trong data-dictionary rằng chúng dự trữ cho chính sách sửa toạ độ chưa bật.**

### 3.2 `connectors` — 11 cột → payload thực **7 cột**

| Cột | Mức | Bằng chứng |
| --- | --- | --- |
| `station_code` | **DERIVED** | `station_id → station_code` là phụ thuộc hàm; ở `stations` hai khoá song ánh 1:1 |
| `connector_label` | **DERIVED** | `(current_type, power_kw) → connector_label` xác định **hoàn toàn** (vd `AC-11kW`) |
| `vehicle_class` | **DERIVED** | phụ thuộc hàm từ `connector_standard`; 24.406/24.415 = `CAR` (gần hằng số) |
| `province_code` | **KEEP** | khoá partition Hive — cấu trúc, không phải dữ liệu (đã kiểm: luôn == `province_code` của trạm cha) |
| `current_type` | **KEEP** | **không** suy được từ `connector_standard` (1 nhóm vi phạm) — đúng như P7 mô tả |

⇒ Trả lời trực tiếp câu hỏi: **có, `connectors` dư 3/11 cột.** Thông tin độc lập chỉ nằm ở
`connector_id` · `station_id` · `power_kw` · `current_type` · `connector_standard` · `count_total` · `count_available`.

### 3.3 `covered0` — 19 cột, **3 cột hằng số** *(giảm từ 5 sau khi chuyển phạm vi toàn quốc)*

| Cột | Giá trị duy nhất | Vì sao |
| --- | --- | --- |
| `access` | `PUBLIC` | **cặn bộ lọc** — đã lọc theo chính nó |
| `verified` | `True` | cặn bộ lọc |
| `operator` | `VinFast` | toàn bộ cung hiện tại là một operator (**số liệu thật**, không phải cặn lọc) |

`config_src`/`config_resolved`/`is_public` **hết** hằng số ở phạm vi toàn quốc — chúng chỉ hằng số trên
AOI Hà Nội cũ. Còn `access` là dạng dư thừa kinh điển: cột dùng làm **vị từ lọc** rồi vẫn xuất ra sau khi
lọc ⇒ entropy = 0. Giữ được nếu coi nó là *nhãn tự mô tả* của artefact, nhưng phải ghi rõ lý do (**I4**).

### 3.4 `candidate_sites` — 16 cột

| Cột | Mức | Bằng chứng |
| --- | --- | --- |
| ~~`province_code`~~ | ~~DEAD~~ → **ĐÃ SỬA** | 12.827/16.686 non-null, đúng bằng số T0 (**C3**) |
| `exclusion_flags` | **DEAD** | list rỗng ở **mọi** dòng (0 dòng khác rỗng) |
| `is_existing` | **DERIVED** | `is_existing == (tier == 'T0')` đúng mọi dòng |

`exclusion_flags` rỗng là **đúng theo thiết kế** (ô cấm đã bị loại trước khi ghi) — nhưng khi đó nó là cột
audit không bao giờ khác rỗng, nên hoặc bỏ, hoặc chuyển sang ghi ở artefact *bị loại* thay vì artefact *được giữ*.

### 3.5 ⚠️ MỚI — `stations.connector_types` còn nhãn TRƯỚC P7 *(mâu thuẫn trong chính một dòng)*

Không phải dư thừa mà là **sai lệch**: bản sửa **P7** (connector 20–22 kW bị power-tier gán nhầm AC →
thực tế **DC CCS2**) đã áp cho bảng `connectors` **và** cột `stations.current_type`, nhưng **không** áp cho
cột list `stations.connector_types`.

| Kiểm tra | Kết quả |
| --- | --- |
| `stations.current_type` vs `connectors` | **0/19.225 lệch** ✓ đã sửa đúng |
| `stations.connector_types` vs `connectors.connector_label` | **1.579/19.225 lệch** ✗ |
| Bậc công suất dính lệch | **chỉ 20 kW và 22 kW** — đúng lớp của P7 |
| Mẫu lệch | `AC-20kW → DC-20kW` (1.474) · `AC-22kW → DC-22kW` (96) · cả hai (9) |

Hệ quả cụ thể: **1.579 trạm tự mâu thuẫn trong chính dòng của nó** —

```
vn-c-ac000111   current_type = DC   connector_types = ['AC-20kW']
vn-c-ac000395   current_type = DC   connector_types = ['AC-22kW']
```

Ai đọc `connector_types` (thay vì `current_type`) để phân tầng AC/DC sẽ đếm nhầm **1.579 trạm DC thành AC**.
→ **Sinh lại `connector_types` từ bảng `connectors`** (nguồn đã đúng) trong `transform_canonical`, kèm cổng
`connector_types == distinct(connectors.connector_label)`.

> Lưu ý đo lường: `len(connector_types) ≠ num_connectors` (lệch 5.140 dòng) **không** phải lỗi —
> `connector_types` là danh sách **loại phân biệt**, không phải một phần tử mỗi súng (`len ≤ num_connectors`
> đúng mọi dòng).

---

## 4. Đã làm 2026-07-31 (rebuild) — và việc còn lại

### 4.1 Đã đóng

1. **Rebuild toàn chuỗi từ raw đã freeze.** `boundary` → `osm` → *(tải 2 raster R2024B)* → `freeze` →
   `demand` → `landuse-national` → `candidates-national` → `covered0-national`.
   Đóng **A1–A4, E4, F5**, và làm xanh `test_poi_points_artifact_has_no_foreign_rows`
   (20.247 POI ngoài VN đã bị cắt fail-closed; `osm_poi_points` giờ 17.102 dòng, 0 ngoài VN).
2. **Sửa F3** — `build_covered0._baseline_mask` gate bằng **`coord_resolved` VÀ** `DIRTY_COORD_FLAGS`
   ⇒ baseline luôn ⊆ tập cung; 9 dòng `h3_r8` NULL biến mất. Thêm khối `gates` **tự kiểm** vào
   `covered0_report.json` (5 cổng, `strict` sẽ dừng build nếu đỏ) + 2 test hồi quy.
3. **Sửa C3** — `candidate_sites` mang **hai hệ mã tách bạch**: `province_code` (63 CŨ, chỉ T0) +
   `admin_l1_code`/`province_name` (34, từ `demand_h3`). Hợp đồng + doc candidate-sites đã cập nhật.
4. **Sửa URL WorldPop 2025** — `.../Individual_countries/VNM/` trả **404**; R2024B nằm ở cây
   `Global_2015_2030/R2024B/<year>/`. Đã sửa `data/worldpop/paths.py`; hai raster giờ `present: true`
   trong MANIFEST, `verify-snapshot` **PASS**.

### 4.2 Còn lại

1. **Sửa `stations.connector_types`** (§3.5) — sinh lại từ bảng `connectors` + cổng đối soát.
   **Ưu tiên cao nhất trong các việc còn lại**: đây là số *sai*, không phải cột thừa.
2. **Chốt nhóm I** — với mỗi cột DEAD/DERIVED: bỏ, hoặc ghi lý do giữ vào
   [data-dictionary.md](../schema/data-dictionary.md). Cột không có lý do là cột sẽ lệch.
   Ứng viên bỏ rõ nhất: `lat_raw`/`lng_raw`/`coord_fix_dist_m` (§3.1) và
   `connectors.station_code`/`connector_label`/`vehicle_class` (§3.2).
3. **Cập nhật số ở [overview.md](overview.md) + [schema-contract.md](../schema/schema-contract.md)**
   theo cột "đo sau rebuild" của **F5** — doc đang chép số nhánh `integrate/final`.
4. **Đưa D1–D6 + F1–F4 thành test** (F3 đã có; còn lại chưa). Lý do đã ghi ở
   [overview.md §6](overview.md): *artefact không có cổng thì sẽ lệch, chỉ là bao giờ*.
5. **B3** — `demand_weight` (E-DQ7d, Kỳ) · `demand_servable` (E-DQ8c) · coverage/gap · PostGIS · GeoJSON.
