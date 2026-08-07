# KNOWN ISSUES & LIMITATIONS REGISTER

*Danh sách vấn đề của bài toán tối ưu vị trí trạm sạc VGreen. Đây là **nguồn chân lý để monitor & xử lý** — mỗi vấn đề có: mức độ, phạm vi xử lý trong internship, chủ sở hữu, ngày xử lý, hướng khắc phục, trạng thái. Cập nhật cột **Trạng thái** + **processed_date** khi tiến triển.*

## 1. Chú giải

- **Nhóm:**
  - `A` Demand Target & Data Science
  - `B` Spatial Geometry & Siting Mechanics
  - `C` Master Data & Entity Resolution
  - `D` Covariates & Feature Engineering
  - `E` Data Quality & Cleaning (di chuyển khỏi `data-layer/overview.md §7` ngày 24/07 để không theo dõi trùng ở 2 nơi)
  - `F` Pipeline Integrity & Handoff (từ review 2026-07-28 — bằng chứng đầy đủ ở [sprint-reviews/data-pipeline-review-2026-07-28.md](sprint-reviews/data-pipeline-review-2026-07-28.md))
  - `G` Data-lead review 2026-07-29 (mục `L*` — bằng chứng đầy đủ ở [review/2026-07-29-data-lead-review.md](review/2026-07-29-data-lead-review.md))
- **Mức độ:** 🔴 Fatal · 🟠 High · 🟡 Medium · ⚪ Low
- **Phạm vi (trong 3 sprint):**
  - `FIX` bắt buộc sửa
  - `SIMPLIFY` sửa bản rút gọn cho MVP
  - `DOC` không sửa được trong scope → **phải ghi rõ là limitation**
  - `ROADMAP` đã có trong kế hoạch
  - `FUTURE` ngoài quy trình hiện tại
- **Trạng thái:**
  - ☐ Open
  - ◐ In-progress/Partial
  - ☑ Done
  - ⊘ Won't-fix (chấp nhận & document)
- **Ngày giải quyết:** ngày chốt/đóng vấn đề (ISO `YYYY-MM-DD`); `—` nếu chưa xử lý.

---

## 2. Bảng tổng hợp vấn đề (đã gộp)

> **ID có link** → mở file giải pháp trong [`issues/`](issues/README.md). `P2`/`P3` không có file riêng
> (⊘ won't-fix, hạn chế ghi trọn trong dòng register).
> Nhóm `F`/`G` (port từ nhánh Kỳ 30/07) **không** có file trong `issues/` — chi tiết + bằng chứng nằm ở
> [sprint-reviews/data-pipeline-review-2026-07-28.md](sprint-reviews/data-pipeline-review-2026-07-28.md) (F) và
> [review/2026-07-29-data-lead-review.md](review/2026-07-29-data-lead-review.md) (G).

| ID               | Nhóm | Vấn đề                                                                                                                                                                                                                                                                                                                                                                                    | Mức | Phạm vi              | Owner           | ngày giải quyết   | Trạng thái |
| ---------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | --------------------- | --------------- | -------------------- | ------------ |
| **[P1](issues/a-demand-target/p1-heuristic-weights.md)**     | A     | Heuristic weights thay vì fit model có giám sát trên 18,6M occupancy                                                                                                                                                                                                                                                                                                                    | 🟠   | SIMPLIFY              | Kỳ             | —                   | ☐           |
| **P2**     | A     | Selection bias: chỉ quan sát demand nơi**đã có** trạm                                                                                                                                                                                                                                                                                                                           | ⚪   | DOC → FUTURE         | Giang/Kỳ       | —                   | ⊘           |
| **P3**     | A     | Cửa sổ 7,15 ngày → bỏ qua mùa vụ/lễ/thời tiết                                                                                                                                                                                                                                                                                                                                      | ⚪   | DOC → FUTURE         | Giang           | —                   | ⊘           |
| **[P4](issues/b-spatial-geometry/p4-service-radius.md)**     | B     | **1. Bán kính suy biến:** R = 500 m < khoảng cách tâm 2 ô H3 kề nhau (0,98 km) → MCLP = sort top-p; <br /><br />2. 500 m không phải khoảng cách lái xe                                                                                                                                                                                                                 | 🔴   | **FIX (chặn)** | Kỳ + Giang     | **2026-07-24** | ☑           |
| **[P5](issues/b-spatial-geometry/p5-candidate-set.md)**     | B     | Candidate set chưa định nghĩa; thiếu lọc land-use (hồ/núi/đất cấm)                                                                                                                                                                                                                                                                                                                | 🟡   | SIMPLIFY              | Giang           | **2026-07-24** | ☑           |
| **[P6](issues/c-master-data/p6-duplicate-pk.md)**     | C     | Trùng PK (236 dòng); số trạm lệch giữa doc/report (28.417 vs 28.625)                                                                                                                                                                                                                                                                                                                   | 🟡   | FIX                   | Giang           | **2026-07-24** | ☑           |
| **[P7](issues/c-master-data/p7-vehicle-class.md)**     | C     | Trộn lẫn trạm sạc xe máy điện: dùng power tier chung thay vì chuẩn cắm (CCS2)                                                                                                                                                                                                                                                                                                    | 🟠   | FIX                   | Giang           | **2026-07-24** | ☑           |
| **[P8](issues/c-master-data/p8-status-access.md)**     | C     | Thiếu lọc trạng thái vận hành (inactivate / activate) & access (private vs public)                                                                                                                                                                                                                                                                                                     | 🟡   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **[P9](issues/c-master-data/p9-snapshot-skew.md)**     | C     | Lệch thời điểm giữa các đợt crawl (occupancy 2026 · WorldPop 2020 · OSM)                                                                                                                                                                                                                                                                                                           | 🟡   | FIX + DOC             | Giang           | —                   | ☐           |
| **[P10](issues/d-covariates/p10-worldpop-vintage.md)**    | D     | WorldPop 2020 lỗi thời (6 năm) — **mở lại 29/07 (nhánh Kỳ):** không chỉ cũ, mặt nạ BSGM gán 0 người cho **60,3%** ô có đường. Đóng bằng `E-DQ7e`/`E-DQ7f` (UNadj + `pop_adj`) + cột sensitivity `pop_2025` (R2024B) — *xem §2.1*                                                                                                                                                                                                                                                                                                                                                            | 🟠   | FIX + DOC                   | Giang           | **2026-07-29**                   | ☑           |
| **[P11](issues/d-covariates/p11-car-ownership.md)**    | D     | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ)                                                                                                                                                                                                                                                                                                                | 🟠   | SIMPLIFY              | Giang           | —                   | ☐           |
| **[E-DQ10](issues/e-data-quality/e-dq10-freeze-snapshot.md)** | E     | Chưa freeze snapshot / provenance                                                                                                                                                                                                                                                                                                                                                           | 🟡   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **[E-DQ9](issues/e-data-quality/e-dq9-aoi-clip.md)**  | E     | Grid toàn quốc vs MVP 1 thành phố (`demand_h3` toàn bảng)                                                                                                                                                                                                                                                                                                                            | 🟡   | SIMPLIFY              | Giang           | **2026-07-27** | ☑           |
| **[E-DQ2](issues/e-data-quality/e-dq2-crosssource-dedup.md)**  | E     | Trùng chéo nguồn (evcs vs official)                                                                                                                                                                                                                                                                                                                                                       | 🟠   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **[E-DQ1](issues/e-data-quality/e-dq1-coord-placeholder.md)**  | E     | Toạ độ placeholder trùng khít                                                                                                                                                                                                                                                                                                                                                          | 🟠   | FIX                   | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7a](issues/e-data-quality/e-dq7a-poi-outside-vn.md)** | E     | **POI ngoài lãnh thổ VN** — Overpass query bằng `VN_BBOX` thô, không clip biên giới → **54,2%** POI nằm ở Campuchia/Lào/Thái/TQ *(≡ `E-DQ11` nhánh Kỳ — hai lần fix độc lập, xem §2.1; 30/07 port thêm chính sách fail-closed: `osm_poi_points` chỉ chứa `in_vn=True`, phần ngoài tách `osm_poi_outside_vn.parquet`)*                                                                                                                                                                                                                                  | 🔴   | **FIX (chặn)** | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7b](issues/e-data-quality/e-dq7b-road-semantics.md)** | E     | **`road_len` sai ngữ nghĩa** <br />1.`track`+`service` tính là đường sinh cầu (19,9%)<br /><br />2. double-count 2 chiều (motorway 96,9% `oneway`)<br />3. `_MAJOR` gộp cao tốc + quốc lộ + tỉnh lộ                                                                                                                                                           | 🟠   | FIX                   | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7c](issues/e-data-quality/e-dq7c-poi-taxonomy.md)** | E     | **POI thiếu & lẫn đơn vị**1. Tỉ lệ`apartments` với `mall`bị gắn mặc đinh là 1:1 (**84,8%** số đếm ở top-100 ô là chung cư);<br /><br />2. Lẫn đơn vị **bên trong** từng nhóm crawl<br /><br />3. **335** trùng node/way + 13 đối tượng ở 2 nhóm<br /><br />4. recall OSM **fuel 35,9% · parking 8,6%** (đo ngoại vi) | 🟠   | FIX + DOC             | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7e](issues/e-data-quality/e-dq7e-pop-calibration.md)** | E     | **`pop` chưa hiệu chuẩn TUYỆT ĐỐI**:  raster UN-**unadjusted**: 99,627M so với bản UNadj **97,569M** (**+2,11%**).                                                                                                                                                                                                                                       | 🟡   | FIX + DOC             | Giang           | **2026-07-29** | ☑           |
| **[E-DQ7f](issues/e-data-quality/e-dq7f-pop-dasymetric.md)** | E     | `pop` bị dồn lại trong 1 vài ô dân cư  + DỒN THỪA xét trên cấp xã                                                                                                                                                                                                                                                                                                           | 🟠   | FIX                   | Giang           | **2026-07-29** | ☑           |
| **[E-DQ7g](issues/e-data-quality/e-dq7g-overture-crosscheck.md)** | E     | **Tầng POI thiếu lớp + chưa có nguồn thứ hai.** 1. Lớp `PARK` **chưa từng tồn tại** — `overpass_poi.CATEGORIES` không có nhóm nào sinh ra công viên, nên "thiếu công viên" là *bug định nghĩa*, không phải OSM thưa (đã crawl `leisure=park` → **4.146** POI trong VN; **không** nối vào `DERIVED_COLUMNS`, để E-DQ7d quyết định).<br /><br />2. Đối chiếu Overture Places (release 2026-07-22.0, **2,19M** place trong bbox → **43.446** trong VN, **0,0%** đến từ OSM ⇒ độc lập thật): chồng lấn @50 m chỉ **16,7%** ở `FUEL`, nới tới 200 m cũng chỉ lên 23,0% ⇒ **hai tập địa điểm khác nhau**, không phải lệch toạ độ.<br /><br />3. Chênh lệch số lượng **≠ độ phủ**: `MALL` Overture đông 22,85× nhưng chỉ **8,4%** tên mang danh từ của lớp ⇒ nhiễu taxonomy; `PARKING_OFF` lẫn **10,7%** garage sửa xe. Chỉ `FUEL` sạch nhãn (**93,6%**).<br /><br />4. Hợp nhất 2 nguồn kéo recall fuel **35,9% → 43,7%** (`PARKING_OFF` chỉ +1,3 điểm — không cứu được).<br /><br />5. Overture **không có** ngày sửa mức đối tượng ở VN (`update_time` là ngày giao lô, **1** giá trị phân biệt cho 99% điểm); OSM có, và **42,9%** cây xăng quá 5 năm chưa ai sửa | 🟠   | FIX + DOC             | Giang           | **2026-08-07** | ☑           |
| **E-DQ12** | E     | Lưới `pop` không thấy được **vùng tập trung dân cư** + ô WorldPop mâu thuẫn WorldCover (nước/rừng >80% nhưng hàng nghìn người) — bảng phụ **settlement** DEGURBA: `settlement_class`/`cluster_*`/`centre_*`/`pop_k1`/`pop_unsupported` (port nhánh Kỳ, chạy trên `pop` thô + `pop_2025` cả hai niên đại; phần "đỉnh dồn cục" trùng vai `E-DQ7f` — xem §2.1). Test: `tests/test_settlement.py`                                                                                                                                                                                                                                                                                                                             | 🟠   | FIX                   | Giang           | **2026-07-29** | ☑           |
| **[E-DQ8a](issues/e-data-quality/e-dq8a-access-tier.md)** | E     | Chỉ xét đường đi trong 1 ô thay vì trong 1 nhóm các ô                                                                                                                                                                                                                                                                                                                             | 🟡   | FIX                   | Giang           | **2026-07-30** | ☑           |
| **[E-DQ8b](issues/e-data-quality/e-dq8b-roadless-reallocation.md)** | E     | Dân cư bị phân bố lại ở những ô không phải dân cư (E-DQ7f) -> ko có lối vào                                                                                                                                                                                                                                                                                               | 🟠   | FIX                   | Giang           | **2026-07-30** | ☑           |
| **[E-DQ8c](issues/e-data-quality/e-dq8c-servable-denominator.md)** | E     | **Dân KHÔNG phục vụ được — mẫu số, không phải làm sạch**: 225 ô / 42.576 người không dời được (xóm kênh rạch ĐBSCL đi thuyền) + lưới **chưa phải tessellation** (76 ô chứa 83 trạm vận hành không có dòng ở bảng lưới nào) | ⚪   | DOC → policy          | Giang/Kỳ       | —                   | ☐           |
| **[E-DQ7d](issues/e-data-quality/e-dq7d-demand-proxy-validation.md)** | E     | **Proxy cầu chưa kiểm chứng ngoại vi**                                                                                                                                                                                                                                                                                                                                            | 🔴   | **FIX (chặn)** | **Kỳ**  | —                   | ☐           |
| **[E-DQ4](issues/e-data-quality/e-dq4-asset-vs-live-config.md)**  | E     | Cấu hình súng thu thập được bị diễn giải sai - Xét số súng livePower (đang hoạt động) thay cho vì Asset (tổng số súng).                                                                                                                                                                                                                                               | 🟠   | FIX                   | Giang           | **2026-07-30** | ☑           |
| **[E-DQ5](issues/e-data-quality/e-dq5-operator-ownership.md)**  | E     | ~~Trường `operator` bẩn~~ → **tiền đề bị bác**: `operator` là **HẰNG SỐ** trên tập cung (0 null, **1** giá trị phân biệt) ⇒ **không có gì để làm sạch**. Tín hiệu chủ sở hữu/mặt bằng nằm ở `name` chưa parse (**76,8%** cung mang token `Tư nhân`/`NQ`) — **Giang chốt 30/07: không cần sửa trong scope**, giữ lại làm ghi chú vì nó là *feature* tiềm năng, không phải lỗi. **33** dòng lỗi phạm trù (payment → network) theo cùng `E-DQ6` nếu mở lại | ⚪   | DOC → FUTURE          | Giang           | **2026-07-30** | ⊘           |
| **[E-DQ6](issues/e-data-quality/e-dq6-freetext-cleanup.md)**  | E     | Text tự do bẩn (`name`, `address`)                                                                                                                                                                                                                                                                                                                                                     | ⚪   | SIMPLIFY              | Giang           | —                   | ☐           |
| **[E-DQ3](issues/e-data-quality/e-dq3-admin-enrichment.md)**  | E     | Cột admin trống (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`) **+ trọng tài `COORD_ADDR_MISMATCH` của E-DQ1** (nguồn: ranh giới xã VNSDI 2025-06-16)                                                                                                                                                                                                                                                                                                 | 🟡   | FIX                   | Giang           | **2026-07-30**      | ☑           |
| **[F1](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | HF dataset public (license Unknown, push lại 28/07) — rủi ro pháp lý ToS/vault. **Quyết định 31/07 (data lead, sau grill):** GIỮ PUBLIC nguyên raw — khuyến nghị private của review bị bác, rủi ro ToS chấp nhận có chủ đích; mirror chưa đồng bộ thế hệ 2026-07-30. | 🟠 | **RISK-ACCEPTED** | Kỳ | **2026-07-31** | ⊘ |
| **[F2](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | `split_timeseries` ghi đè khi resume → mất telemetry vĩnh viễn. Fix: raw run bất biến `timeseries_runs/load_ts_<run-id>.csv` + merge-union vào `evcs_timeseries/<code>.csv` *(port nguyên bản vào pipeline hợp nhất 30/07)* | 🔴 | FIX | Giang | **2026-07-28** | ☑ |
| **[F3](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Race listener Socket.IO → time-series gán nhầm trạm; fix: cô lập socket theo trạm + `.failed` | 🔴 | FIX | Giang | **2026-07-28** | ☑ |
| **[F4](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Bộ lọc dirty-coord chết (2 cờ không producer nào sinh); `DUP_COORD_SUSPECT` không ai tiêu thụ; T0 bypass buildable *(pipeline hợp nhất lọc bằng cổng `coord_resolved` của E-DQ1 — xem §2.1)* | 🔴 | FIX | Giang | **2026-07-28** | ☑ |
| **[F5](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | `covered0` bỏ qua P8/E-DQ2 (`status`/`is_public` thô, thiếu `is_primary`) → baseline lệch hệ quy chiếu với T0 | 🟠 | FIX | Giang | **2026-07-28** | ☑ |
| **[F6](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Telemetry mất im lặng: timeout→null→`.done` không retry; enrich lỗi→`seen` vĩnh viễn | 🟠 | FIX | Giang | **2026-07-28** | ☑ |
| **[F7](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | `match_official`: NaN distance→`verified=True`; matcher không được wire vào pipeline *(port 30/07: cổng xref sha256 byte-for-byte với master + unique + phủ đủ `station_code`, fail-fast, recovery `--allow-missing-xref`)* | 🟠 | FIX | Giang | **2026-07-28** | ☑ |
| **[F8](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Enumerate resume mất force-seed → under-coverage cụm dày đặc | 🟠 | FIX | Giang | **2026-07-28** | ☑ |
| **[F9](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Overpass trả 200 + kết quả cụt (`remark`) không kiểm → POI thiếu ở ô dày | 🟠 | FIX | Giang | **2026-07-28** | ☑ |
| **[F10](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Bàn giao 21/07 = snapshot mồ côi (hash ≠ MANIFEST, cùng nhãn 07-20) → re-handoff bundle v4 28/07 | 🟠 | FIX | Kỳ+Giang | **2026-07-28** | ☑ |
| **[F11](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | `evcs_new_supply` (phía Kỳ) không dedup nội tập + chứa OOS/Maintaining → nhiễm ground truth T1 (B4) | 🔴 | **FIX (chặn B4)** | Kỳ | **2026-07-28** | ☑ |
| **[F12](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Không atomic/fail-fast: `run_pipeline.sh` chạy tiếp khi crawl fail; ckpt ghi thẳng; `transform_canonical` rmtree *(port 30/07: `_write_partitioned_atomically` — swap cả generation, có rollback)* | 🟡 | FIX | Giang | **2026-07-28** | ☑ |
| **[F13](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Tàn dư ngưỡng 25kW + cột đánh lừa `num_ports`=totalCharging *(điều chỉnh hợp nhất 30/07 — xem §2.1: rename `n_charging_snapshot` GIỮ; fallback tier 25 kW GIỮ LẠI theo Q5)* | 🟡 | FIX | Giang | **2026-07-28** | ☑ |
| **[F14](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | `penalty` chuẩn hoá per-AOI trên file dùng chung; hard-exclude quá tay *(điều chỉnh hợp nhất 30/07 — xem §2.1: port `SUBSTATION_PENALTY_SCALE_M`=50 km + gate `MAX_POP_NO_ROAD_FRAC`=0,20; NOT_BUILT_UP vẫn loại cứng theo E-DQ8a)* | 🟡 | SIMPLIFY | Giang | **2026-07-28** | ☑ |
| **[F15](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Docs/config trôi: schema-contract thiếu 6 cột E-DQ2 + QA ảo; `params.yaml` mồ côi; cột chết trong candidate *(điều chỉnh hợp nhất 30/07 — xem §2.1: `province_code`/`exclusion_flags` GIỮ theo Q8)* | 🟡 | FIX | Giang | **2026-07-28** | ☑ |
| **[F16](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Test né logic rủi ro: không test `_load_stations`/`_gapfill`/`_qa_gate`/covered0 | 🟡 | FIX | Giang | **2026-07-28** | ☑ |
| **[F17](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | `_tos_firewall` (phía Kỳ) chỉ bọc bảng `stations`, các bảng dist khác không qua firewall | 🟡 | FIX | Kỳ | **2026-07-28** | ☑ |
| **[F18](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Gộp Low: `fetch_locators` không so `meta.count`; PBF/TIF thiếu check `got<total`; manifest hỏng→WARN | ⚪ | FIX | Giang | **2026-07-28** | ☑ |
| **[F19](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Occupancy sampling theo sự kiện không đều (median 0,9′ · max gap 71h) → calibrate P1/A2 bắt buộc duration-weight | 🟡 | FIX + DOC | Kỳ | **2026-07-28** | ☑ |
| **[F20](sprint-reviews/data-pipeline-review-2026-07-28.md)** | F | Code sinh snapshot HF 28/07 mới hơn git HEAD (E-DQ1 làm ngoài repo) — họ lỗi "artefact không tái lập từ repo" | 🟠 | FIX | Giang | **2026-07-28** | ☑ |
| **[L1](review/2026-07-29-data-lead-review.md)** | G | Guard dedup `_distinct_store` là phép lặp thừa của khoá chính → tầng T2 chết (97 cặp tên trùng khít đếm cung 2 lần) | 🔴 | FIX | Kỳ | **2026-07-29** | ☑ |
| **[L4](review/2026-07-29-data-lead-review.md)** | G | Lớp ranh giới VN nằm ngoài repo & ngoài MANIFEST *(hợp nhất 30/07: đóng bằng xây dựng — ranh giới lấy từ `.pbf` đã freeze, xem §2.1)* | 🔴 | FIX | Kỳ | **2026-07-29** | ☑ |
| **[L6](review/2026-07-29-data-lead-review.md)** | G | Canonical sửa bằng swap thư mục thủ công → `make canonical` không ra bản đã giao (F20 tái diễn) *(hợp nhất 30/07: E-DQ1 chạy trong `transform_canonical` + ghi nguyên tử F12 — xem §2.1)* | 🔴 | FIX | Kỳ | **2026-07-29** | ☑ |
| **[L10](review/2026-07-29-data-lead-review.md)** | G | 298 trạm trong snapshot sinh bởi code không có trong repo → `evcs_enumerate --seed-from-official` + sidecar seed | 🔴 | FIX | Kỳ | **2026-07-29** | ☑ |

> ✅ **Tái kiểm 2026-07-31 trên `data/giang`.** Con số nhóm `F`/`G` gốc đo trên nhánh Kỳ (28–29/07); sau hợp
> code 30/07 và **rebuild toàn chuỗi từ raw ngày 31/07** (`snapshot_id = 2026-07-20`, `verify-snapshot` PASS,
> mọi QA-gate report PASS) + **pytest 169 passed / 1 skipped** — dấu ☑ nhóm `F`/`G` trích dẫn được.
> *(31/07 bổ sung: `F5` siết gate toạ độ `covered0` — baseline ⊆ tập cung; tầng LIVE gỡ khỏi `stations` →
> `tests/test_connector_rollup.py`. Nghiệm thu `data/processed/` →
> [processed-data-checklist.md](data-layer/processed-data-checklist.md).)* Bằng chứng theo dòng:
> `F2`/`F3`/`F6` → `tests/test_timeseries_integrity.py`; `F7`/`F8`/`F12` (+ `L1` guard dedup, `L6` swap
> nguyên tử, E-DQ1) → `tests/test_f7_f12_integrity.py`; `F9`/`F13`/`F16` → `tests/test_f8_f9_f13_f14_f16.py`;
> `F5` → `tests/test_covered0.py`; `F18` → guard `meta.count` fail-fast trong `vinfast_official/fetch_locators.py`;
> `F10`/`F20` → chính lần rebuild (artefact tái lập từ HEAD, hash khớp MANIFEST); `F15`/`F19` → fix docs/schema
> đã nằm trong cây hợp nhất; `L4` → `tests/test_vn_boundary.py`; `L10` → `tests/test_seed_discovery.py`.
> **Ngoại lệ — dấu ☑ KHÔNG đến từ test gốc phía Kỳ, ghi trung thực:**
>
> - **F4:** đóng theo **phương án Giang (B3)** — module `coord_quality` phía Kỳ không port; test gốc thay bằng
>   `tests/test_covered0.py::test_t0_gates_on_coord_resolved` + 2 test E-DQ1 trong `tests/test_f7_f12_integrity.py`.
> - **F14:** đóng theo **phương án Giang (B3)** — `penalty_flags` phía Kỳ không port; test gốc thay bằng
>   `tests/test_access_tiers.py` (chính sách ISOLATED, E-DQ8a); phần port (`SUBSTATION_PENALTY_SCALE_M`,
>   gate `MAX_POP_NO_ROAD_FRAC`) nằm trong `build_buildable_h3.py`, PASS trong `make landuse` 30/07 —
>   **không có test riêng mang tên F14**.
> - **F11**/**F17:** fix nằm **trong repo Kỳ** (`evcs_new_supply`/`_tos_firewall` không tồn tại trên
>   `integrate/final`) — dấu ☑ giữ theo biên bản 28/07 phía Kỳ, **không tái kiểm được từ repo này**.
>
> **12 mục `L` còn mở** (L2/L3/L5/L7–L9/L11–L16) theo dõi tại
> [review/2026-07-29-data-lead-review.md](review/2026-07-29-data-lead-review.md) — chưa thăng cấp thành dòng register.
>
> **Chốt phiên hoàn thiện 31/07 (grill với data lead):**
>
> - **Token VNSDI trong lịch sử `data/giang` — HẠ MỨC, ĐÓNG.** Xác minh 31/07: `tokenChinh` là token
>   **public tự xoay** — `config.aspx` phát cho *bất kỳ* khách vãng lai, referer-bound, không bền
>   (`vnsdi/fetch_communes._fetch_token`). Không phải secret ⇒ **không cần rotate, không rewrite lịch sử**.
>   Cảnh báo "PHẢI rotate" trong hồ sơ B2/B3 là đánh giá quá tay tại thời điểm chưa đọc cơ chế token.
>   Việc còn lại chỉ là vệ sinh: Giang chuyển allowlist cá nhân sang `.claude/settings.local.json`.
> - **`export_handoff.py` không có test riêng — quyết định có chủ đích của data lead 31/07** (không phải
>   nợ treo). Bằng chứng vận hành: bundle `evcs_vn_2026-07-30` đóng thành công qua gate F10 + FX-05 thật
>   (kể cả nhánh FAIL của F10 đã kích hoạt đúng khi manifest lệch).
> - **Bản tách timeseries 720h:** đo 31/07 — 19.426 file, **38.255.343 dòng, khớp nguồn từng dòng**;
>   giữ nguyên, không crawl lại.
> - **`pop_2025` khác footprint thế hệ:** bổ sung `worldpop_pop_2020_r24_h3` (cặp cùng thế hệ R2024B) để
>   so per-cell hợp lệ — xem [schema-contract](schema/schema-contract.md) mục `pop_2025`.
> - **WARN `poi_recall_bias_parking_off` 2,44 — chấp nhận có chủ đích** (T4 gap-fill 920 ô đang bù,
>   coverage 91,05% PASS) — xem [candidate-sites](data-layer/candidate-sites.md).

### 2.1 Ghi chú hợp nhất nhánh (2026-07-30) — một sự thật mỗi lớp

Ba lớp dữ liệu được **cả hai nhánh sửa độc lập** với hai lời giải khác nhau. Register chỉ giữ MỘT sự thật
mỗi lớp; phương án thắng chốt ở phiên B3 (30/07):

1. **Lớp ranh giới VN — `E-DQ7a` (Giang) thắng; `E-DQ11` + `L4` (Kỳ) gộp vào.** Hai lần fix độc lập cùng
   một lỗi bbox-spill 54,2%: Kỳ cắt bằng đa giác 34 tỉnh (`ev_siting/vn_boundary.py`, gói `data/ref/vn_admin`
   — lưới 314.904 ô trên nhánh Kỳ); Giang trích relation `admin_level=2` (49915) **từ chính `.pbf` đã freeze**
   (`osm/vn_boundary.py`, giữ `cell_state`/`frac_in_vn` — lưới 255.480 ô trên nhánh Giang trước hợp nhất).
   *(Đo 2026-07-30 trên `demand_h3` rebuild `integrate/final`: lưới hợp nhất = **314.934 ô** — INSIDE
   311.447 / BORDER 3.487.)* Phương án Giang thắng vì lớp gác
   nằm **trong MANIFEST bằng xây dựng** (đóng luôn `L4` mà không cần gói ngoài; gói `vn_admin` vẫn là member
   frozen nhưng không còn là lớp gác) và vì `frac_in_vn` cho phép chia tỉ lệ ô biên. **Port từ Kỳ:** chính
   sách **fail-closed** POI — `osm_poi_points.parquet` chỉ chứa `in_vn=True`, phần ngoài tách
   `osm_poi_outside_vn.parquet` (hằng `POI_OUTSIDE_VN`), `build_candidates._load_poi` lọc `in_vn` trực tiếp.
2. **Lớp dân số — `E-DQ7e`/`E-DQ7f`/`E-DQ8b` (Giang) là neo; `P10`-mở-lại + `E-DQ12` (Kỳ) gộp một phần.**
   Hai lần fix độc lập cùng một lớp `pop`: Kỳ giữ 2020 mặc định + thêm `pop_2025` + 3 cờ phủ `NaN≠0`;
   Giang đổi raster **UNadj** (7e) + `pop_adj` dasymetric VNSDI (7f) + dời dân ô roadless (8b). Phương án
   Giang thắng làm **neo xếp hạng** (`pop_adj`) vì có nguồn đối chứng độc lập (VNSDI DANSO) và thứ hạng
   bất biến từng bit qua 7e. **Giữ từ Kỳ:** `pop_2025` (R2024B unadjusted) làm cột **sensitivity niên đại**
   (manifest khai đủ 3 member raster) và toàn bộ lớp **settlement** của `E-DQ12` (DEGURBA/`pop_k1`/
   `pop_unsupported` — không có bản tương đương phía Giang, chạy trên `pop` thô + `pop_2025` như đã đo).
   **Không đưa vào:** 3 cờ phủ `pop_covered`/`pop_2025_covered`/`osm_covered` — hợp đồng `demand_h3` chốt
   `fillna(0)` (Q6ii); hạn chế "0-không-phủ ≠ 0-đo-được" ghi làm limitation, sensitivity đo qua `pop_2025`.
3. **Lớp toạ độ E-DQ1 — `fix_coords` (Giang) thắng; `coord_quality`/`L6` (Kỳ) không port.** Hai lời giải
   cùng lớp: Kỳ gắn `COORD_LOW_TRUST` qua module `coord_quality` chạy ngoài `make canonical` (chính là lỗi
   L6 phải vá bằng swap thủ công); Giang chạy `fix_coords` **trong** `transform_canonical` — enum `coord_src`
   ∈ {`evcs`, `official`, `placeholder`}, cổng `coord_resolved` (placeholder → `h3_r8=NULL`, tự loại khỏi
   cung/T0). Phương án Giang thắng vì tái lập bằng một lệnh `make canonical` (+ ghi nguyên tử F12) — đúng
   yêu cầu của L6. `COORD_LOW_TRUST` **không tồn tại** trong pipeline hợp nhất; mọi consumer lọc bằng
   `coord_resolved`, không bằng danh sách cờ (F4 đóng theo cách này).

**Điều chỉnh trạng thái nhóm `F` theo B3** (phần fix bị đảo một phần bởi phương án Giang):

- **F13:** rename `num_ports` → `n_charging_snapshot` **GIỮ** (cột là snapshot số xe đang sạc, không phải cấu
  hình cung); phần "bỏ suy AC/DC theo kW" **đảo lại theo Q5** — `transform_canonical` giữ fallback tier 25 kW
  cho trạm evcs-only (không còn `UNKNOWN`), registry first-party vẫn ghi đè khi khớp; hạn chế fallback ghi ở
  [schema-contract.md](schema/schema-contract.md).
- **F14:** hai phần trực giao **port**: `SUBSTATION_PENALTY_SCALE_M = 50 km` (mẫu số vật lý cố định, không
  phụ thuộc AOI) + gate `MAX_POP_NO_ROAD_FRAC = 0,20` (FAIL nếu >20% ô `pop>0` không đường — road input thiếu
  coverage). Phần "NOT_BUILT_UP/NO_ROAD_ACCESS thành phạt mềm" **không port** — chính sách buildable theo Q7:
  `NOT_BUILT_UP` loại cứng, lối vào lọc bằng `access_tier == ISOLATED` (E-DQ8a).
- **F15:** phần schema-contract thiếu cột E-DQ2 đã vá; phần "xoá `province_code`/`exclusion_flags`" **đảo lại
  theo Q8** — schema `candidate_sites` giữ nguyên bản Giang (không có `penalty_flags` ở bảng bàn giao).

---

## 3. Thứ tự xử lý & ràng buộc phụ thuộc

Các dòng **E-DQ** trong [Bảng tổng hợp §2](#2-bảng-tổng-hợp-vấn-đề-đã-gộp) đã được **sắp theo thứ tự xử lý** (trên → dưới) — mỗi bước làm nhỏ tập lỗi cho bước sau:

> `E-DQ10` freeze inputs ✅ → `E-DQ9` clip MVP city ✅ → `E-DQ2` dedup chéo nguồn ✅ → `E-DQ1` sửa toạ độ ✅ →
> **`E-DQ7a` clip biên giới VN ✅** → **`E-DQ7b` retype road ✅** → **`E-DQ7c` retype POI ✅** →
> **`E-DQ7e` hiệu chuẩn tuyệt đối ✅** → **`E-DQ7f` sửa dồn cục dasymetric ✅** →
> **`E-DQ8a` bậc lối vào ✅** → **`E-DQ8b` dời dân ô roadless ✅** → `E-DQ8c` mẫu số không phục vụ được →
> **`E-DQ4` tầng cấu hình TÀI SẢN ✅** → `E-DQ7d` kiểm chứng ngoại vi (**gate của `demand_weight`** — chẩn đoán xong 29/07, **bàn giao Kỳ**) →
> ~~`E-DQ5`~~ (⊘ 30/07 — tiền đề bị bác, xem dòng register) + `E-DQ6` chuẩn hoá categorical →
> `E-DQ3` enrich admin ✅ (cũng trọng tài `COORD_ADDR_MISMATCH` của E-DQ1).

> ⚠️ **Đổi thứ tự 30/07 — `E-DQ4` chuyển lên TRƯỚC `E-DQ7d`** (bản cũ đặt nó sau). Lý do là **chính lập luận
> mà register đã dùng cho "E-DQ7c phải xong trước E-DQ7d"**, áp nguyên văn: audit của 7d chỉ ra hai cột nặng
> nhất mà nó chạm là **số súng/ô** (ρ = **0,773**, cao nhất trong mọi đại lượng đo được) và **`current_type`**
> (`occ_mean` AC 0,122 vs MIXED 1,831 — chênh **13×**). Fit trên artefact trước E-DQ4 là fit một cột công suất
> **đọc thiếu 9,9% trên tập cung** và một biến phân tầng **sai ở 531 trạm**. Chi phí đổi thứ tự **gần bằng 0**
> (một phép join vào artefact đã freeze), nên không có lý do trả sau.

> ⚠️ **`E-DQ4` KHÔNG đổi thứ hạng ô, nên nó không phải rào chặn của MCLP** — cùng khuôn kết luận với 7e/7f/8b:
> ρ(số súng, occ) ở cấp ô đi **0,7711 → 0,7745** (ô poll dày ≥500: **0,7937 → 0,8021**). Nói rõ để không ai
> đọc quá lời: E-DQ4 **không cứu** proxy cầu (verdict 0,33/0,865 của 7d **đứng nguyên**). Nó sửa đúng hai thứ
> 7d cần mà trước đây không có: **biến phân tầng** đúng, và **mẫu số exposure** để nói được "cầu trên mỗi súng"
> — thứ mà chẩn đoán B của 7d ("target thô 77% là công suất") biến thành điều kiện tiên quyết.

**Ba ràng buộc thứ tự trong nhóm `E-DQ7`** (lý do tách 6 dòng `E-DQ7a`–`E-DQ7f` thay vì 1):

- ~~**`E-DQ7b` phải xong trước `E-DQ8`.**~~ **Ràng buộc này đã TAN (28/07) — và lý do nó tồn tại chính là bằng
  chứng phương án cũ sai.** Lập luận gốc: bỏ `track`+`service` khỏi `road_len_m` làm **tăng** số ô `road=0` nên
  đo E-DQ8 trước = phải đo lại lần hai. Điều đó chỉ đúng nếu 7b dùng **một cột duy nhất**. E-DQ7b đã chốt theo
  hướng **hai cột** (`road_access_m` cho lối vào, `road_len_m` cho cầu — xem [E-DQ7b](issues/e-data-quality/e-dq7b-road-semantics.md)):
  E-DQ8 đo trên `road_access_m` (xóm chỉ có đường mòn **vẫn có** đường) nên con số **đứng yên ở 6.350 ô**,
  đúng bằng giá trị sau 7a. E-DQ8 nay **đo được ngay**, có thêm 2 tập con để phân loại:
  27.828 ô lối vào phi chính thức (850.207 dân) và 100 ô có trạm sạc thật nhưng OSM không có đường nào.
  *(Cập nhật 28/07: dự đoán rằng **7a** làm xê dịch E-DQ8 cũng đã **sai** — clip biên giới xoá 14.369 ô nhưng
  gần như không ô nào có dân, nên E-DQ8 chỉ đi từ **6.352 → 6.350 ô**. Cả hai dự đoán xê dịch đều không xảy ra.)*
  *(⚠️ Đính chính 30/07: **số dân của dòng này lỗi thời** — "1.268.026" tính trên raster UN-**unadjusted**
  trước E-DQ7e. Trên artefact đang dùng: **6.350 ô / 1.241.833 người**. Số **ô** thì đúng như đã ghi. Cùng
  họ lỗi lỗi-thời-vì-7e với các con số của 7f, xem [E-DQ8a](issues/e-data-quality/e-dq8a-access-tier.md).)*
- **`E-DQ7c` phải xong trước `E-DQ7d`** — ràng buộc **còn nguyên** (khác hai cái trên). E-DQ7d hiệu chuẩn trọng
  số `demand_weight` bằng 18,6M bản ghi occupancy; không thể fit trọng số cho "trung tâm thương mại" trên một cột
  mà **84,8%** số đếm là toà chung cư. E-DQ7c giao ra **10 cột tách rời**; E-DQ7d gán trọng số. Hệ quả: mọi nguồn
  POI mới (Overture/FSQ) nếu muốn thay tầng này thì phải vào **trước** 7d, nếu không là fit trên một covariate
  sắp bị thay.
  *(Cập nhật 29/07: ràng buộc đã **được thoả** — nhưng audit cho thấy 10 cột tách rời ấy, dù fit tối ưu, chỉ
  đạt ρ = 0,329/0,865. Ràng buộc "7c trước 7d" vẫn đúng, nó chỉ **không đủ**: 7c làm cho tập feature **fit
  được**, không làm cho nó **đủ thông tin**.)*
- **`E-DQ7d` KHÔNG bị chặn bởi `E-DQ7e`/`E-DQ7f`/`E-DQ8`** dù nằm sau chúng trong hàng (đo 29/07). `E-DQ7e` là
  phép **rescale đơn điệu** của `pop` — trước đây chỉ là *phỏng đoán* ("gần đơn điệu"), nay **đã đo hai lần**:
  tỉ số UNadj/unadjusted là hằng số **0,979344** (std **2,4e-08** trên 2,64M pixel), và sau khi **thực sự đổi
  nguồn** (29/07), Spearman(`pop` cũ, `pop` mới) = **1,000000** trên toàn bộ 104.171 ô ⇒ thứ hạng **bất biến
  từng bit**, đúng thứ duy nhất mà `demand_weight` và MCLP quan tâm. Nói cách khác: **7e đã xong và 7d không
  phải chạy lại vì nó**. `E-DQ7f` **có** xê dịch thứ hạng, nhưng chỉ chạm
  **14/12.811 ô cung** (0,1%) nên không đầu độc phép hiệu chuẩn của 7d; `E-DQ8` không đụng tới target. Cái
  **thật sự** chặn chất lượng target vẫn là **`E-DQ1`/`E-DQ3`**: một trạm sai toạ độ đổ occupancy vào **sai ô**,
  đầu độc trực tiếp biến phụ thuộc. Vì vậy 7d chạy được **ngay**; chỉ cần chạy lại sau 7e/7f (rẻ, nhờ D1 tách
  harness khỏi trọng số) và ưu tiên đóng phần dư của E-DQ1/E-DQ3.

  > ⚠️ **Bổ sung 30/07 — `E-DQ8b` KHÔNG nhẹ như 7f, Kỳ cần biết trước khi fit.** Câu "E-DQ8 không đụng tới
  > target" vẫn đúng (8b không sửa occupancy), nhưng nó **sửa một FEATURE** (`pop_adj`) trên diện rộng hơn 7f
  > **hai bậc độ lớn**: 7f chạm **14/12.811** ô cung (0,1%), 8b chạm **2.541/12.811** (**19,83%**, +93.859
  > người). Vẫn **không** phải rào chặn, vì thứ hạng — thứ duy nhất `demand_weight` dùng — gần như bất động
  > **ở đúng chỗ 7d fit**: Spearman(`pop_adj` 7f↔8b) trên **tập cung** = **0,998947** và top-500 `pop_adj`
  > toàn quốc trùng **500/500**. Trên toàn lưới thì thấp hơn hẳn (**0,932865** trên 262.849 ô) vì 8b cố ý
  > dời khối lượng giữa các ô nông thôn. Kết luận: 7d **fit được ngay**, nhưng **phải fit trên artefact sau
  > 8b** — fit trên bản trước 8b rồi so với bản sau là so hai tập feature khác nhau.
  >
- **`E-DQ7a` mở khoá `E-DQ3`.** Để clip POI theo biên giới phải trích **polygon `admin_level=2`** từ chính `.pbf`
  đã freeze — đúng artefact mà `E-DQ3` cần để spatial-join admin, và do đó cũng giải phóng **758 `COORD_ADDR_MISMATCH`**
  mà E-DQ1 cố ý hoãn. Một artefact, ba issue → làm 7a **sớm nhất** dù E-DQ3 nằm cuối hàng. *(Đã xong 28/07:
  `vn_boundary.parquet` chứa sẵn **40 polygon `admin_level=4`**; `in_vn` đã thăng cấp **4/758** mismatch thành
  lỗi toạ độ xác nhận.)*
  > ⚠️ **Kết cục 30/07 — mở khoá đúng MỘT NỬA.** 40 polygon adm4 **không dùng được** (trộn hai niên đại sáp nhập
  > 2025) ⇒ E-DQ3 chốt nguồn **VNSDI cấp xã**, và ranh giới xã lại làm `in_vn` **thừa** ở vai detector (bắt **16**
  > toạ độ sai so với **4** của adm2, vì polygon quốc gia bao gồm lãnh hải). "Một artefact, ba issue" đúng về
  > **thứ tự làm**, nhưng không bảo đảm artefact đó là **nguồn tốt nhất** cho issue thứ ba. Chi tiết:
  > [E-DQ3](issues/e-data-quality/e-dq3-admin-enrichment.md).

Thứ tự này thay cho *kế hoạch làm sạch §8* trước đây ở [data-layer/overview.md](data-layer/overview.md) (đã gỡ — thứ tự nay nằm ngay ở đây). Nguyên tắc chung không đổi: **flag dòng, không xoá**; đối soát `input = output + quarantined + merged` ở mọi bước.

---

## 4. Bộ giải pháp — một file mỗi vấn đề

Chi tiết chẩn đoán · cách xử lý · kết quả đo · QA gate · limitation của **từng** vấn đề nằm ở
**[`docs/issues/`](issues/README.md)** (tách khỏi file này ngày **2026-07-30**: §3 cũ đã dài 1.660 dòng,
mỗi lần sửa một issue là một diff khổng lồ và không ai review được).

Riêng nhóm **`F`** và **`G`** (port từ nhánh Kỳ 30/07) chưa có file trong `issues/` — chi tiết chẩn đoán,
con số đo và cách fix nằm nguyên ở hai biên bản nguồn:
[sprint-reviews/data-pipeline-review-2026-07-28.md](sprint-reviews/data-pipeline-review-2026-07-28.md) (F1–F20)
và [review/2026-07-29-data-lead-review.md](review/2026-07-29-data-lead-review.md) (L1–L16). Con số trong hai
biên bản đó đo trên **nhánh Kỳ trước hợp nhất** — không trộn vào số liệu register/issues đo trên nhánh Giang.

Register này giữ **đúng ba việc**: chú giải, bảng trạng thái, và thứ tự xử lý (+ ghi chú hợp nhất §2.1).
Mọi con số đo được thuộc về file issue tương ứng — **không nhân bản số liệu ở hai nơi**.
