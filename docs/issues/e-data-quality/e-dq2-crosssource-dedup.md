# E-DQ2 — Trùng chéo nguồn (evcs ↔ official) (bước 2)

`🟠 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán — KHÔNG phải 1 vấn đề, mà là 3** (giống cách mổ **P5**). Đo trên canonical car-only
(19.507) + registry official:

| Loại                                                                                                                                                                                                                                            | Bằng chứng                                                                                     | Xử lý                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | --------------------------------------------- |
| **2a — collapse evcs↔official** (1 trạm VinFast vật lý = nhiều bản ghi: 1 `exact_code` + các `spatial_fuzzy` rơi vào **cùng** `official_store_id`; vd AEON Hà Đông bị 3 app EFASTCHARGE/TIENMAT/evcs liệt kê) | **9** store official bị >1 canonical trỏ vào                                            | collapse (dinh danh first-party trùng khớp) |
| **2b — trùng nội evcs** (station_code khác, không anchor official, cùng điểm vật lý; vd đại lý BYD 2 feed)                                                                                                                    | **204** cụm toạ độ trùng khít / **478** trạm                                  | merge coord + name                            |
| **2c — official-only** (chiều ngược: trạm car official vắng khỏi evcs)                                                                                                                                                              | **3.486** official-only — nhưng **3.466 `UNAVAILABLE`**, chỉ **~13** live | **DOC**, không merge                   |

**Tại sao KHÔNG dedup bằng H3 thô** (như register ghi ban đầu): 10.284 trạm chung ô res 8, nhưng ô
0,83 km² → mall/sân bay chứa **nhiều trạm thật**. Dò 1 cụm ramp toạ độ placeholder cho thấy **44 charger
"Tư nhân"** ở **44 tỉnh khác nhau** nhưng toạ độ tăng đều (giả) — dedup theo ô sẽ **phá ~10k trạm thật**.
Phải theo **khoảng cách + định danh**, ô chỉ là khoá blocking.

**Cách xử lý — identity resolution `physical_id`, FLAG không xoá** (nhất quán P6/P8), ở
[`dedup_crosssource.py`](../../../src/ev_siting/data/evcs/dedup_crosssource.py):

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
  `is_primary` (giống `is_operational` của P8) — [`build_candidates._load_stations`](../../../src/ev_siting/features/build_candidates.py)
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

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
