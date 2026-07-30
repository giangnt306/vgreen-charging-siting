# KNOWN ISSUES & LIMITATIONS REGISTER

*Danh sách vấn đề của bài toán tối ưu vị trí trạm sạc VGreen. Đây là **nguồn chân lý để monitor & xử lý** — mỗi vấn đề có: mức độ, phạm vi xử lý trong internship, chủ sở hữu, ngày xử lý, hướng khắc phục, trạng thái. Cập nhật cột **Trạng thái** + **processed_date** khi tiến triển.*

## 1. Chú giải

- **Nhóm:**
  - `A` Demand Target & Data Science
  - `B` Spatial Geometry & Siting Mechanics
  - `C` Master Data & Entity Resolution
  - `D` Covariates & Feature Engineering
  - `E` Data Quality & Cleaning (di chuyển khỏi `data-layer/overview.md §7` ngày 24/07 để không theo dõi trùng ở 2 nơi)
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
| **[P10](issues/d-covariates/p10-worldpop-vintage.md)**    | D     | WorldPop 2020 lỗi thời (6 năm)                                                                                                                                                                                                                                                                                                                                                            | 🟡   | DOC                   | Giang           | —                   | ⊘           |
| **[P11](issues/d-covariates/p11-car-ownership.md)**    | D     | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ)                                                                                                                                                                                                                                                                                                                | 🟠   | SIMPLIFY              | Giang           | —                   | ☐           |
| **[E-DQ10](issues/e-data-quality/e-dq10-freeze-snapshot.md)** | E     | Chưa freeze snapshot / provenance                                                                                                                                                                                                                                                                                                                                                           | 🟡   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **[E-DQ9](issues/e-data-quality/e-dq9-aoi-clip.md)**  | E     | Grid toàn quốc vs MVP 1 thành phố (`demand_h3` toàn bảng)                                                                                                                                                                                                                                                                                                                            | 🟡   | SIMPLIFY              | Giang           | **2026-07-27** | ☑           |
| **[E-DQ2](issues/e-data-quality/e-dq2-crosssource-dedup.md)**  | E     | Trùng chéo nguồn (evcs vs official)                                                                                                                                                                                                                                                                                                                                                       | 🟠   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **[E-DQ1](issues/e-data-quality/e-dq1-coord-placeholder.md)**  | E     | Toạ độ placeholder trùng khít                                                                                                                                                                                                                                                                                                                                                          | 🟠   | FIX                   | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7a](issues/e-data-quality/e-dq7a-poi-outside-vn.md)** | E     | **POI ngoài lãnh thổ VN** — Overpass query bằng `VN_BBOX` thô, không clip biên giới → **54,2%** POI nằm ở Campuchia/Lào/Thái/TQ                                                                                                                                                                                                                                  | 🔴   | **FIX (chặn)** | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7b](issues/e-data-quality/e-dq7b-road-semantics.md)** | E     | **`road_len` sai ngữ nghĩa** <br />1.`track`+`service` tính là đường sinh cầu (19,9%)<br /><br />2. double-count 2 chiều (motorway 96,9% `oneway`)<br />3. `_MAJOR` gộp cao tốc + quốc lộ + tỉnh lộ                                                                                                                                                           | 🟠   | FIX                   | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7c](issues/e-data-quality/e-dq7c-poi-taxonomy.md)** | E     | **POI thiếu & lẫn đơn vị**1. Tỉ lệ`apartments` với `mall`bị gắn mặc đinh là 1:1 (**84,8%** số đếm ở top-100 ô là chung cư);<br /><br />2. Lẫn đơn vị **bên trong** từng nhóm crawl<br /><br />3. **335** trùng node/way + 13 đối tượng ở 2 nhóm<br /><br />4. recall OSM **fuel 35,9% · parking 8,6%** (đo ngoại vi) | 🟠   | FIX + DOC             | Giang           | **2026-07-28** | ☑           |
| **[E-DQ7e](issues/e-data-quality/e-dq7e-pop-calibration.md)** | E     | **`pop` chưa hiệu chuẩn TUYỆT ĐỐI**:  raster UN-**unadjusted**: 99,627M so với bản UNadj **97,569M** (**+2,11%**).                                                                                                                                                                                                                                       | 🟡   | FIX + DOC             | Giang           | **2026-07-29** | ☑           |
| **[E-DQ7f](issues/e-data-quality/e-dq7f-pop-dasymetric.md)** | E     | `pop` bị dồn lại trong 1 vài ô dân cư  + DỒN THỪA xét trên cấp xã                                                                                                                                                                                                                                                                                                           | 🟠   | FIX                   | Giang           | **2026-07-29** | ☑           |
| **[E-DQ8a](issues/e-data-quality/e-dq8a-access-tier.md)** | E     | Chỉ xét đường đi trong 1 ô thay vì trong 1 nhóm các ô                                                                                                                                                                                                                                                                                                                             | 🟡   | FIX                   | Giang           | **2026-07-30** | ☑           |
| **[E-DQ8b](issues/e-data-quality/e-dq8b-roadless-reallocation.md)** | E     | Dân cư bị phân bố lại ở những ô không phải dân cư (E-DQ7f) -> ko có lối vào                                                                                                                                                                                                                                                                                               | 🟠   | FIX                   | Giang           | **2026-07-30** | ☑           |
| **[E-DQ8c](issues/e-data-quality/e-dq8c-servable-denominator.md)** | E     | **Dân KHÔNG phục vụ được — mẫu số, không phải làm sạch**: 225 ô / 42.576 người không dời được (xóm kênh rạch ĐBSCL đi thuyền) + lưới **chưa phải tessellation** (76 ô chứa 83 trạm vận hành không có dòng ở bảng lưới nào) | ⚪   | DOC → policy          | Giang/Kỳ       | —                   | ☐           |
| **[E-DQ7d](issues/e-data-quality/e-dq7d-demand-proxy-validation.md)** | E     | **Proxy cầu chưa kiểm chứng ngoại vi**                                                                                                                                                                                                                                                                                                                                            | 🔴   | **FIX (chặn)** | **Kỳ**  | —                   | ☐           |
| **[E-DQ4](issues/e-data-quality/e-dq4-asset-vs-live-config.md)**  | E     | Cấu hình súng thu thập được bị diễn giải sai - Xét số súng livePower (đang hoạt động) thay cho vì Asset (tổng số súng).                                                                                                                                                                                                                                               | 🟠   | FIX                   | Giang           | **2026-07-30** | ☑           |
| **[E-DQ5](issues/e-data-quality/e-dq5-operator-ownership.md)**  | E     | ~~Trường `operator` bẩn~~ → **tiền đề bị bác**: `operator` là **HẰNG SỐ** trên tập cung (0 null, **1** giá trị phân biệt) ⇒ **không có gì để làm sạch**. Tín hiệu chủ sở hữu/mặt bằng nằm ở `name` chưa parse (**76,8%** cung mang token `Tư nhân`/`NQ`) — **Giang chốt 30/07: không cần sửa trong scope**, giữ lại làm ghi chú vì nó là *feature* tiềm năng, không phải lỗi. **33** dòng lỗi phạm trù (payment → network) theo cùng `E-DQ6` nếu mở lại | ⚪   | DOC → FUTURE          | Giang           | **2026-07-30** | ⊘           |
| **[E-DQ6](issues/e-data-quality/e-dq6-freetext-cleanup.md)**  | E     | Text tự do bẩn (`name`, `address`)                                                                                                                                                                                                                                                                                                                                                     | ⚪   | SIMPLIFY              | Giang           | —                   | ☐           |
| **[E-DQ3](issues/e-data-quality/e-dq3-admin-enrichment.md)**  | E     | Cột admin trống (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`) **+ trọng tài `COORD_ADDR_MISMATCH` của E-DQ1** (nguồn: ranh giới xã VNSDI 2025-06-16)                                                                                                                                                                                                                                                                                                 | 🟡   | FIX                   | Giang           | **2026-07-30**      | ☑           |

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

Register này giữ **đúng ba việc**: chú giải, bảng trạng thái, và thứ tự xử lý. Mọi con số đo được thuộc về file
issue tương ứng — **không nhân bản số liệu ở hai nơi**.
