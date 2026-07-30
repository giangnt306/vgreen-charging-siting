# Review: `data-schema-by-phase.md` vs. Dự án thực tế

> Đánh giá ngày **2026-07-24**. So sánh bản schema collaborator gửi với 3 tài liệu gốc của dự án:
> `problem-analysis.md`, `known-issues.md`, `data-layer-overview.md`.

---

## TL;DR (Kết luận nhanh)

| Chiều đánh giá | Kết quả |
|---|---|
| Khớp mục tiêu bài toán? | ✅ Phần lớn khớp |
| Khớp kiến trúc dữ liệu hiện có? | ⚠️ **Lệch đáng kể** — dùng thuật ngữ medallion (`raw→gold`) trong khi pipeline thực tế dùng `raw/interim/processed` |
| Schema bảng cốt lõi có nhất quán? | ⚠️ **Có khác biệt** ở số dòng, tên cột, và cấu trúc bảng |
| Các known-issues đã xử lý đúng? | ✅ Phần lớn đúng, nhưng thiếu một số issue quan trọng |
| Phân pha D0→DF có hợp lý? | ✅ Logic tốt, phù hợp roadmap Sprint 1–3 |
| Có thể dùng ngay làm "hợp đồng"? | 🔴 **Chưa** — cần đồng bộ lại các điểm lệch trước |

---

## 1. ✅ Điểm KHỚP — Schema đúng với dự án

### 1.1 Mục tiêu bài toán & triết lý tối ưu
Schema xác định đúng:
- **Brownfield** (đặt thêm, không xóa cũ) — khớp với `problem-analysis.md` §3.
- **MCLP** làm baseline optimizer — khớp roadmap Sprint 2.
- `demand_a / demand_b` hai biến thể để robustness — đúng với cách dự án dùng Proxy A/B (xem `known-issues.md` P1).
- `covered0` = vùng đã phủ bởi trạm hiện hữu → D1 chỉ tối ưu phần *thêm* — khớp 100%.

### 1.2 Phân tầng D0 → DF
- **D1 không cần data mới** → đúng, `data-layer-overview.md` xác nhận pipeline cung+cầu đã xong cơ bản.
- **D2 cần A3 (OSRM), A4 (candidates thật), A2 (calibrate)** — khớp roadmap Sprint 3.
- **DF (data không tồn tại):** 4 mục liệt kê (OD, session time-series, giá đất, mạng trung thế EVN) — nhất quán với `problem-analysis.md` nhóm 2 và phần "Hướng mở rộng".

### 1.3 Vault / ToS constraint
Schema ghi đúng ràng buộc 🔒 Vault: row-level ở lại vault, report chỉ method + aggregate, `gold-only variant` cho G1 rollback — phản ánh đúng thực tế dự án.

### 1.4 Bảng output D1
`siting/d1_picks` và `siting/d1_budget_curve` khớp với output yêu cầu trong `problem-analysis.md` §4:
- coverage % theo mức ngân sách ✅
- đường cong coverage vs. budget ✅
- GeoJSON output cho map demo ✅

### 1.5 `gold/nn_substation` & feasibility
Schema mô tả đúng tín hiệu OSM `power=substation` là proxy thô (caveat median 3.2km) — nhất quán với `known-issues.md` P5 và `data-layer-overview.md` §5 (substation-dist BallTree).

---

## 2. ⚠️ Điểm LỆCH — Cần đồng bộ

### 2.1 🔴 Mismatch kiến trúc: Medallion vs. `raw/interim/processed`

**Schema của collaborator dùng:**
```
medallion raw → gold
```
> `gold/stations`, `gold/demand_proxy`, `gold/nn_substation`, `gold/agg_h3`, `gold/core`

**Pipeline thực tế (`data-layer-overview.md` §1 & §3) dùng:**
```
data/raw/ → data/interim/ → data/processed/
```

Đây là **mismatch kiến trúc thư mục**. Schema collaborator dùng thuật ngữ Databricks medallion (bronze/silver/gold) nhưng codebase thực tế không dùng kiến trúc này. Cần thống nhất:
- `gold/stations` = `data/interim/canonical/stations/` (Parquet Hive-partitioned)
- `gold/demand_proxy` = `data/interim/demand_h3.parquet` (hiện 7 cột, chưa đủ 11 cột)
- `gold/core` = `data/processed/` (chưa tồn tại — là output *cần xây*)

> [!WARNING]
> Nếu dùng schema này làm "hợp đồng" mà không map lại tên thư mục, sẽ gây nhầm lẫn khi integrate với Kỳ.

---

### 2.2 🟠 `gold/stations` — số dòng & trường lệch

| Chỉ số | Schema collaborator | Thực tế (`data-layer-overview.md` §4) |
|---|---|---|
| Số dòng | **13.258** | **19.507** |
| Số cột | **34** | **34** ✅ |
| `operator` | Liệt kê là trường solver tối thiểu | ⚠️ `operator` đang bẩn (P6/P7 trong known-issues) — lẫn nhãn, chưa làm sạch |
| `status` | Solver tối thiểu | ⚠️ null 72 dòng, chưa xử lý |
| `province_name`, `commune_name` | Khai báo có | ✅ **enrich xong 30/07 (`E-DQ3`)** — 19.453/19.507 có nhãn, nguồn VNSDI cấp xã niên đại 2025-06-16; thêm `commune_code`/`admin_src`/`admin_verdict` |
| `source_lineage`, `primary_source` | Liệt kê | Chưa thấy trong schema thực tế — cần kiểm |

> [!IMPORTANT]
> Con số 13.258 của collaborator vs 19.507 thực tế — lệch **~6.249 dòng**. Có thể collaborator đang tính sau khi lọc bỏ BSS (9.118 battery-swap) và một số subset, nhưng **con số không khớp với bất kỳ mốc nào trong `data-layer-overview.md`**. Cần xác nhận nguồn gốc con số này.

---

### 2.3 🟠 `gold/demand_proxy` — thiếu cột so với thực tế

**Schema collaborator khai báo 11 cột** (316.526 ô):
`pop`, `n_poi`, `road_len_m`, `pop_n`, `poi_n`, `road_n`, `demand_a`, `demand_b` + admin fields

**Thực tế (`data-layer-overview.md` §4):** `demand_h3` hiện có **7 cột** (268.404 ô):
`pop`, `road_len_m`, `road_len_mt_m`, `n_poi`, `n_parking`, `n_fuel` — **chưa có `demand_weight`**, chưa có admin.

| Vấn đề | Chi tiết |
|---|---|
| Số ô lệch | 316.526 vs 268.404 — lệch ~48k ô |
| `demand_a/b` chưa tồn tại | Đây là TODO (`features/build_demand_proxy.py`) |
| `pop_n/poi_n/road_n` chưa tồn tại | Chưa normalize |
| Admin fields chưa có | ✅ **có từ 30/07 (`E-DQ3`)** — 255.298/255.480 ô; kèm `admin_frac`/`n_communes`. ⚠️ nhãn là **argmax diện tích**, cộng khối lượng phải qua `cell_commune`/`demand_commune` (40% dân ở ô vắt ≥2 xã) |
| `n_parking`, `n_fuel` không khai báo | Có trong thực tế nhưng bị bỏ qua trong schema collaborator |

> [!NOTE]
> `n_parking` và `n_fuel` trong `demand_h3` thực tế quan trọng vì chúng là input cho **candidate site T1** (parking/fuel = anchor ưu tiên). Schema collaborator bỏ qua 2 trường này.

---

### 2.4 🟡 `gold/nn_substation` — số dòng lệch nhỏ

Schema: **13.237 × 4** | Thực tế: liên kết với 19.507 stations → con số 13.237 chưa được giải thích rõ.

---

### 2.5 🟡 `gold/agg_h3` — bảng CHƯA TỒN TẠI trong pipeline thực tế

`gold/agg_h3` (316.556 × 15) mô tả bảng tổng hợp per-ô: đếm trạm/trụ, `n_parking`, `n_fuel`, khoảng cách tới trạm gần nhất, cờ gap.

Tìm trong `data-layer-overview.md`: **không thấy bảng này**. Đây là bảng *mới cần xây* — không phải bảng đã có. Schema collaborator ghi ở "Tầng 0 — ĐÃ CÓ" nhưng thực tế **chưa có**.

> [!CAUTION]
> Việc đánh dấu `gold/agg_h3` là "đã có" là sai. Đây là output *cần build* từ join `stations × demand_h3 × OSM`. Nếu Kỳ dựa vào bảng này mà không được Giang build trước → chặn pipeline.

---

### 2.6 🟡 `gold/core` — bảng CHƯA TỒN TẠI

`gold/core` (bundle per-city, sinh bởi `gold_core.py`) — script `gold_core.py` **không có trong codebase** (`data-layer-overview.md` §2 không liệt kê). Đây là bảng *cần xây* cho 4 TP pilot (HN/HCM/DN/QN).

---

### 2.7 🟡 Phân vai — Schema không phản ánh đúng vai trò

**Schema collaborator** ghi "Handoff Giang (D-d): hợp đồng = `gold/stations` + `gold/demand_proxy`" — ngụ ý Giang **giao data cho người khác**.

**Thực tế** (`problem-analysis.md` §3): Giang làm toàn bộ data layer, **bàn giao cho Kỳ** ở 2 điểm:
1. `demand proxy + candidate sites` → Kỳ chạy MCLP
2. Kỳ → Giang: GeoJSON kết quả

Schema không đề cập `candidate_sites` là điểm bàn giao thứ 3 (đã được chốt trong `known-issues.md` P5).

---

### 2.8 🟢 Nhỏ nhưng đáng ghi nhận

- Schema dùng **`h3_r8` / `h3_r9`** — nhất quán với dự án ✅
- `current_type` AC/DC/MIXED — nhất quán ✅
- Phân biệt `vehicle_class` ô tô/2 bánh — nhất quán với quyết định lọc BSS ✅ (đã hiện thực hoá 24/07 từ chuẩn cắm chính thức — **P7**)
- `quality_flags` trong stations — nhất quán ✅

---

## 3. ❌ Điểm THIẾU trong Schema (so với known-issues)

| Issue trong dự án | Có trong schema? | Ghi chú |
|---|---|---|
| **P4** Bán kính suy biến R/d | ✅ Có đề cập gate `R > d` | OK |
| **P5** Candidate set / land-use | ⚠️ Đề cập qua A4 nhưng không nhắc `buildable_h3`, QA gate 5 cổng | Schema A4 ở D2 — nhưng thực tế candidate đã xong ở Sprint 1 |
| **P6** Trùng PK / dedup | ❌ Không nhắc | |
| **P7** Nhiễm xe máy / BSS | ✅ **Đã xử lý (24/07).** `vehicle_class` + `connector_standard` suy từ chuẩn cắm chính thức (CCS2/Type2); BSS 9.118 đã lọc; sửa 1.588 connector 20-22 kW AC→DC CCS2 | |
| **P8** Null status/is_public | ❌ Không nhắc — nhưng `status` đưa vào "solver tối thiểu" | Nguy hiểm: null 72 dòng mà coi là tối thiểu |
| **P9** Lệch thời điểm crawl | ❌ Không nhắc | |
| **P10** WorldPop 2020 lỗi thời | ❌ Không nhắc | |
| **P11** Tổng dân số vs sở hữu ô tô | ❌ Không nhắc | |
| Tọa độ placeholder (274 trùng) | ❌ Không nhắc | Ảnh hưởng `lat/lng` solver |
| `admin_*` null 100% | ❌ Không nhắc — nhưng liệt kê `province_name/commune_name` như có sẵn | ✅ đã đóng ở `E-DQ3` (30/07) |

---

## 4. Đề xuất hành động

### Ưu tiên cao (chặn việc dùng schema làm hợp đồng)

1. **Đồng bộ tên thư mục:** Map `gold/*` → `data/interim/*/` hoặc đồng ý đổi sang medallion thật sự (cần quyết định kiến trúc).
2. **Xác nhận nguồn gốc 13.258 dòng** — là stations subset nào? Sau lọc BSS + lọc gì nữa?
3. **Đánh lại trạng thái bảng:** `gold/agg_h3` và `gold/core` phải chuyển sang "Cần xây" (D1 output), không phải "Đã có".
4. **Bổ sung `candidate_sites` là điểm bàn giao D1** (hiện thiếu hoàn toàn).

### Ưu tiên trung bình

5. **Thêm `n_parking`, `n_fuel`** vào schema `gold/demand_proxy`.
6. ~~**Ghi rõ trạng thái null** của `province_name`, `commune_name`~~ → **hết null 30/07 (`E-DQ3`)**; `status`/`is_public` → resolve qua `op_status`/`access` (**P8**, 27/07).
7. **Thêm cảnh báo P6–P11** vào phần QA của schema (ít nhất là comment).

### Ưu tiên thấp (nice-to-have)

8. Bổ sung `road_len_mt_m` (đường chính) vào demand schema — hiện có trong thực tế nhưng schema bỏ qua.
9. Ghi rõ `demand_a/demand_b` là **TODO** chưa build, không phải "đã có".

---

## 5. Tóm tắt bằng ma trận

```
Bảng                 | Trạng thái thực   | Schema khai báo | Đánh giá
---------------------|-------------------|-----------------|----------
gold/stations        | ✅ Có (19.507)    | Có (13.258)     | ⚠️ Số lệch
gold/demand_proxy    | ⚠️ 7/11 cột      | Có (11 cột)     | ⚠️ Thiếu cột + demand_a/b chưa build
gold/nn_substation   | ✅ Có             | Có              | ⚠️ Số dòng cần verify
gold/agg_h3          | ❌ Chưa có        | Có              | 🔴 Sai trạng thái
gold/core            | ❌ Chưa có        | Có              | 🔴 Sai trạng thái
Vault (evcs_vn)      | ✅ Có             | Có              | ✅ Khớp
D1 outputs           | ⏳ Chưa build     | Định nghĩa rõ   | ✅ Schema tốt
D2 outputs (A3/A4)   | ⏳ Roadmap        | Định nghĩa rõ   | ✅ Schema tốt
candidate_sites      | ✅ Đã build (P5)  | Không nhắc      | 🔴 Thiếu
```
