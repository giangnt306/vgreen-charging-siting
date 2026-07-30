# REVIEW TRƯỞNG NHÓM DỮ LIỆU — chốt dataset 2026-07-29

*Phạm vi: toàn bộ diff `devky/review-dataset` ↔ `main` (78 file, +9.762 dòng) + 4 module untracked mới.
Đối chiếu với `docs/schema/schema-contract.md`, `docs/known-issues.md`, `docs/de-bai-v2.md`, `data/raw/MANIFEST.json`.*

**Quy tắc của bản review này:** không tin doc, chỉ tin số đo lại trên chính dữ liệu trong `data/`.
Mỗi mục ghi rõ **đã kiểm chứng bằng cách nào**. Mục nào không đo được thì ghi `CHƯA KIỂM CHỨNG` + lý do.
Lệnh tái lập nằm ngay dưới mỗi bằng chứng.

---

## PHẦN B — ĐÁNH GIÁ CHẤT LƯỢNG DỮ LIỆU HIỆN TẠI

> ## ⚠ CẬP NHẬT 2026-07-29 (sau review) — **4 lỗi CHẶN đã đóng**
>
> Phán quyết §B.0 bên dưới giữ nguyên **nguyên văn tại thời điểm review**. Bốn mục 🔴 đã được sửa
> cùng ngày; chi tiết + bằng chứng ở [known-issues.md §G](../known-issues.md). Tóm tắt:
>
> | ID | Sửa gì | Kiểm chứng |
> |---|---|---|
> | **[L1]** | `_distinct_store` chỉ chặn khi registry nói **độc lập** với PK; so **danh tính** (trừ `address`, đòi tập-con + khớp token chữ số) thay vì tỷ lệ mờ trên `name` | primary 19.775 → **19.644** · dup 30 → **161** · 145 nhóm max 4 · guard nổ **1** lần thay vì ~2.630 · 5/5 gate PASS · 4 test đối kháng |
> | **[L4]** | Lớp ranh giới vào `data/ref/vn_admin/` + nguồn **`vn_admin`** trong MANIFEST (ODbL); fallback ra repo anh em nay **cảnh báo to** | snapshot **6 nguồn / 14 member**; `verify --hashes` **PASS**; E-DQ11 regression 0/0/0 |
> | **[L6]** | `coord_quality` tự swap generation (atomic + rollback); `make canonical` gọi `admin-join` → `coord-quality` | chạy `make canonical` **2 lần** → mọi cột quyết định giống hệt, 171 cờ cả hai lần |
> | **[L10]** | `evcs_enumerate --seed-from-official` + `make discover-new` + sidecar `.seed.json`; đóng băng registry gen 179 | seed **tất định**, 7 test không cần mạng; gen 179 phủ **242/298 (81%)** |
>
> **Kèm theo:** kiểm chứng luôn `de-bai-v2` §7.2 (`GIẢ-ĐỊNH-HỞ`): `UNAVAILABLE → ACTIVE|BUSY` =
> **127/3.800 = 3,3%** trong 7 ngày, và **168/298** trạm mới từng là `UNAVAILABLE` ⇒ **cách đọc
> đúng**, nhưng chậm (~3%/tuần) nên là *sổ pipeline*, không phải tín hiệu ngắn hạn.
> Cũng phát hiện thêm: công cụ inspect `dedup_crosssource` **không nạp cột `address`** nên báo số
> khác producer (118 vs 161 duplicate) — đã sửa.
>
> **Còn lại để chuyển sang ĐẠT:** [L3] `.fillna(0.0)` ở `_gapfill` · [L9] hai tầng telemetry ·
> [L13] holdout cũ · [L2]/[L5]/[L7]/[L8]/[L11]/[L14]/[L15]/[L16]. Xem §B.16.

### B.0 · Phán quyết

> ## ⛔ CHƯA ĐẠT — không chốt được ở trạng thái hiện tại.
>
> *(phán quyết tại thời điểm review — xem khối cập nhật phía trên)*

Không phải vì chất lượng nội dung kém. Ngược lại: **các fix E-DQ11 (cắt biên) và E-DQ12 (settlement) là
thật, đo lại đúng, và đóng đúng vấn đề chúng tuyên bố đóng.** Lý do CHƯA ĐẠT nằm ở ba chỗ khác:

| # | Lý do chặn | Bằng chứng một dòng |
|---|---|---|
| **1** | **Dataset hiện tại không tái lập được từ repo này.** | `make canonical && make covered0-national` từ bản sạch cho baseline **19.265**, bản đang giao là **19.210** — lệch **55 trạm**, mọi QA gate vẫn PASS |
| **2** | **Lớp ranh giới VN — thứ gác toàn bộ E-DQ11 — nằm NGOÀI repo và NGOÀI MANIFEST.** | `admin_dir()` → `../evcs-dataset/data/ref/vn_admin/…`; `data/ref` không tồn tại; `grep -c vn_admin MANIFEST.json` = **0** |
| **3** | **Fix dedup 29/07 vô hiệu hoá chính tầng T2 mà E-DQ2 sinh ra để giải.** | `official_store_id == station_code` cho **19.605/19.635 (99,85%)** ⇒ guard đúng bằng "khác PK" ⇒ **338 cặp <50 m tên giống ≥82 bị chặn, 97 cặp tên TRÙNG KHÍT**, tất cả đều `is_primary=True` |

Ngoài ba mục trên còn **một vấn đề phạm vi lớn hơn kỹ thuật** (§B.13): dataset đang được chốt là dataset
**cho MCLP phủ dân số**, trong khi `de-bai-v2.md` (chốt cùng ngày 29/07, và `docs/README.md` bảo *"Đọc file
này TRƯỚC"*) đã tuyên bố hàm mục tiêu phủ **FAIL gate G3** (ρ = −0,114) và thay bằng `ΔΠ`.

**Đường ra:** cả ba mục chặn đều là **việc kỹ thuật vài giờ**, không phải cào lại dữ liệu. Chi tiết ở §B.14.

---

### B.1 · Không gian — CRS, đơn vị, độ phân giải, cắt biên

**Đã kiểm chứng bằng:** đọc code `vn_boundary.py`, chạy lại `mask_points_in_vn` / `mask_cells_touching_vn`
trên chính 3 artefact đã giao.

| Kiểm tra | Kết quả đo lại | Kết luận |
|---|---|---|
| POI ngoài đa giác VN trong `osm_poi_points.parquet` | **0 / 17.106** | ✅ ĐÓNG THẬT |
| Ô `demand_h3` không chạm đa giác VN | **0 / 314.904** | ✅ ĐÓNG THẬT |
| Candidate ngoài VN trong `candidate_sites.parquet` | **0 / 22.219** | ✅ ĐÓNG THẬT (tốt hơn doc — doc còn ghi "4 điểm T0 ngoài ranh giới") |
| Chiều vị từ STRtree (`within` chứ không `covers`) | đúng, có test khoá (`test_vn_boundary.py`, `test_admin_join.py`) | ✅ |
| Trục toạ độ `points(x=lng, y=lat)` | đúng, có test | ✅ |
| H3 res 8, `R = 3 km`, `d = 0,98 km` | gate `grid_radius` PASS, `R/d = 3,06` | ✅ |
| `cell_area` dùng giá trị thật từng ô (0,79–0,87 km²) chứ không hằng số | `settlement.cell_areas` → `h3.cell_area(c,"km^2")`; `dens_ppkm2 == pop/area` sai số **0,0** | ✅ đúng |

**Nhận xét:** trục không gian là trục **làm tốt nhất** của sprint này. Bài học "cổng hỏi sai câu hỏi thì
không bao giờ đỏ" đã được nội hoá đúng: `validate.py` giờ hỏi bằng đa giác, và có 2 test độc lập khẳng
định bbox-cũ *sẽ* cho pass các điểm Thái Lan.

⚠ **Nhưng xem [L4]** — chính lớp ranh giới đó không được version-hoá.

---

### B.2 · Thời gian — mốc snapshot, lệch thời điểm, rò dữ liệu tương lai

**Đã kiểm chứng bằng:** quét trực tiếp 400 file ngẫu nhiên mỗi tầng time-series, đọc `MANIFEST.json`,
`occupancy_f19.meta.json`.

| Nguồn | Vintage thực đo | Ghi trong MANIFEST |
|---|---|---|
| evcs catalog (28.625 dòng) | crawl **07-21/22** | ✔ |
| evcs catalog (+298 dòng mới) | crawl **07-29** | ✔ (gộp chung một dòng vintage) |
| telemetry 168h | **2026-07-13 → 07-21**, gap p50 **2,09′**, gap max **36 h** | ✔ |
| telemetry 720h | **2026-06-29 → 07-29**, gap p50 **5,0′**, gap max **313,5 h (13 ngày)** | ✔ |
| OSM PBF | `replication_timestamp 2026-07-20T20:21:16Z`, seq 4852 | ✔ |
| WorldPop | 2020 BSGM + 2025 R2024B | ✔ |
| WorldCover | v200 / **2021** | ✔ |

- **Rò dữ liệu tương lai: KHÔNG có.** `tmax` của cả hai tầng ≤ 2026-07-29T14:15+07 = thời điểm crawl.
- **`snapshot_id` đổi 2026-07-20 → 2026-07-29** trong khi `known-issues.md` E-DQ10 và P9 vẫn ghi
  *"khoá cố định mốc 2026-07-20"*. Doc chưa cập nhật → **[L14]**.
- **Lệch vintage thật sự lớn:** WorldCover 2021 vs WorldPop 2025 vs OSM 07/2026 vs telemetry 07/2026 —
  khoảng cách 5 năm giữa lớp đất đai và lớp cầu. P9 vẫn `☐ Open` và **đúng là còn open**.
- **Gap 313,5 h trong tầng "lưới 5′"** là con số mới, chưa nằm trong bất kỳ doc nào → **[L9]**.

---

### B.3 · Định danh & dedup — khoá join, gộp nhầm

**Đã kiểm chứng bằng:** BallTree haversine trên toàn bộ 19.805 trạm canonical + chạy lại
`rapidfuzz.token_set_ratio` với đúng ngưỡng của module.

Đây là **phát hiện lớn nhất của review này**. Xem [L1].

| Đại lượng | Trước fix 29/07 (doc) | Sau fix 29/07 (đo lại) |
|---|---:|---:|
| dòng `is_primary=False` | 329 | **30** |
| nhóm trùng | 289 | **27** |
| `dup_method = coord_name` | 318 | **8 dòng / 4 nhóm** |
| `dup_method = official_store` | 11 | **49 dòng / 23 nhóm** |
| nhóm lớn nhất | 4 | 3 |

**Cơ chế:** `_distinct_store` chặn merge khi hai dòng có `official_store_id` **khác nhau**. Nhưng:

```
official_store_id == station_code  :  19.605 / 19.635  (99,85%)
station_code là PK unique          :  19.805 / 19.805
⇒ với mọi cặp dòng phân biệt, official_store_id LUÔN khác nhau
⇒ tầng T2 `coord_name` chết cho 99,85% bảng
```

Bằng chứng trong docstring của chính module (*"2.625 cặp <50 m đều có store_id khác nhau, 0 cặp trùng"*)
là **hệ quả của phép lặp thừa**, không phải bằng chứng độc lập.

**338 cặp bị chặn** có `token_set_ratio ≥ 82`, trong đó **97 cặp tên trùng khít**:

| station_code A | station_code B | name |
|---|---|---|
| C.TVI0003 | C.TVI0013 | `Vincom Plaza Trà Vinh` |
| C.STR0001 | C.STR0012 | `Vincom Plaza Sóc Trăng` |
| C.SLA0002 | C.SLA0010 | `Vincom Plaza Sơn La` |
| C.DTH10562 | C.DTH10673 | `Tư nhân NGUYỄN TẤN QUỐC, tổ 8, ấp mỹ tường, xã mỹ thiện, tỉnh đồng tháp` |
| C.TGI0073 | C.TGI0074 | `Nhượng quyền CÔNG TY TNHH KING PALACE` / `CÔNG TY TNHH KING PALACE` (1 vs 6 trụ) |

**Tất cả đều `is_primary=True`** ⇒ đếm 2 lần trong cung. Toàn bảng: **2.639 cặp <50 m mà cả hai đều primary**;
**201 nhóm / 472 trạm trùng khít toạ độ tuyệt đối** mà cả nhóm đều primary.

Guard **có phần đúng**: một số cặp thật sự là hai trạm riêng (`Văn Hiền 1` / `Văn Hiền 2` cách nhau vài mét,
`Nha Khoa Hải Vân 1` / `Hải Vân 2`). Vấn đề không phải "guard sai hướng" mà là **guard không trả lời câu hỏi
nó tự đặt ra** — nó hỏi "hai dòng này có khác PK không", không hỏi "first-party có coi đây là hai cửa hàng không".

---

### B.4 · Độc lập nguồn — nguồn nào phái sinh từ nguồn nào

**Đã kiểm chứng bằng:** so `official_store_id` với `station_code` trên toàn bảng canonical.

> **`vinfastauto.com` KHÔNG phải nguồn độc lập với `evcs.vn`. Đã chứng minh, không còn là nghi vấn.**

- `match_method = exact_code` cho **19.604/19.805 (99,0%)**, và exact_code nghĩa là `station_code == store_id`.
- Doc E-DQ2 tự ghi: khoảng cách toạ độ giữa hai nguồn **max 0,3 m, p99 = 0,0**.
- `coord_quality.py` docstring cũng tự kết luận điều này (*"registry và evcs.vn cùng một backend"*) — và
  dùng nó để **chính đáng hoá việc không sửa toạ độ**. Đúng.

**Nhưng cùng một sự thật lại bị dùng ngược ở ba chỗ khác — đây mới là vấn đề:**

| Chỗ dùng | Giả định ngầm | Thực tế |
|---|---|---|
| `dedup._distinct_store` | store_id là **trọng tài định danh** | store_id = station_code ⇒ trọng tài rỗng (**[L1]**) |
| `verified` / `confidence` (`0,4·completeness + 0,6·verification`) | official **chứng thực** evcs | tự chứng thực chính mình ⇒ `confidence` TB 0,995 là **vô nghĩa** (**[L2]**) |
| quét bổ sung 298 trạm 07-29 (seed từ registry) | registry phủ được nguồn mới | trạm evcs-only (**170 dòng `match_method=none`**) không bao giờ được seed (**[L11]**) |

`verified = True` cho **19.632/19.805 (99,1%)** — một cột hằng số, không mang thông tin, nhưng đang được
`_pick_survivor` dùng làm tiêu chí xếp hạng.

---

### B.5 · Đầy đủ — null theo cột / theo tỉnh, ô bị mặt nạ loại oan

**Đã kiểm chứng bằng:** `isna().mean()` toàn bảng + group theo tỉnh (join `station_admin.parquet`).

**Cột canonical:**

| Cột | % null | Đánh giá |
|---|---:|---|
| `admin_l1_code`, `province_name`, `commune_name`, `commune_kind` | **100,00%** | ⛔ 4 cột chết trong hợp đồng (**[L5]**) |
| `dup_dist_m` / `dup_group_id` / `dup_method` | 99,85 / 99,71 | hệ quả [L1] |
| `current_type`, `max_power_kw`, `total_power_kw` | 1,43 | 283 trạm không connector |
| `official_*`, `match_dist_m` | 0,86 | 170 trạm evcs-only |
| `status` / `is_public` (thô) | 0,36 / 0,40 | đã có `op_status`/`access` thay |

**Theo tỉnh:** đủ **34/34** tỉnh. Không tỉnh nào bị bỏ. Chất lượng khá đồng đều — `%current_type UNKNOWN`
dao động 0,0–4,7%; `%không có telemetry` 0,0–4,7%. **Top 5 tỉnh chiếm 40,9% cung** (HN 2.545 · HCM 2.329 ·
Bắc Ninh 1.124 · Phú Thọ 1.098 · Đồng Nai 1.000) — tập trung nhưng đúng với phân bố dân số/xe.

**Ô lưới bị loại oan:** đây là chỗ nặng nhất của trục này.

| Đo trên 302.863 ô `buildable` | Số ô | % |
|---|---:|---:|
| `pop` (2020) = **NaN** | 204.632 | **67,6%** |
| `pop_2025` = NaN | 11.308 | 3,7% |
| `pop`=NaN **nhưng** `pop_2025 > 0` | **193.693** | **64,0%** |
| `pop`=NaN **nhưng** có đường | 146.982 | 48,5% |

**13,12 triệu người** nằm ở nhóm dòng 3 — và bị chấm điểm 0 ở bước sinh T4 (**[L3]**).

---

### B.6 · Ngữ nghĩa giá trị thiếu — `fillna(0)` trộn "bằng 0" với "không biết"

**Đã kiểm chứng bằng:** đọc dtype + null count `demand_h3`, rồi truy vết từng consumer.

**Ở tầng bảng: ĐÃ SỬA ĐÚNG.** `demand_h3` giữ `pop`/`pop_2025`/`road_len_*` là `NaN` khi nguồn không phủ,
kèm 3 cờ `pop_covered` (33,1%) / `pop_2025_covered` (96,3%) / `osm_covered` (78,7%). Đây là fix chuẩn mực.

**Ở tầng quyết định: BỊ HOÀN TÁC.** `build_candidates.py:130` gọi `.fillna(0.0)` ngay lập tức trên đúng
những cột đó, trước khi tính điểm chọn T4. Fix chỉ đi được nửa đường (**[L3]**).

Ba chỗ `fillna` khác đã kiểm và **không gây hại hiện tại** (ghi lại để không ai gỡ nhầm):

| Chỗ | Rủi ro lý thuyết | Đo thực tế |
|---|---|---|
| `settlement.land_support:187-188` | ô thiếu landuse → `built=0` → gắn cờ `pop_no_built` oan | **7 ô thiếu / 0 ô bị cờ oan** — latent, chưa nổ (**[L12]**) |
| `build_osm_h3.aggregate:98-100` | ô không POI → 0 | đúng nghĩa: đếm POI, không có = 0 thật |
| `settlement.classify` NaN→0 | DEGURBA coi không-phủ = 0 dân | nhất quán với định nghĩa `pop`; có test khoá |

---

### B.7 · Độ chính xác toạ độ

**Đã kiểm chứng bằng:** group theo `(lat,lng)`, BallTree, đối chiếu `station_admin.parquet`.

| Kiểm tra | Kết quả |
|---|---|
| `lat`/`lng` null | **0** |
| điểm (0,0) | **0** |
| `h3_r8` null | **0** |
| nhóm toạ độ **trùng khít tuyệt đối** | **207 nhóm / 484 trạm** |
| ngoài mọi đa giác tỉnh | **4** (toạ độ chắc chắn hỏng) |
| ngoài mọi đa giác xã | **18** (yếu hơn — có khe hở lớp xã ven biển) |
| `COORD_LOW_TRUST` (≥2 tín hiệu) | **171** |
| `DUP_COORD_SUSPECT` | **214** |
| toạ độ bị **sửa** | **1** (`COORD_REPAIRED_OFFICIAL`) |

**Đánh giá phương pháp: đây là phần làm tốt nhất về mặt tư duy.** Kết luận *"E-DQ1 là bài toán gắn cờ,
không phải bài toán sửa"* được rút ra từ một phép đo đúng (không có nguồn độc lập → không có quyền sửa),
và ngưỡng ≥2 tín hiệu được biện minh bằng dương tính giả cụ thể của từng tín hiệu. `test_coord_quality.py`
khoá đúng những bất biến quan trọng (không sửa dòng, không sửa toạ độ, cờ cộng thêm, idempotent).

Bằng chứng cụ thể cho thấy cụm placeholder là thật — hai trạm cùng toạ độ nhưng **địa chỉ ở hai tỉnh khác nhau**:

```
@(8.694218, 106.603142)  C.HCM17177 "…phường Tam Thắng, TP. Hồ Chí Minh"
                         C.HYE10751 "…Đặc Khu Côn Đảo, TP HCM"
@(10.338400, 106.264000) C.BNI11161 "…phường Vân Hà, tỉnh Bắc Ninh"      ← toạ độ tròn khả nghi
                         C.DTH10733 "…Xã Kim Sơn, Tỉnh Đồng Tháp"
@(10.243678, 105.343567) 4 trạm mã C.HBI*/C.QNI* (Hoà Bình / Quảng Ngãi) — toạ độ ở An Giang
```

⚠ **Nhưng cách áp cờ thì hỏng** — xem [L6]: cờ này được ghim vào canonical bằng **swap thư mục thủ công**.

---

### B.8 · Nhất quán schema so với `schema-contract.md`

**Đã kiểm chứng bằng:** đọc dtype + value_counts từng cột, đối chiếu từng dòng của contract.

**Đạt:**

| Ràng buộc contract | Đo lại |
|---|---|
| `station_id` PK unique | 19.805/19.805 ✅ |
| FK `connectors.station_id → stations` | 0 orphan ✅ |
| `num_connectors == Σ count_total` | 0/19.805 lệch ✅ |
| `op_status` ∈ {OPERATIONAL, MAINTENANCE, OUT_OF_SERVICE, UNKNOWN} | ✅ (16.123 / 3.411 / 212 / 59) |
| `access` ∈ {PUBLIC, RESTRICTED, UNKNOWN} | ✅ (19.716 / 22 / 67) |
| `is_operational == False ⇔ op_status == OUT_OF_SERVICE` | ✅ crosstab khớp tuyệt đối |
| `connector_standard` ∈ {CCS2, TYPE2, UNKNOWN} | ✅ (8.660 / 15.855 / 272) |
| `candidate_sites` unique theo `h3_r8` | 22.219/22.219 ✅ |
| Parquet Hive-partition theo `province_code` | ✅ |
| F13: không suy AC/DC từ ngưỡng kW | ✅ đã bỏ sạch |

**Không đạt:**

| Vi phạm | Số | ID |
|---|---:|---|
| 4 cột admin của `stations` null 100% | 19.805 | [L5] |
| `current_type` = `NaN` (ngoài enum khai báo) | 283 | [L15] |
| `vehicle_class = UNKNOWN` — contract mô tả nhưng không giải thích ca "không connector" | 283 | [L15] |
| `demand_h3` có **10 cột** không có trong contract (`pop_k1`, `dens_ppkm2`, `settlement_class`, `cluster_*`, `centre_*`, `pop_unsupported`) | — | [L16] |
| `size_ceiling` gate = **80.000** national, contract §P5 ③ vẫn ghi **3.000** | — | [L16] (đã ghi ở `candidate-sites.md` §195, chỉ contract chưa đồng bộ) |

---

### B.9 · Thiên lệch lấy mẫu

**Đã kiểm chứng bằng:** join POI với `settlement_class`, đọc `merge_catalog._sources()`, so header CSV.

**(a) Thiên lệch đô thị của OSM — đo được, nặng:**

| | ô | POI | dân |
|---|---:|---:|---:|
| URBAN_CENTRE | 11.876 (3,8%) | **11.702 (68,4%)** | 45,88M (46,1%) |
| URBAN_CLUSTER | 41.191 (13,1%) | 3.523 (20,6%) | 43,77M (43,9%) |
| RURAL | 261.837 (83,1%) | **1.881 (11,0%)** | 9,97M (10,0%) |

T4 gap-fill tồn tại **chính xác để bù chỗ này**. Nhưng T4 chấm điểm bằng `pop` 2020 vốn NaN ở 67,6% ô
buildable — mà phần NaN đó **tập trung ở nông thôn** (64,0% số ô đó có `pop_2025 > 0`). ⇒ **Hai lớp thiên
lệch đô thị chồng lên nhau, và cơ chế chống thiên lệch bị chính lỗi mặt nạ vô hiệu hoá.** ([L3])

**(b) Enum `hours` {24, 168, 720} — ĐÃ ĐÓNG ĐÚNG.** `evcs_scrape.py` fail-fast nếu ngoài enum
(`hours_outside_server_enum_fails_fast` có test). Giá trị ngoài enum trước đây timeout 100% im lặng.

**(c) Ràng buộc 1-phiên-Cloudflare — ĐÃ ĐÓNG ĐÚNG và là thiết kế tốt.** `session.py` giữ profile Chromium
bền vững (`data/.cache/cf_profile`), mượn lại `__io_args` (kèm hàm `auth`) của chính trang, một request
in-flight, vứt+dựng lại socket sau **mọi** nhánh hỏng. Đó là điều kiện **đủ** cho F3 (chỉ `socket.off` là
chưa đủ, docstring lập luận đúng). Chi phí 0,37 s/trạm.

**(d) Tầng lấy mẫu — tách đúng, nhưng chưa được cưỡng chế.** `TS_DIR_168H` / `TS_DIR_720H` riêng biệt
(19.218 vs 19.426 file), timestamp chồng khớp ~0. Nhưng `run_pipeline.sh` không truyền `--ts-dir` ([L7]).

**(e) Thiên lệch discovery mới — chưa được ghi nhận ở đâu:** 298 trạm thêm ngày 29/07 được tìm bằng
**seed có đích từ registry VinFast**, khác hẳn cơ chế quét lưới của 28.625 trạm còn lại. Cột `is_new`
bị `extrasaction="ignore"` loại khỏi catalog gộp, `tab` ghi `cs` cho cả hai ⇒ **không có cách nào phân biệt
hai cơ chế lấy mẫu ở hạ nguồn** ([L11]). Đã kiểm: 298/298 là trạm hoàn toàn mới (0 chồng với cs/other/bss),
nên không có vấn đề "giá trị cũ đè giá trị mới" — chỉ có vấn đề provenance.

---

### B.10 · Nhãn & mục tiêu

**Đã kiểm chứng bằng:** đọc `data/interim/assess/occupancy_f19.{parquet,meta.json}`, `de-bai-v2.md` §7, §9.

**Trong repo này KHÔNG có nhãn giám sát.** Thứ gần nhất là `occupancy_f19.parquet`:

```
19.218 trạm · occ_mean_dw · duration_observed_s · duration_coverage · max_gap_ms · n_obs · ever_active
source_sha256 = 2e6bd5f9…  ← khớp MANIFEST entry data/raw/evcs/load_ts.csv (tầng 168h)
```

Ba vấn đề đo được:

1. **Nó dựng trên tầng 168h cũ** (19.218 trạm, cửa sổ 07-13→07-21), trong khi `de-bai-v2` §7.1 định nghĩa
   `S₀` bằng **telemetry 720h** (19.426 trạm, 06-29→07-29). Hai tập bằng chứng vận hành không khớp ([L9]).
2. **`occ_mean_dw` không phải "hiệu suất"** — `de-bai-v2` §7.3 chỉ ra ba đại lượng đang cùng tên. Trung vị
   0,145 là *số trụ bận đồng thời*, không phải tỷ lệ. Áp ngưỡng 30% của BO lên nó chặn ~74,8% mạng DC.
3. **Chính sách cap 30′/khoảng của F19 chỉnh cho tầng 168h**, đang cắt ~45% tổng thời lượng ở cả hai tầng;
   `de-bai-v2` §8.3 đo lệch cohort ~19% ⇒ **19% throughput = 19% doanh thu**. Chưa suy lại cho 720h ([L9]).

**Mất cân bằng lớp:** `CHƯA KIỂM CHỨNG` — tập ground-truth NEW-HIGH (1.271 điểm) nằm ở repo `evcs-dataset`,
không có trong repo này. Chỉ kiểm được metadata của nó qua `holdout_split.json`.

**Rò nhãn:** `CHƯA KIỂM CHỨNG trong repo này` — feature và nhãn được dựng ở repo `evcs-dataset`; không đọc
được pipeline đó từ đây nên không kết luận. **Rủi ro cần Kỳ tự kiểm:** nếu feature `occ` của trạm lân cận
lấy từ **cùng cửa sổ 720h** dùng để định nghĩa "trạm đã tồn tại", đó là contamination thời gian.

---

### B.11 · Tách train/test

**Đã kiểm chứng bằng:** đọc `data/interim/assess/holdout_split.json`.

**Có tách theo KHÔNG GIAN, và làm đúng chuẩn:**

```
block_res = 3 (H3 r3 ≈ 12.400 km²) · 47 block · 18 block holdout
n_points 1.271 → design 763 / holdout 508 (39,97%)
leak check: leak_radius 6 km → 17 điểm holdout rò (3,35%)
ground_truth_sha256 ghim
```

Đây là **spatial block CV có kiểm rò khoảng cách** — đúng thứ cần cho dữ liệu không gian, tốt hơn hẳn
random split. Ghi nhận.

**Nhưng KHÔNG có tách theo THỜI GIAN.** Và bản split này đã **cũ**:

- Sinh 2026-07-28, trước khi có +298 trạm, trước fix dedup (`de-bai-v2` §7.1 tự ghi *"fix dedup 29/07 trả
  +314 trạm về cung … nền covered0 = 18.839 đã cũ; mọi số neo phải tính lại"*).
- `ground_truth_sha256` ghim GT cũ ⇒ **split hết hiệu lực ngay khi rebuild**, nhưng không có gate nào bắt.
- File nằm ở `data/interim/assess/`, **không có trong MANIFEST** (manifest chỉ phủ `data/raw/`) ⇒ pre-registration
  không được content-address ([L13]).

---

### B.12 · Tái lập & provenance

**Đã kiểm chứng bằng:** chạy `make verify-snapshot`, `git check-ignore`, `pytest`, và mô phỏng lại đường
chạy sạch.

**Đạt:**

- `make verify-snapshot` → **PASS** (5 nguồn / 12 member / ~3,3 GB). Cổng nhanh hoạt động thật.
- `MANIFEST.json` được git track dù `/data/` bị ignore. ✅
- `freeze_snapshot` lưu bản manifest cũ trước khi ghi đè — **ý tưởng đúng** (chống F10 mồ côi).
- `pytest` → **84/84 PASS** trong 12,9 s.
- Ghi file atomic (`.tmp` + `os.replace`) ở `admin_join`, `coord_quality`, `settlement`, `split_timeseries`. ✅

**Không đạt — bốn lỗ, mỗi lỗ đủ để chặn:**

| # | Lỗ | Bằng chứng |
|---|---|---|
| [L4] | Lớp ranh giới VN ngoài repo, ngoài MANIFEST | `admin_dir()` → `../evcs-dataset/…`; `data/ref` không tồn tại; `grep -c vn_admin MANIFEST.json` = 0 |
| [L6] | Canonical bị sửa bằng **swap thư mục thủ công** | `stations.bak-precoordq` tồn tại; `coord_quality` in *"đổi chỗ thủ công sau khi eyeball"*; không có `make coord-quality` |
| [L10] | 298 trạm sinh bởi code **không có trong repo** | `evcs_stations_2026-07-29-new.csv` có cột `is_new`; `evcs_enumerate.FIELDS` không có, và dùng `extrasaction="ignore"` |
| [L8] | Manifest cũ lưu ra rồi **bị gitignore** | `git check-ignore -v data/raw/MANIFEST-2026-07-20.json` → khớp `.gitignore:18` |

**Hợp lại:** clone repo này ở máy khác → `make canonical` **crash** (thiếu lớp ranh giới), và nếu có lớp
ranh giới thì vẫn ra **19.265** thay vì **19.210** trạm baseline, **không có một cảnh báo nào**.

---

### B.13 · Trục thứ 13 — dataset đang chốt phục vụ bài toán đã bị rút

Không nằm trong 12 trục được giao, nhưng là rủi ro lớn nhất, nên ghi riêng.

`docs/README.md` nói `de-bai-v2.md` là **"ĐỀ BÀI HIỆN HÀNH (29/07) — Đọc file này TRƯỚC"**. File đó nói:

| | |
|---|---|
| **N1** | ρ(Δ phủ biên, util) = **−0,1144** ⇒ MCLP **FAIL gate G3** |
| **N2** | máy chấm v0 AUC **0,452** ⇒ **FAIL gate G2** (trần thật chỉ 0,698) |
| **N3** | mạng đã bão hoà: HN nền 0,9909, +20 trạm = +0,68 pp |
| §1.3 | *"coverage % theo ngân sách"* là tiêu chí **tự áp**, không có trong yêu cầu BO |
| §3 | thay bằng `ΔΠ(q,c\|S₀)` = cầu bắt được − cầu bị hút khỏi S₀ − chi phí |

Trong khi đó `schema-contract.md` vẫn khai `demand_h3` là *"Nguồn demand chính thức cho **MCLP**"* và
`candidate_sites` là *"Đầu vào candidate cho **MCLP**"*, và toàn bộ QA gate của `build_candidates` đo
**upper-bound coverage**.

Cụ thể, những gì `de-bai-v2` đòi mà dataset hiện chưa có:

| `de-bai-v2` đòi | Trạng thái dataset |
|---|---|
| §2.2 — **13.149 trạm chỉ-AC = tập ứng viên đã được xác thực** | ✅ **CÓ SẴN**: 13.353 trạm `current_type=AC` trong canonical. **Nhưng `candidate_sites` không chứa tầng nâng cấp nào** — 22.219 candidate chia T0/T1/T2/T4, không có tier "AC→DC" |
| §6.3 — **OSRM travel-time** thay Euclid | ❌ chưa có; mọi khoảng cách đang là haversine |
| §4.1 `cap_k` — sức chứa kWh/tháng | 🟡 dựng được từ `num_connectors × max_power_kw` (đã có, 0 lệch) |
| §8.2 A5 CapEx / A6 thuê mặt bằng — **hai tham số duy nhất đổi xếp hạng** | ❌ chưa có; `capex_class` hiện chỉ là proxy 3 mức từ `penalty` |
| §7.2 — 3.466 trạm registry `UNAVAILABLE` làm GT thứ hai | 🟡 có trong `official_stations.parquet`, chưa khai thác |
| §6.4 — thay T4 synthetic bằng mặt bằng thật liệt kê được | ❌ vẫn 5.701 điểm T4 synthetic |

⇒ **Khuyến nghị phạm vi:** chốt dataset **tầng cung + tầng cầu thô** (đúng, sạch, dùng được cho cả hai bài
toán) nhưng **không chốt `candidate_sites.parquet` như bàn giao cuối** — nó là artefact của hàm mục tiêu đã
bị rút. Xem §C.

---

### B.14 · DANH SÁCH ĐẦY ĐỦ LỖI LOGIC — [L1] … [L16]

*Đánh số liên tục, không cắt bớt. Cột "bằng chứng" là số đo lại trên `data/`, không phải số chép từ doc.*

---

#### [L1] Guard `_distinct_store` là phép lặp thừa của khoá chính → tầng dedup T2 chết

| | |
|---|---|
| **File** | `src/ev_siting/data/evcs/dedup_crosssource.py:108-116`, dùng ở `:185` |
| **Bảng** | `data/interim/canonical/stations`, `data/processed/covered0.parquet` |
| **Bằng chứng** | `official_store_id == station_code` cho **19.605/19.635 (99,85%)**; `station_code` unique 19.805/19.805 ⇒ guard ≡ `i ≠ j`. Hệ quả: `coord_name` **318 → 8 dòng (4 nhóm)**; `is_primary=False` **329 → 30**; nhóm trùng **289 → 27**. **338 cặp** <50 m sim ≥82 bị chặn, **97 cặp sim = 100** (`Vincom Plaza Trà Vinh` ×2, `Vincom Plaza Sóc Trăng` ×2, `Vincom Plaza Sơn La` ×2, `Tư nhân NGUYỄN TẤN QUỐC…` ×2). **2.639 cặp <50 m mà cả hai đều `is_primary`**. |
| **Hạ nguồn** | Cung/`covered0`/anchor T0 đếm 1 trạm vật lý thành 2 ⇒ (a) `covered0` phóng đại cung; (b) `de-bai-v2` §3 `ΔΠ` — số hạng *"cầu bị hút khỏi S₀"* tính trên tập S₀ có trạm ma ⇒ **ước lượng ăn thịt sai hệ thống**; (c) T1 ground-truth của Kỳ nhiễm lại đúng lỗi F11 vừa đóng |
| **Mức** | 🔴 **CHẶN** |
| **Cách sửa** | Guard phải hỏi *"first-party có coi đây là hai cửa hàng không"*, và chỉ hỏi được khi có **thuộc tính official độc lập với station_code** (địa chỉ official khác nhau, toạ độ official cách nhau > 0, `official_admin` khác nhau). Tối thiểu: `_distinct_store` trả `False` khi `store_id == station_code` ở **cả hai** dòng (không có thông tin ⇒ không chặn), rồi để blob-guard + name-sim quyết như cũ. Thêm test đối kháng: cặp trùng tên + trùng toạ độ + khác store_id **phải** merge. |

---

#### [L2] `verified` / `confidence` là tự chứng thực

| | |
|---|---|
| **File** | `src/ev_siting/data/evcs/transform_canonical.py` (join xref), `dedup_crosssource._pick_survivor:96-105` |
| **Bằng chứng** | `verified=True` cho **19.632/19.805 (99,1%)**; `confidence` TB **0,995**. Công thức `0,4·completeness + 0,6·verification`, mà `verification` đến từ nguồn trùng khớp `station_code` 99,85%. |
| **Hạ nguồn** | `_pick_survivor` xếp hạng theo `_matched`/`_conf` — hai cột gần như hằng số ⇒ thực tế chỉ còn `station_id` nhỏ nhất quyết định survivor (tất định nhưng **tuỳ tiện**). Mọi lọc theo `confidence` là no-op. |
| **Mức** | 🟠 **CAO** |
| **Cách sửa** | Đổi tên thành `first_party_code_match` (mô tả đúng thứ nó đo), và **bỏ khỏi công thức `confidence`**. `confidence` giữ đúng `completeness`. Ghi rõ trong contract rằng dự án **không có** nguồn xác minh độc lập. |

---

#### [L3] `.fillna(0.0)` hoàn tác fix NaN≠0 ngay tại điểm ra quyết định T4

| | |
|---|---|
| **File** | `src/ev_siting/features/build_candidates.py:130` |
| **Bảng** | `data/processed/candidate_sites.parquet` (5.701 điểm T4) |
| **Bằng chứng** | Trên 302.863 ô buildable: `pop` = NaN **204.632 (67,6%)**; trong đó **193.693 ô (64,0%)** có `pop_2025 > 0`, tổng **13,12M người** bị chấm điểm 0. Tái lập điểm số với `pop_2025` thay `pop`: chỉ **82,5%** T4 hiện tại còn được chọn ⇒ **17,5% tập T4 đổi** thuần do chọn niên đại. |
| **Hạ nguồn** | T4 là tầng **chống thiên lệch đô thị** (P5). Phần NaN tập trung ở nông thôn ⇒ cơ chế chống thiên lệch bị chính lỗi mặt nạ vô hiệu hoá. Điểm T4 là *toạ độ đề xuất xây* ⇒ sai ở đây thành khuyến nghị sai. |
| **Mức** | 🟠 **CAO** |
| **Cách sửa** | Đừng `fillna` mù. Dùng `pop_eff = pop.where(pop_covered, pop_2025)` (hoặc chạy hai lần và báo độ nhạy như P10 đã hứa). Nếu vẫn muốn 0, phải là `pop.fillna(0).where(pop_covered)` + **log số ô bị ảnh hưởng**. |

---

#### [L4] Lớp ranh giới VN — nằm ngoài repo, ngoài MANIFEST, ngoài mọi cổng verify

| | |
|---|---|
| **File** | `src/ev_siting/vn_boundary.py:38-53`, `src/ev_siting/data/evcs/admin_join.py:44-73` |
| **Bằng chứng** | `admin_dir()` → `/home/…/internVSF/evcs-dataset/data/ref/vn_admin/valid_from=2025-07-01`. `data/ref` **không tồn tại** trong repo này. `grep -c vn_admin data/raw/MANIFEST.json` = **0**. `make verify-snapshot` vẫn **PASS**. |
| **Hạ nguồn** | Lớp này gác: cắt POI (−20.256 điểm), cắt lưới `demand_h3`, cắt T4, cổng `poi_coords_in_vn`, `admin_join` (19.805 dòng), 2/5 tín hiệu của `coord_quality`. Đổi lớp ⇒ **mọi con số E-DQ11 đổi im lặng**. Clone repo đơn lẻ ⇒ `SystemExit`. |
| **Mức** | 🔴 **CHẶN** |
| **Cách sửa** | Copy `provinces.parquet`/`communes.parquet` vào `data/ref/vn_admin/valid_from=2025-07-01/`, thêm nguồn `vn_admin` vào `manifest.source_specs()` (license **ODbL** — ghi rõ), `make freeze` lại. Giữ `_FALLBACK` nhưng in **cảnh báo lớn** khi rơi vào nhánh đó. |

---

#### [L5] Bốn cột admin của `stations` null 100% — hợp đồng khai cột chết

| | |
|---|---|
| **File** | `src/ev_siting/data/evcs/admin_join.py:222-231` (cố ý ghi bảng phụ), `docs/schema/schema-contract.md` §2 `stations` |
| **Bằng chứng** | `admin_l1_code` / `province_name` / `commune_name` / `commune_kind` = **19.805/19.805 null (100,0%)**. Bảng phụ `station_admin.parquet` có đủ (null 0,02% / 0,09%). |
| **Hạ nguồn** | Contract nói 2 cột này để *"Nối `agg_admin`, lọc theo tỉnh"*. Consumer làm đúng contract sẽ lọc ra **rỗng**. Mọi thống kê theo tỉnh (kể cả bảng §B.5 của review này) buộc phải join thủ công bảng phụ. |
| **Mức** | 🟠 **CAO** (hợp đồng sai, không phải dữ liệu sai) |
| **Cách sửa** | **Không nhập vào canonical** — lý do license (ODbL) là **đúng và nên giữ**. Sửa `schema-contract.md`: chuyển 4 cột sang bảng `station_admin` với ghi chú license, đánh dấu 4 cột trong `stations` là **deprecated/luôn null** hoặc bỏ hẳn. |

---

#### [L6] Canonical bị sửa bằng swap thư mục thủ công → pipeline không tái lập được kết quả đã giao

| | |
|---|---|
| **File** | `src/ev_siting/data/evcs/coord_quality.py:203-207`; `Makefile` (không có target); `transform_canonical.py` (không biết `COORD_LOW_TRUST`) |
| **Bằng chứng** | `data/interim/canonical/stations.bak-precoordq` tồn tại, 19.805 dòng, **0 cờ `COORD_LOW_TRUST`**; bản live có **171**. Module in `"đổi chỗ thủ công sau khi eyeball"`. `features/paths.DIRTY_COORD_FLAGS` **đã** gồm `COORD_LOW_TRUST` và cả `build_candidates._load_stations` lẫn `build_covered0` lọc theo nó. Mô phỏng đường chạy sạch: dirty **271 → 214**, baseline **19.210 → 19.265** ⇒ **lệch 55 trạm**, tất cả gate vẫn PASS. |
| **Hạ nguồn** | `covered0` (nền coverage), tập T0, và mọi số dẫn xuất. Đây **đúng là F20** (*"code sinh snapshot mới hơn git HEAD"*) tái diễn, chỉ đổi module. |
| **Mức** | 🔴 **CHẶN** |
| **Cách sửa** | `transform_canonical` gọi `admin_join → coord_quality` như một bước cuối (hoặc thêm `make coord-quality` vào `make canonical`), ghi off-path rồi swap generation **tự động** như F12 đã làm cho canonical. Xoá `stations.bak-precoordq` sau khi đường chạy tự động cho kết quả bit-identical. |

---

#### [L7] `run_pipeline.sh` tham số hoá `--hours` nhưng không tham số hoá thư mục đích

| | |
|---|---|
| **File** | `src/ev_siting/data/evcs/run_pipeline.sh:56-60`; `paths.py:35-37`; `split_timeseries.py:64` |
| **Bằng chứng** | STEP 3 dùng `${EVCS_HOURS:-720}`; STEP 4 gọi `split_timeseries --input "$TS_RAW"` **không có `--ts-dir`** ⇒ luôn ghi vào `TS_DIR` = `evcs_timeseries_720h/`. Chạy `EVCS_HOURS=168 bash run_pipeline.sh` ⇒ dữ liệu **sự-kiện gap p50 2,09′** trộn vào thư mục **lưới 5′**. Đúng thứ `paths.py:31-36` và `de-bai-v2` §8.3 (*"cấm union mù"*) cấm. STEP 4 còn in sai đích: `-> data/interim/evcs_timeseries/`. |
| **Hạ nguồn** | Chuỗi mật độ mẫu không đồng nhất, **không truy nguyên được điểm nào thuộc tầng nào** ⇒ mọi thống kê cửa sổ (P3/F19) lệch. |
| **Mức** | 🟠 **CAO** (chưa nổ, nhưng một biến môi trường là nổ) |
| **Cách sửa** | `TS_OUT=$([[ "${EVCS_HOURS:-720}" == "168" ]] && echo "$TS_DIR_168H" || echo "$TS_DIR_720H")` rồi `--ts-dir "$TS_OUT"`; hoặc để `split_timeseries` tự suy thư mục từ `hours` ghi trong header/metadata của raw run. Sửa dòng `echo`. |

---

#### [L8] Manifest cũ được lưu ra rồi bị `.gitignore` nuốt

| | |
|---|---|
| **File** | `src/ev_siting/data/provenance/freeze_snapshot.py:56-70`; `.gitignore:16-19` |
| **Bằng chứng** | `git check-ignore -v data/raw/MANIFEST-2026-07-20.json` → khớp `.gitignore:18 /data/raw/*`. Chỉ `!/data/raw/MANIFEST.json` (dòng 19) được re-include. |
| **Hạ nguồn** | Comment của chính đoạn code nói mục đích là chống *"bàn giao dựa trên snapshot cũ thành mồ côi — không còn checksum nào để đối chiếu"*. Mục đích đó **không đạt**: `MANIFEST-2026-07-20.json` chỉ tồn tại trên máy này. Bàn giao v4 (28/07) neo snapshot 07-20 ⇒ đúng lại là F10. |
| **Mức** | 🟡 **TRUNG** |
| **Cách sửa** | Đổi `.gitignore:19` thành `!/data/raw/MANIFEST*.json`. Thêm cổng E-DQ10 ⑤: khẳng định mọi `MANIFEST*.json` đều git-tracked. |

---

#### [L9] Hai tầng telemetry không đồng bộ với nhau và với tầng nhãn

| | |
|---|---|
| **File** | `paths.py:37` (`TS_DIR` đổi nghĩa), `build_master_evcs.py:154`, `validate.py:71`, `data/interim/assess/occupancy_f19.meta.json` |
| **Bằng chứng** | `TS_DIR` trước trỏ `evcs_timeseries/`, nay mặc định `evcs_timeseries_720h/` ⇒ `has_timeseries` và cổng QA 1:1 tính trên **19.426** file, còn `occupancy_f19` (`source_sha256 = 2e6bd5f9…` = `load_ts.csv` tầng 168h) tính trên **19.218** trạm. Docstring `build_master_evcs.py:7,14,151` và `validate.py:14` vẫn ghi `data/interim/evcs_timeseries/`. Tầng 720h có **max gap 313,5 h (13 ngày)** — không phải "lưới 5′" đồng đều như tên gọi. |
| **Hạ nguồn** | `de-bai-v2` §7.1 định nghĩa `S₀` bằng telemetry 720h; §8.3 nói chính sách cap 30′ (chỉnh cho 168h) đang cắt ~45% thời lượng và làm lệch cohort ~19% ⇒ **19% doanh thu**. Nhãn/feature và định nghĩa cung đang đứng trên hai tầng khác nhau. |
| **Mức** | 🟠 **CAO** |
| **Cách sửa** | (a) Đặt tên hằng số tường minh, không để `TS_DIR` đổi nghĩa ngầm — buộc mọi consumer chọn `TS_DIR_168H`/`TS_DIR_720H`; (b) rebuild `occupancy_f19` trên 720h; (c) suy lại chính sách cap riêng cho 720h và pre-register nó; (d) sửa docstring. |

---

#### [L10] 298 trạm trong snapshot đóng băng được sinh bởi code không có trong repo

| | |
|---|---|
| **File** | `src/ev_siting/data/evcs/merge_catalog.py:12-36`; `evcs_enumerate.py:79-95` |
| **Bằng chứng** | `evcs_stations_2026-07-29-new.csv` có **16 cột**, gồm `is_new`. `evcs_enumerate.FIELDS` có **15 cột**, không có `is_new`, và ghi bằng `DictWriter(..., extrasaction="ignore")` ⇒ **không thể** sinh cột đó. Không có mode seed-từ-registry trong `evcs_enumerate` (`grep add_argument` → chỉ `--enrich-from`). File đã nằm trong `MANIFEST.json` snapshot `2026-07-29`. 298/298 là trạm hoàn toàn mới. |
| **Hạ nguồn** | 298 trạm → canonical **19.507 → 19.805** → T0 → `covered0` → `candidate_sites`. Không tái sinh được. Lại là **F20**. |
| **Mức** | 🔴 **CHẶN** |
| **Cách sửa** | Commit script seed (thêm mode `--seed-from-official` vào `evcs_enumerate`), hoặc nếu là script ad-hoc thì đưa vào `src/…/evcs/` kèm docstring ghi 285 truy vấn/285 trạm. Thêm cổng QA: mọi file trong `CATALOG_DIR` phải sinh được bởi một entrypoint trong repo. |

---

#### [L11] Cơ chế discovery mới bị mất provenance trong catalog gộp

| | |
|---|---|
| **File** | `merge_catalog.py:71-78` (`fields` + `extrasaction="ignore"`) |
| **Bằng chứng** | Catalog gộp 28.923 dòng, cột `tab` = `{cs: 19.725, other: 80, bss: 9.118}` — 298 trạm seed-registry được gán `cs`, giống hệt 19.427 trạm quét lưới. Cột `is_new` bị loại. `'is_new' in header(evcs_catalog.csv)` = **False**. |
| **Hạ nguồn** | (a) Không phân biệt được hai cơ chế lấy mẫu ⇒ mọi phân tích "new supply" (chính là B4 của Kỳ) coi chúng đồng nhất; (b) seed từ registry ⇒ trạm evcs-only (**170 dòng `match_method=none`**) không bao giờ được tìm thấy bằng cơ chế mới — **thiên lệch discovery có hướng**, không ghi ở đâu; (c) không tách được vintage 07-21/22 vs 07-29. |
| **Mức** | 🟡 **TRUNG** |
| **Cách sửa** | Thêm 2 cột vào catalog gộp: `discovery = grid_scan\|registry_seed` và `crawl_date`. Ghi hạn chế của seed-registry vào `docs/sources/evcs.md`. |

---

#### [L12] `land_support` có thể bịa cờ `pop_no_built` từ dữ liệu thiếu (latent)

| | |
|---|---|
| **File** | `src/ev_siting/data/worldpop/settlement.py:186-191` |
| **Bằng chứng** | `built = landuse["built_up_frac"].fillna(0.0)` rồi `no_built = (built < 0.02) & (p > 500)` ⇒ ô **vắng mặt** khỏi `landuse_h3` thoả điều kiện chỉ vì thiếu dữ liệu. **Đo hiện tại: 7/314.904 ô thiếu landuse, 0 ô bị cờ oan.** |
| **Hạ nguồn** | Chưa có. Nhưng cờ này chặn ô khỏi nguồn T4 (`build_candidates:127-129`) nên khi `landuse_h3` chạy ở phạm vi khác (city) độ phủ sẽ khác. |
| **Mức** | ⚪ **THẤP (latent — báo để không gỡ nhầm, chưa gây sai số nào)** |
| **Cách sửa** | Thêm mask `landuse_known = landuse["built_up_frac"].notna()` và `and landuse_known` vào cả hai điều kiện; đếm + in số ô không có landuse. |

---

#### [L13] Split holdout không được content-address và đã cũ so với dữ liệu

| | |
|---|---|
| **File** | `data/interim/assess/holdout_split.json` |
| **Bằng chứng** | Sinh 2026-07-28. `ground_truth_sha256` ghim GT cũ. `de-bai-v2` §7.1 tự ghi *"fix dedup 29/07 trả +314 trạm về cung … nền covered0 = 18.839 đã cũ; mọi số neo phải tính lại"*. File nằm ở `data/interim/`, `MANIFEST` chỉ phủ `data/raw/` ⇒ không được freeze. Không có tách theo thời gian. |
| **Hạ nguồn** | Pre-registration mất hiệu lực im lặng. Với `n_holdout = 508` và `de-bai-v2` §6.1 cảnh báo khoảng tin cậy AUC ±0,18 ở n≈25/nhóm, việc split trôi là rủi ro thật cho T1. |
| **Mức** | 🟠 **CAO** |
| **Cách sửa** | Đưa `holdout_split.json` + GT vào MANIFEST (hoặc một `MANIFEST-derived.json` riêng cho artefact dẫn xuất). Thêm cổng: nếu `sha256(GT hiện tại) != ground_truth_sha256` thì **FAIL**, buộc pre-register lại. Bổ sung trục thời gian (holdout theo cửa sổ crawl) khi có ≥2 snapshot. |

---

#### [L14] `snapshot_id` trôi 07-20 → 07-29, doc neo không đổi

| | |
|---|---|
| **File** | `data/raw/MANIFEST.json:3`; `docs/known-issues.md` P9 + E-DQ10 |
| **Bằng chứng** | MANIFEST `snapshot_id = 2026-07-29`; known-issues P9 vẫn *"khoá cố định mốc 2026-07-20"*, E-DQ10 vẫn *"`snapshot_id = 2026-07-20` (neo P9)"*. Trong khi đó OSM PBF **vẫn là bản 07-20** (`replication_sequence 4852`) và WorldPop 2020 không đổi. |
| **Hạ nguồn** | Nhãn `2026-07-29` giờ trùm một bundle **trộn niên đại** (OSM 07-20 + catalog 07-21/22 + catalog 07-29 + telemetry 06-29→07-29). Bàn giao v4 neo `2026-07-20` không còn khớp `MANIFEST.json` hiện tại. |
| **Mức** | 🟡 **TRUNG** |
| **Cách sửa** | Cập nhật P9/E-DQ10 với snapshot mới + bảng vintage từng nguồn; hoặc giữ `snapshot_id` là ngày freeze và thêm trường `anchor_date` riêng cho mốc P9. |

---

#### [L15] `current_type = NaN` nằm ngoài enum contract

| | |
|---|---|
| **File** | `docs/schema/schema-contract.md` §2 `stations`; `transform_canonical.py` |
| **Bằng chứng** | `current_type`: AC 13.353 · DC 3.592 · MIXED 2.364 · UNKNOWN 213 · **NaN 283**. Contract khai enum `{AC, DC, MIXED, UNKNOWN}` — NaN không thuộc. 283 dòng này là trạm **không có connector nào**. |
| **Hạ nguồn** | Consumer viết `df[df.current_type == 'UNKNOWN']` bỏ sót 283 trạm; viết `.isin(['AC'])` để tìm tập ứng viên nâng cấp (`de-bai-v2` §2.2) cũng bỏ sót. Nhỏ nhưng là lớp lỗi im lặng. |
| **Mức** | ⚪ **THẤP** |
| **Cách sửa** | Điền `UNKNOWN` cho 283 dòng (đã có cờ `CURRENT_TYPE_UNVERIFIED`), hoặc thêm `NO_CONNECTOR` vào enum và ghi vào contract. |

---

#### [L16] Doc/contract trôi so với artefact thật

| | |
|---|---|
| **File** | `docs/schema/schema-contract.md` §2 (`demand_h3`, `candidate_sites`) |
| **Bằng chứng** | (a) `demand_h3` thực có **21 cột**; contract mô tả 11 + 4 (bản cập nhật 29/07) = 15 ⇒ **10 cột settlement không được khai** (`pop_k1`, `dens_ppkm2`, `settlement_class`, `cluster_id/pop/n_cells`, `centre_id/pop/n_cells`, `pop_unsupported`). (b) `size_ceiling` gate = **80.000** (đã ghi ở `candidate-sites.md:195`) nhưng contract + known-issues P5 ③ vẫn ghi **3.000**. (c) Cột settlement trong `demand_h3` là niên đại **2020**; bản `_2025` chỉ có ở `settlement_h3.parquet`, và hai bản **bất đồng 12,75% số ô** (crosstab: 484 ô URBAN_CENTRE-2020 thành RURAL-2025; 4.968 thành URBAN_CLUSTER; chỉ **6.424/11.876 = 54%** giữ nguyên URBAN_CENTRE). |
| **Hạ nguồn** | Consumer lọc `settlement_class == 'URBAN_CENTRE'` nhận một tập **khác 46%** tuỳ niên đại, và không nhìn thấy điều đó từ `demand_h3`. Đây đúng là thứ P10/E-DQ12 hứa *"đo độ nhạy thay vì chọn mù"* — nhưng cột đưa ra chỉ có một bản. |
| **Mức** | 🟡 **TRUNG** |
| **Cách sửa** | Khai đủ 21 cột vào contract, ghi rõ hậu tố rỗng = niên đại 2020; đưa `settlement_class_2025` + `pop_unsupported_2025` vào `demand_h3` (hoặc bắt consumer join `settlement_h3`); đồng bộ `size_ceiling`. |

---

### B.15 · Đối chiếu riêng các vấn đề đã biết — ĐÃ ĐÓNG THẬT CHƯA?

*Không tin doc. Mỗi dòng đọc code hiện tại + đo lại dữ liệu.*

| Vấn đề | Doc nói | **Đo lại 29/07** | Phán quyết |
|---|---|---|---|
| **dedup cross-source gộp nhầm 276/285 nhóm** | ☑ đã sửa bằng guard `_distinct_store` | Guard tautological (99,85% `store_id==station_code`); over-merge **đã hết** nhưng đổi thành **under-merge**: 338 cặp bị chặn, 97 cặp tên trùng khít, 2.639 cặp <50 m cả hai primary | 🔴 **ĐÓNG SAI — đổi lỗi này lấy lỗi khác** ([L1]) |
| **POI không cắt biên (54,2%)** | ☑ E-DQ11 | POI ngoài VN **0/17.106** · demand ngoài VN **0/314.904** · candidate ngoài VN **0/22.219** · `validate.poi_coords_in_vn` giờ hỏi bằng đa giác · 2 test khoá bbox-cũ sẽ fail | ✅ **ĐÓNG THẬT** (nhưng lớp ranh giới không version-hoá — [L4]) |
| **Mặt nạ WorldPop 2020 loại 60,3% ô có đường** | ☑ P10, thêm `pop_2025` + 3 cờ phủ | `pop_covered` **33,1%** · `pop_2025_covered` **96,3%**; NaN được giữ đúng ở tầng bảng; `worldpop_pop --vintage {2020,2025,all}` chạy được | 🟡 **ĐÓNG Ở TẦNG BẢNG, HỞ Ở TẦNG DÙNG** — `pop` 2020 vẫn là mặc định của `_gapfill` và `_qa_gate`, và `.fillna(0.0)` xoá lại thông tin ([L3]) |
| **`fillna(0)` nhập nhằng ở lớp demand** | ☑ | `demand_h3` giữ NaN đúng ✅; `build_candidates:130` fillna(0.0) ngay ❌; `settlement.land_support` fillna latent | 🟡 **NỬA ĐÓNG** ([L3], [L12]) |
| **Nguồn "official" không phải nguồn độc lập** | ghi ở docstring `coord_quality`, dùng đúng để **không sửa toạ độ** | Đã **chứng minh**: 19.605/19.635 = 99,85% `store_id == station_code`; `verified` 99,1% | 🔴 **NHẬN THỨC ĐÚNG, ÁP DỤNG SAI Ở 3 CHỖ** ([L1], [L2], [L11]) |
| **Enum `hours` {24,168,720}** | ☑ | `HOURS_ALLOWED=(24,168,720)`, `raise SystemExit` nếu ngoài enum, có test `hours_outside_server_enum_fails_fast` | ✅ **ĐÓNG THẬT** |
| **Tầng lấy mẫu 168h vs 720h** | ☑ tách thư mục | Tách đúng (19.218 vs 19.426 file; gap p50 2,09′ vs 5,0′). Nhưng `run_pipeline.sh` không truyền `--ts-dir` ⇒ `EVCS_HOURS=168` là trộn | 🟡 **ĐÓNG Ở HẰNG SỐ, HỞ Ở PIPELINE** ([L7]) |
| **1-phiên-Cloudflare của evcs.vn** | ☑ `session.py` | Profile bền vững + mượn `__io_args` (kèm `auth`) + 1 request in-flight + reset socket ở **mọi** nhánh hỏng; `.done` chỉ ghi khi có rows; `.failed` riêng | ✅ **ĐÓNG THẬT** — thiết kế đúng, lập luận "socket.off là chưa đủ" chính xác |

**Ngoài danh sách được giao, kiểm thêm:**

| | Đo lại | Phán quyết |
|---|---|---|
| F12 atomicity | `.tmp` + `os.replace` ở 4 module mới; canonical swap generation | ✅ |
| F16 test gap | 84/84 PASS; test mới phủ đúng logic rủi ro (STRtree direction, DEGURBA, ngưỡng 2 tín hiệu, bbox-vs-polygon) | ✅ **trừ một chỗ**: `test_dedup_never_merges_rows_with_distinct_official_store_id` (`test_f7_f12_integrity.py:180`) chỉ test ca thuận lợi (hầm B2/B3), **không có ca đối kháng** (trùng tên + trùng toạ độ) ⇒ test **khoá lại lỗi** [L1] thay vì gác nó |
| E-DQ3 (admin) | Join point-in-polygon đúng, 34/34 tỉnh, commune khớp 3.320 vs official 3.321 | ✅ chất lượng tốt, nhưng ở **bảng phụ** ([L5]) |
| E-DQ12 (settlement) | `pop_unsupported` 4.365 ô / 4,34M người; 18 "đô thị" 1-ô lộ ra đúng như doc; `_gapfill` loại chúng | ✅ **ĐÓNG THẬT**, phân tích DEGURBA là đóng góp thật |

---

### B.16 · Việc phải làm để chuyển sang ĐẠT

| Thứ tự | Việc | Ước lượng | Đóng |
|---|---|---|---|
| 1 | Copy `vn_admin/` vào `data/ref/` + thêm vào MANIFEST + `make freeze` | 30′ | [L4] |
| 2 | Sửa `_distinct_store` (không chặn khi `store_id == station_code`) + test đối kháng + rebuild | 2 h | [L1] |
| 3 | Nối `admin_join`+`coord_quality` vào `make canonical`, bỏ swap thủ công, xác nhận bit-identical | 2 h | [L6] |
| 4 | Commit script seed-registry (hoặc port sang `evcs_enumerate --seed-from-official`) | 2 h | [L10] |
| 5 | Bỏ `.fillna(0.0)` ở `_gapfill`, dùng `pop_eff`, rebuild candidate + báo độ nhạy 2 niên đại | 1 h | [L3] |
| 6 | `.gitignore` → `!/data/raw/MANIFEST*.json`; `run_pipeline.sh` truyền `--ts-dir` | 15′ | [L8], [L7] |
| 7 | Đồng bộ `schema-contract.md` (21 cột demand, 4 cột admin deprecated, size_ceiling, enum current_type) | 1 h | [L5], [L15], [L16] |

Sau bước 1–4 dataset **tái lập được**; sau bước 5–7 **khớp hợp đồng**. Ước tính tổng **~1 ngày công**.

---
---

## PHẦN C — CÒN THIẾU DỮ LIỆU GÌ ĐỂ BAO QUÁT BÀI TOÁN

### C.0 · Cây quyết định — và vì sao thứ tự ưu tiên đã đổi

Xuất phát từ `de-bai-v2` §3: đại lượng quyết định không còn là *phủ*, mà là

```
ΔΠ(q, c | S₀) = DT_bắt_được(q,c) − DT_bị_hút_khỏi_S₀ − (CapEx/T + OpEx)
                 └── CẦU ────────┘  └── CUNG/CẠNH TRANH ┘  └── CHI PHÍ ──┘
                                                          ↑ RÀNG BUỘC KỸ THUẬT lọc trước
                                                          ↑ KẾT QUẢ hiệu chuẩn cả ba
```

Điều này **đảo thứ tự ROI** so với thời MCLP:

- Thời MCLP, thứ đắt giá nhất là **cầu** (dân số, POI) vì hàm mục tiêu là phủ dân.
- Với `ΔΠ`, dân số chỉ là *một* đầu vào của `d_j`, và `de-bai-v2` đã đo rằng nó **không dự đoán được**
  nơi operator chọn (G2: AUC 0,452, **trần thật 0,698**). Thứ đắt giá nhất giờ là **(i) khoảng cách đi
  được thật**, **(ii) kết quả vận hành có mốc thời gian (COD)**, **(iii) hai tham số chi phí biến thiên
  theo site** — vì `de-bai-v2` §8.1 chứng minh chỉ tham số **biến thiên theo site** mới đổi xếp hạng.

### C.1 · Bảng xếp hạng lớp dữ liệu còn thiếu

*Sắp giảm dần theo ROI, rồi theo khả thi. ROI/Khả thi thang 1–5.*

| # | Lớp dữ liệu | Biến cụ thể | Vì sao cần (giả thuyết / feature) | Nguồn ứng viên | ROI + lý do | Khả thi (license/chi phí/công/độ trễ) | Proxy tạm | Rủi ro pháp lý-ToS |
|---|---|---|---|---|---|---|---|---|
| **1** | **Ma trận thời gian lái** | `T[j,k]` giây, j = ô H3 r8, k = trạm | `de-bai-v2` §6.3 gọi Euclid là *"giới hạn nghiêm trọng nhất"*. Đĩa Euclid băng sông Hồng/Sài Gòn ⇒ catchment sai **hệ thống**, không ngẫu nhiên. Là đầu vào bắt buộc của `z_jk = 0 nếu T[j,k] > T_max` | **OSRM self-host** trên chính `vietnam-latest.osm.pbf` **đã có trong MANIFEST** | **5** — sửa đồng thời `d_j`, ràng buộc catchment, và số hạng ăn thịt. Không lớp nào khác chạm được cả ba | **5** — BSD-2, chi phí 0đ, PBF đã đóng băng, dựng trong ngày | vành haversine 3 km hiện tại | **0** — dữ liệu đã có, self-host |
| **2** | **Kết quả vận hành có mốc thời gian** | `COD` (ngày vận hành thương mại), kWh/phiên hoặc số phiên/ngày | `de-bai-v2` §2.1③ + §7.4: **không có COD ⇒ không phân biệt được ramp-up với thất bại** ⇒ toàn bộ khuyến nghị "đóng/di dời" bị hạ xuống *danh sách theo dõi*. Có COD ⇒ mở được quasi-experiment trước/sau cho giả thuyết ăn thịt (hiện chỉ có ρ nội sinh nặng) | ① diff registry VinFast theo `generation` (hiện đã có gen 16); ② mốc xuất hiện đầu tiên trong chuỗi telemetry; ③ BO (không có quyền) | **5** — mở khoá ①③ trong ba loại quyết định, và là điều kiện của gate T3 | **4** — ① miễn phí nhưng phải **pull định kỳ từ hôm nay**; ② dựng ngay được từ 720h nhưng chỉ suy được COD cho trạm mở **sau** 06-29 | `first_seen` trong catalog 07-21/22 → cận trên thô của COD | 🟡 registry là first-party public; **pull định kỳ = tăng bề mặt ToS**, phải rate-limit |
| **3** | **Đăng ký xe điện theo tỉnh** | số ô tô điện lưu hành / tỉnh / quý; tách VinFast vs hãng khác | Mẫu số của **mọi** con số phủ. `de-bai-v2` §7.5: `cov_open` 0,925 ↔ `cov_neutral` **0,149** — băng **0,776**, giả định hở lớn nhất dự án. Cũng đóng P11 (dân số thô ≠ mật độ sở hữu ô tô) | Cục Đăng kiểm VN (công bố quý); VAMA/VinFast báo cáo bán hàng; GSO | **5** — biến kịch bản K1/K2 từ *caveat* thành *deliverable*; đóng P11 | **3** — công bố PDF/HTML không có API, phải parse tay; cấp **tỉnh** (không mịn hơn); độ trễ 1 quý | `pop_2025 × tỷ lệ sở hữu ô tô toàn quốc` (hằng số ⇒ **triệt tiêu khỏi xếp hạng**, gần như vô dụng) | ⚪ thấp — số liệu công bố công khai |
| **4** | **Giá thuê mặt bằng** | đ/m²/tháng theo phường/xã, phân lớp mặt tiền vs trong hẻm | `de-bai-v2` §8.2 A6: **một trong hai** tham số kinh tế được đánh dấu *"biến thiên theo site MẠNH → CÓ ảnh hưởng xếp hạng"*. Không có nó thì mọi khuyến nghị đều fail nghĩa vụ sensitivity của §8.3 | batdongsan.com.vn, chotot.com (tin cho thuê); giá đất Nhà nước theo QĐ tỉnh | **5** — thiếu nó thì **không khuyến nghị nào được phát** theo chính luật của dự án | **2** — scraping tin rao **vi phạm ToS**; giá đất Nhà nước thì public nhưng lệch xa giá thị trường | **giá đất Nhà nước theo bảng giá tỉnh** (public, đúng luật, dùng làm *hạng* chứ không dùng làm *mức*) | 🔴 **CAO** với batdongsan/chotot — ToS cấm scraping. Bảng giá đất tỉnh: ⚪ thấp |
| **5** | **CapEx theo cấu hình** | đ/trụ theo (kW, AC/DC), chi phí đấu nối theo cấp áp | `de-bai-v2` §8.2 A5 — tham số biến thiên theo site còn lại. `capex_class` hiện chỉ là proxy 3 mức suy từ `penalty` land-use, **không có đơn vị tiền** | vcharge.vn báo giá công khai; đơn giá EVN cho đấu nối; catalog nhà sản xuất | **4** — cho `cost_i(u_i)` một đơn vị thật; cần dùng **khoảng**, không dùng điểm | **4** — báo giá công khai, đọc tay ~20 dòng | `capex_class` hiện tại (chỉ xếp hạng, không định lượng) | ⚪ thấp — báo giá công khai |
| **6** | **Công suất lưới khả dụng tại site** | trạm biến áp trung thế + công suất còn trống, cấp áp | `de-bai-v2` §5.4: `d_substation_m` hiện có **AUC 0,499 = vô dụng**. Đây là ràng buộc kỹ thuật quyết định **có xây được DC không**, và không có gì thay được | EVN (không public); OSM `power=substation` (đã có, vô dụng); quy hoạch điện lực tỉnh (PDF) | **4** — chặn thật ở tầng khả thi; nhưng cũng là thứ **không lấy được** | **1** — EVN không public; quy hoạch tỉnh chỉ có sơ đồ, không có công suất trống | **giữ nguyên: ra cờ `Cần review thêm` + câu hỏi cụ thể cho khảo sát** (đúng §5.4) | ⚪ thấp (không lấy được thì không có rủi ro) |
| **7** | **Lưu lượng giao thông (AADT)** | xe/ngày-đêm theo đoạn QL/CT | `YÊU-CẦU` #1 nói nguyên văn *"lưu lượng xe"* — hiện dự án **không có biến nào** cho nó, đang thay bằng `road_len_mt_m` (chiều dài đường, không phải lưu lượng) | Tổng cục ĐBVN báo cáo đếm xe; VEC (cao tốc); Mapbox/TomTom Traffic Index (thương mại) | **4** — đóng một chữ trong yêu cầu gốc; đặc biệt cho trạm dọc tuyến (T3 rest_area còn ở roadmap) | **2** — công bố VN rời rạc, chỉ vài trăm mặt cắt/năm; API thương mại đắt | `road_len_mt_m` + hạng đường từ `.pbf` (đã có, chưa dùng hạng) | 🟡 API thương mại: license cấm redistribute |
| **8** | **Bãi đỗ ô tô có sức chứa** | số chỗ, có/không thu phí, giờ hoạt động | `de-bai-v2` §5.4 liệt kê *"số chỗ đỗ dành được cho sạc"* là cờ rà soát không quyết được bằng dữ liệu mở. `n_parking` hiện chỉ **đếm điểm** (2.463 điểm toàn quốc), không có sức chứa | OSM `capacity=*` trên `amenity=parking` (đã tải, chưa parse); khảo sát mall/toà nhà | **3** — nâng T1 parking từ "có POI" lên "có bao nhiêu chỗ" | **4** — dữ liệu **đã nằm trong PBF/Overpass đã tải**, chỉ cần parse thêm tag | `n_parking` hiện tại | ⚪ ODbL — như OSM hiện có |
| **9** | **Mạng lưới đối thủ** | trạm EVN/PetroVN/Porsche/EBOOST…: vị trí, số trụ, kW | Số hạng *"cầu bị hút khỏi S₀"* của `ΔΠ` hiện **chỉ tính trạm V-GREEN**. Dưới kịch bản K2 (mở mạng, §7.5) đối thủ vào cùng tập cạnh tranh | PlugShare, ChargeMap (crowdsourced); web từng hãng; OSM `amenity=charging_station` | **3** — quan trọng cho K2, ít quan trọng cho K1 (hôm nay V-GREEN gần như độc quyền ô tô điện VN) | **3** — OSM miễn phí nhưng phủ thưa ở VN; PlugShare ToS hạn chế | OSM `amenity=charging_station` từ PBF đã có | 🟡 PlugShare ToS cấm scraping; OSM ODbL |
| **10** | **Ngập lụt & độ dốc** | tần suất ngập, cao độ, độ dốc ô H3 | Loại cứng ở tầng khả thi. Trạm sạc DC ngập = rủi ro an toàn + bảo hiểm | SRTM/Copernicus DEM 30 m (miễn phí); bản đồ ngập lụt của tỉnh (rời rạc) | **3** — loại được ô rõ ràng không xây được; nhưng `buildable_h3` đã bắt phần lớn qua WorldCover water/wetland | **4** — DEM miễn phí, xử lý giống hệt WorldCover đã làm | `frac_water`/`frac_wetland` hiện có | ⚪ thấp — Copernicus/NASA open |
| **11** | **Quy hoạch sử dụng đất chính thức** | quy hoạch phân khu, đất được phép kinh doanh dịch vụ | `known-issues` P5 tự khai limitation: *"quy hoạch sử dụng đất chính thức VN không public → WorldCover/OSM chỉ là proxy"* | Cổng quy hoạch tỉnh (ảnh scan); guland.vn/meey (thương mại, phái sinh) | **3** — chuyển "buildable" từ proxy sang thật | **1** — ảnh scan không georeference, mỗi tỉnh một định dạng; bên thứ ba thì license bẩn | `buildable_h3` (WorldCover + OSM) hiện tại + cờ `Cần review thêm` | 🔴 guland/meey: dữ liệu phái sinh, license không rõ |
| **12** | **Luồng khách du lịch** | lượt khách/tháng theo tỉnh, mùa vụ | Đóng P3 (*cửa sổ 30 ngày bỏ qua mùa vụ*). Quan trọng cho tuyến du lịch (Hạ Long, Đà Lạt, Phú Quốc) | GSO/Cục Du lịch (công bố tháng, cấp tỉnh) | **2** — cấp tỉnh quá thô cho quyết định cấp site; chỉ hữu ích ở lớp mùa vụ | **4** — công bố công khai, parse dễ | không có | ⚪ thấp |

---

### C.2 · Kế hoạch lấy dữ liệu — cho các dòng ROI ≥ 4 **và** khả thi ≥ 3

#### ① Ma trận thời gian lái OSRM (ROI 5 / khả thi 5) — **làm trước tiên**

1. `docker run -v $PWD/data/raw/osm:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/vietnam-latest.osm.pbf` → `osrm-partition` → `osrm-customize` → `osrm-routed --algorithm mld`. Dùng **đúng file PBF đã đóng băng trong MANIFEST** (seq 4852) ⇒ ma trận content-addressed theo snapshot.
2. Endpoint: `GET /table/v1/driving/{lng,lat;…}?sources=…&destinations=…&annotations=duration`. Giới hạn thực tế ~100×100 mỗi request ⇒ chia lô.
3. Khối lượng: **không** dựng ma trận đầy đủ 314.904 × 19.805. Chỉ dựng cho cặp trong bán kính haversine 3R = 9 km (`de-bai-v2` §6.1 nền `S₀`). Ước lượng từ số đo hiện có (p50 7 trạm DC trong 9 km): **~10⁷ cặp** ⇒ ~1.000 request bảng 100×100 ⇒ **1–2 h** trên máy đơn.
4. Ra: `data/interim/osrm/drive_time_h3_station.parquet` (`h3_r8`, `station_id`, `duration_s`, `distance_m`). Đóng băng vào MANIFEST như artefact dẫn xuất.
5. Kiểm chứng bắt buộc: so `duration_s` với haversine ở HN/HCM, báo **phân vị tỷ lệ vòng vèo**; kỳ vọng đuôi nặng ở các cặp qua sông — nếu **không** thấy đuôi thì OSRM cấu hình sai.

#### ② COD từ diff registry + telemetry (ROI 5 / khả thi 4)

1. **Ngay hôm nay:** snapshot `vinfastauto.com` locator (`fetch_locators.py` đã có, ghi `generation`/`count`) và **lưu bản mới cạnh gen 16**, đừng ghi đè. Mỗi bản ~226 MB → 1 bản/tuần là đủ.
2. Viết `official_diff.py`: so hai generation theo `store_id` → `{new, removed, status_changed}`. Kiểm giả thuyết §7.2 của `de-bai-v2`: đếm tỷ lệ `UNAVAILABLE → ACTIVE`. **Nếu ≈ 0 thì cách đọc sai và cả §7.2 lẫn nhánh này bị huỷ** — kiểm cái này *trước* khi xây gì thêm.
3. Song song: suy `first_telemetry_ts` từ `evcs_timeseries_720h/` (19.426 file, có sẵn) → cận trên của COD cho trạm mở sau 2026-06-29. Rẻ, chạy trong phút.
4. Ra: `data/interim/vinfast_official/station_cod.parquet` (`station_code`, `cod_lower`, `cod_upper`, `cod_source ∈ {registry_diff, first_telemetry, unknown}`). **Không bao giờ điền COD đoán** — để `unknown` (bài học E-DQ1).
5. Thời gian: bước 1+3 **nửa ngày**; bước 2 cần **≥ 2 snapshot cách nhau ≥ 1 tuần** ⇒ tín hiệu thật có từ ~05/08. Càng hoãn pull đầu tiên càng lùi ngày đó.

#### ③ Đăng ký xe điện theo tỉnh (ROI 5 / khả thi 3)

1. Nguồn chính: Cục Đăng kiểm VN — số liệu phương tiện đăng ký mới theo quý, có tách nhiên liệu. Phụ: công bố bán hàng VinFast, báo cáo VAMA hằng tháng.
2. Không có API ⇒ tải PDF/HTML về `data/raw/registration/`, parse tay sang `data/interim/ev_registration_province.parquet` (`admin_l1_code`, `quarter`, `n_ev_car`, `n_ev_car_vinfast`, `source_url`, `retrieved_at`).
3. Khối lượng nhỏ: 34 tỉnh × ~8 quý = **~270 dòng**. Công sức nằm ở đối chiếu **34 tỉnh sau sáp nhập 2025** với công bố còn theo 63 tỉnh — đây là công việc thật, không phải parse. Dùng đúng bảng ánh xạ mà `admin_join` đã phải xử lý.
4. Ra: `d_j` được nhân trọng số theo tỷ lệ EV/tỉnh thay vì dân số thô ⇒ đóng **P11**; và mẫu số K1/K2 của §7.5 thành số thật.
5. Thời gian: **1 ngày** (chủ yếu là đối chiếu địa giới). Độ trễ dữ liệu 1 quý — chấp nhận được vì đây là biến chậm.

#### ④ CapEx theo cấu hình (ROI 4 / khả thi 4)

1. Nguồn: bảng giá công khai vcharge.vn theo dòng trụ (AC 7/11/22 kW, DC 30/60/120 kW); đơn giá đấu nối của EVN theo cấp áp; catalog nhà sản xuất cho khoảng giá.
2. Ghi tay vào `config/capex.yaml` — **mỗi dòng là một KHOẢNG `[low, high]`, không phải một điểm** (nghĩa vụ sensitivity §8.3).
3. Khối lượng: ~20 dòng. **Nửa ngày**, phần lớn là đọc và ghi nguồn.
4. Ra: `cost_i(u_i)` có đơn vị tiền ⇒ `ΔΠ` chạy được thật; `capex_class` hiện tại giáng xuống thành *fallback khi không khớp cấu hình*.
5. Cổng bắt buộc: chạy `ΔΠ` ở cả hai đầu khoảng. **Nếu thứ hạng đảo trong khoảng ⇒ khuyến nghị đó không được phát** (§8.2).

*(Dòng #4 — giá thuê mặt bằng — ROI 5 nhưng khả thi 2, nên **không** có kế hoạch lấy ở đây. Thay bằng bảng giá đất Nhà nước theo QĐ tỉnh: public, đúng luật, dùng làm **hạng** chứ không dùng làm **mức**. Nếu cần giá thị trường thì phải mua license, không scrape.)*

---

### C.3 · Ba việc nên làm tuần này

1. **Dựng OSRM và thay Euclid.** ROI cao nhất, khả thi cao nhất, chi phí 0đ, dữ liệu đã đóng băng sẵn trong repo. Đây là thứ `de-bai-v2` tự gọi là *"giới hạn nghiêm trọng nhất"* mà lại **gỡ được trong một ngày**.
2. **Pull snapshot registry VinFast đầu tiên sau gen 16, và kiểm giả thuyết `UNAVAILABLE → ACTIVE`.** Đây là việc **nhạy cảm thời gian**: COD chỉ dựng được từ diff giữa hai lần pull, nên mỗi ngày hoãn là một ngày lùi mốc có tín hiệu. Đồng thời chính phép kiểm này quyết định §7.2 của `de-bai-v2` sống hay chết — làm sớm để khỏi xây trên giả định hở.
3. **Đóng ba lỗi CHẶN của Phần B ([L4] ranh giới, [L1] dedup, [L6]+[L10] tái lập).** Không phải "dữ liệu mới" nhưng phải xong trước — mọi lớp dữ liệu ở §C.1 đều đổ vào cùng tập trạm đó; đếm sai cung thì OSRM và COD cũng chỉ làm sai chính xác hơn.

### C.4 · Những gì KHÔNG nên lấy dù có sẵn — và vì sao

| Không lấy | Vì sao |
|---|---|
| **Scrape batdongsan.com.vn / chotot.com** lấy giá thuê | ToS cấm rõ ràng. Dự án **đang có** F1 chưa đóng (HF dataset public, license Unknown) — thêm một nguồn vi phạm ToS nữa vào lúc này là tự chặn đường phát hành. Dùng bảng giá đất Nhà nước. |
| **PlugShare / ChargeMap** làm nguồn đối thủ | Crowdsourced, ToS cấm scraping, và **phủ VN quá thưa** để mang thông tin. Dùng OSM `amenity=charging_station` từ PBF đã có. |
| **Nhập `commune_name`/`province_name` (OSM) thẳng vào `canonical/stations`** | `admin_join.py` đã lập luận đúng và **phải giữ nguyên**: OSM là ODbL, nhập vào biến **cả bảng** thành tác phẩm phái sinh ODbL và siết điều kiện phát hành. Giữ ở bảng phụ, join theo `station_id`. |
| **`gold_station_id` / `gold_dist_m`** (còn trong header `evcs_other.csv`/`evcs_bss.csv`) | Đã bị F10 gắn nhãn "cột bẫy" (NN không ngưỡng, p99 6,6 km). `merge_catalog` đang loại đúng qua `extrasaction="ignore"`. **Đừng bao giờ tái sinh.** |
| **WorldPop 2025 làm bản thay thế duy nhất cho 2020** | Nó **cũng là mô hình**, và thấp bất thường ở Tây Nam Bộ (An Giang+Kiên Giang 3,11M vs 4,17M). P10 đã quyết đúng: giữ cả hai, **đo** độ nhạy. Đừng đổi quyết định đó thành "2025 là bản đúng". |
| **Quy hoạch từ guland.vn / meey** | Dữ liệu phái sinh từ nguồn Nhà nước, license không rõ, không kiểm chứng được. Với một quyết định **không đảo ngược** như siting, nguồn không truy được là nợ, không phải tài sản. |
| **Bất kỳ nguồn nào không có `retrieved_at` + `sha256`** | E-DQ10 đã dựng đúng kỷ luật này. Thêm một nguồn ngoài manifest là thêm một [L4] nữa. |

---

*Người review: data lead · 2026-07-29 · mọi số trong file này đo lại trực tiếp trên `data/` của commit hiện tại (`8f44dd1` + working tree), không chép từ doc.*
