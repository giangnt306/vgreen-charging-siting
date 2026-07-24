# Nguồn chính thức VinFast (vinfastauto.com) — crawl + đối chiếu

Nguồn **first-party** (nhà sản xuất), dùng làm **căn cứ xác minh** cho master
crawl thô `stations_master_evcs.csv` (evcs.vn). Code: `src/ev_siting/data/vinfast_official/`.

## 1. Crawl (`fetch_locators.py`)

| Bước    | Lệnh                        | Output                                                                 |
| ------- | --------------------------- | --------------------------------------------------------------------- |
| `bulk`  | `... fetch_locators bulk`   | `official_stations.parquet` — 23.247 trạm sạc ô tô (type 2444) từ CDN |
| `detail`| `... fetch_locators detail` | `data/raw/.../details/<store_id>.json` — 1 file/trạm (resume qua `.done`) |
| `parse` | `... fetch_locators parse`  | `official_connectors.parquet` (71.174 connector) + `official_admin.parquet` (23.240 trạm) |

**Fields/coords thực tế** (đã inspect toàn bộ 23.240 detail):
- Registry (`bulk`): `store_id`, `code` (`vfc_<store_id>`), `name`, `address`, `lat`/`lng`,
  `charging_status` (ACTIVE/INACTIVE/BUSY/UNAVAILABLE/OUTOFSERVICE), `access_type`, `status`,
  `party_id`, `hotline`, `province_id`.
- Detail (`data.*`): **100%** có `coordinates` + admin (`province`/`district`/`commune`);
  20.526 trạm có connector. Chuẩn cắm: `IEC_62196_T2` (AC 3-pha, 31.614) + `IEC_62196_T2_COMBO`
  (CCS2 DC, 39.560).

> ⚠️ `parse` phải chạy **sau khi** `detail` xong (kiểm `details.done`), nếu không parquet
> connector/admin sẽ khuyết (lỗi từng gặp: parse lúc mới crawl 202/23.240 file).

## 2. Matcher (`match_official.py`)

Đối chiếu `station_code` (evcs) ↔ `store_id` (official). Output
`official_xref.parquet` (1 dòng/`station_code`) + `official_xref_report.json`.

**Hai tầng match:**
1. `exact_code` — `station_code == store_id`. Hai nguồn dùng chung backend VinFast →
   **19.427** trạm `VINFAST_CS` khớp tuyệt đối, toạ độ lệch tối đa **0,3 m**, 0 bất đồng.
2. `spatial_fuzzy` — phần còn lại có toạ độ hợp lệ → `BallTree(haversine)` tìm trạm official
   gần nhất trong bán kính `R` (mặc định 250 m), chấp nhận nếu tên giống (rapidfuzz
   `token_set_ratio ≥ 82`) **hoặc** rất gần (< 40 m). Bắt được **3.730** trạm đổi pin `B.*`
   **co-located** với trạm sạc `C.*` (vd `B.AGI00002 → C.AGI0002`, 0 m, tên trùng).

**Phạm vi xác minh** — `expected_official` = mạng VinFast + trạm sạc ô tô (`C.*`/`VINFAST_CS`).
Trạm ngoài phạm vi (đổi pin, mạng khác) **không bị trừ điểm** vì vắng khỏi registry official.

## 3. Provenance / verified / confidence (bàn giao vào `stations` canonical)

`transform_canonical.py` left-join `official_xref` theo `station_code`, thêm cột và
**định nghĩa lại** `confidence`/`verified`:

| Cột                        | Ý nghĩa                                                             |
| -------------------------- | ------------------------------------------------------------------- |
| `provenance`               | `vinfast_official+evcs.vn` (đã đối chiếu) hoặc `evcs.vn` (đơn nguồn) |
| `official_matched`         | bool — có khớp nguồn chính thức                                     |
| `match_method`             | `exact_code` / `spatial_fuzzy` / `none`                            |
| `official_store_id`        | khoá trạm official đã khớp                                          |
| `match_dist_m`             | khoảng cách haversine giữa toạ độ 2 nguồn                          |
| `match_name_sim`           | độ giống tên 0..100 (rapidfuzz)                                     |
| `official_charging_status` | trạng thái sạc first-party (ACTIVE/BUSY/…) — tín hiệu status mới    |
| `official_access_type`     | Public/Restricted theo official                                    |
| `verified`                 | **redefine**: True khi có corroboration first-party (code khớp + toạ độ đồng thuận ≤ 200 m; hoặc spatial tên mạnh + trong bán kính) |
| `confidence`               | **redefine**: trạm ky vọng → `0.4·completeness + 0.6·verification`; trạm ngoài phạm vi → chỉ `completeness` (không bị trừ) |

`completeness` = giữ 4 chỉ báo cũ (toạ độ hợp lệ · có nguồn cung `evse_powers` · có `status` ·
có telemetry). `verification` = 1.0 (code khớp + toạ độ đồng thuận) · 0.6 (code khớp, lệch) ·
`0.5 + 0.4·sim` (spatial) · 0.0 (không khớp).

**Kết quả canonical** (`stations`, bỏ BSS): 19.432/19.507 verified, confidence TB **0,995**;
67 trạm `OTHER` không có trong registry VinFast → `provenance=evcs.vn`, `verified=False`.

Chạy đủ chuỗi:
```
PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators bulk
PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators detail
PYTHONPATH=src python -m ev_siting.data.vinfast_official.fetch_locators parse
PYTHONPATH=src python -m ev_siting.data.vinfast_official.match_official
PYTHONPATH=src python -m ev_siting.data.evcs.transform_canonical
```
