# KNOWN ISSUES & LIMITATIONS REGISTER

*Danh sách vấn đề của bài toán tối ưu vị trí trạm sạc VGreen. Đây là **nguồn chân lý để monitor & xử lý** — mỗi vấn đề có: mức độ, phạm vi xử lý trong internship, chủ sở hữu, ngày xử lý, hướng khắc phục, trạng thái. Cập nhật cột **Trạng thái** + **processed_date** khi tiến triển.*

## 1. Chú giải

- **Nhóm:**
  - `A` Demand Target & Data Science
  - `B` Spatial Geometry & Siting Mechanics
  - `C` Master Data & Entity Resolution
  - `D` Covariates & Feature Engineering
  - `E` Data Quality & Cleaning (di chuyển từ `data-layer-overview.md §7` — xem Task-1 rationale)
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

| ID               | Nhóm | Vấn đề                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | Mức | Phạm vi              | Owner           | ngày giải quyết   | Trạng thái |
| ---------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | --------------------- | --------------- | -------------------- | ------------ |
| **P1**     | A     | Heuristic weights thay vì fit model có giám sát trên 18,6M occupancy — ⚠️**tiền đề đã bị bác bỏ 29/07**: fit trọng số trên 10 cột hiện có chỉ hơn `pop` đơn **+0,07** và hơn **trọng số bị đảo** +0,06 ⇒ gộp vào **E-DQ7d**, đổi mục tiêu sang **bổ sung feature dòng chảy**                                                                                                                                                                                                                                                                       | 🟠   | SIMPLIFY              | Kỳ             | —                   | ☐           |
| **P2**     | A     | Selection bias: chỉ quan sát demand nơi**đã có** trạm                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ⚪   | DOC → FUTURE         | Giang/Kỳ       | —                   | ⊘           |
| **P3**     | A     | Cửa sổ 7,15 ngày → bỏ qua mùa vụ/lễ/thời tiết                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | ⚪   | DOC → FUTURE         | Giang           | —                   | ⊘           |
| **P4**     | B     | **Bán kính suy biến:** R = 500 m < khoảng cách tâm 2 ô kề (0,98 km) → MCLP = sort top-p; 500 m không phải catchment lái xe                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 🔴   | **FIX (chặn)** | Kỳ + Giang     | **2026-07-24** | ☑           |
| **P5**     | B     | Candidate set chưa định nghĩa; thiếu lọc land-use (hồ/núi/đất cấm)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 🟡   | SIMPLIFY              | Giang           | **2026-07-24** | ☑           |
| **P6**     | C     | Trùng PK (236 dòng); số trạm lệch giữa doc/report (28.417 vs 28.625)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | 🟡   | FIX                   | Giang           | **2026-07-24** | ☑           |
| **P7**     | C     | Nhiễm xe máy điện: dùng power tier chung thay vì chuẩn cắm (CCS2)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 🟠   | FIX                   | Giang           | **2026-07-24** | ☑           |
| **P8**     | C     | Thiếu lọc trạng thái vận hành & access (private vs public)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 🟡   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **P9**     | C     | Lệch thời điểm giữa các đợt crawl (occupancy 2026 · WorldPop 2020 · OSM)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 🟡   | FIX + DOC             | Giang           | —                   | ☐           |
| **P10**    | D     | WorldPop 2020 lỗi thời (6 năm)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 🟡   | DOC                   | Giang           | —                   | ⊘           |
| **P11**    | D     | Model tổng dân số thay vì mật độ**sở hữu ô tô** (~5–9% hộ)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | 🟠   | SIMPLIFY              | Giang           | —                   | ☐           |
| **E-DQ10** | E     | Chưa freeze snapshot / provenance                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | 🟡   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **E-DQ9**  | E     | Grid toàn quốc vs MVP 1 thành phố (`demand_h3` toàn bảng)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 🟡   | SIMPLIFY              | Giang           | **2026-07-27** | ☑           |
| **E-DQ2**  | E     | Trùng chéo nguồn (evcs vs official)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | 🟠   | FIX                   | Giang           | **2026-07-27** | ☑           |
| **E-DQ1**  | E     | Toạ độ placeholder / trùng khít                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 🟠   | FIX                   | Giang           | **2026-07-28** | ☑           |
| **E-DQ7a** | E     | **POI ngoài lãnh thổ VN** — Overpass query bằng `VN_BBOX` thô, không clip biên giới → **54,2%** POI nằm ở Campuchia/Lào/Thái/TQ (và **8.934 km road** rò rỉ: Geofabrik cắt bằng polygon **có đệm**)                                                                                                                                                                                                                                                                                                                                                                           | 🔴   | **FIX (chặn)** | Giang           | **2026-07-28** | ☑           |
| **E-DQ7b** | E     | **`road_len` sai ngữ nghĩa** — `track`+`service` tính là đường sinh cầu (19,9%); double-count 2 chiều (motorway 96,9% `oneway`); `_MAJOR` gộp cao tốc + quốc lộ + tỉnh lộ                                                                                                                                                                                                                                                                                                                                                                                                                     | 🟠   | FIX                   | Giang           | **2026-07-28** | ☑           |
| **E-DQ7c** | E     | **POI thiếu & lẫn đơn vị** — `n_poi` cộng `apartments` (toà nhà) với `mall` (trung tâm) tỉ lệ 1:1 (**84,8%** số đếm ở top-100 ô là chung cư); lẫn đơn vị **bên trong** từng nhóm crawl; **335** trùng node/way + 13 đối tượng ở 2 nhóm; recall OSM **fuel 35,9% · parking 8,6%** (đo ngoại vi)                                                                                                                                                                                                                                                       | 🟠   | FIX + DOC             | Giang           | **2026-07-28** | ☑           |
| **E-DQ7e** | E     | **`pop` chưa hiệu chuẩn TUYỆT ĐỐI** — raster UN-**unadjusted**: 99,627M so với bản UNadj **97,569M** (**+2,11%**). Đo 29/07: UNadj là **hằng số quốc gia 0,979344** (std **2,4e-08** trên 2,64M pixel) ⇒ **không xê dịch thứ hạng**, chỉ làm sai mọi phát biểu **tuyệt đối** (`coverage_pop`, đối chiếu GSO). **Đã đổi nguồn sang file UNadj** (không hardcode hệ số) + **3 cổng QA**; Spearman(cũ, mới) = **1,000000** trên 104.171 ô                                                                     | 🟡   | FIX + DOC             | Giang           | **2026-07-29** | ☑           |
| **E-DQ7f** | E     | **`pop` dồn cục dasymetric + DỒN THỪA cấp xã** — đo lại trên artefact UNadj: **139 ô / 745.283 dân** dồn vào 1–5 pixel (đỉnh **28.731/pixel**); ngưỡng mật độ cũ bắt **61 ô lõi TP.HCM THẬT** và **0/139** ô hỏng (**giao = 0**). Đối chiếu **VNSDI DANSO** (nguồn cấp xã độc lập): **63% khối lượng là dồn THỪA** (WorldPop>1,5×DANSO; 16 ô có 1 ô > cả xã; đảo 22×) → thêm `pop_adj` (RETOTAL 17 xã / REPLACE 53 xã, rải theo built-up) + cờ `pop_pixel_implausible`; top-500 **16→0**, 7 cổng QA | 🟠   | **DONE**        | Giang           | **2026-07-29** | ☑           |
| **E-DQ8a** | E     | **Lối vào đo ở thang SAI** — `buildable_h3`/E-DQ8 hỏi "ô này có đường không?" bằng cách xét **đúng ô đó**, nhưng tâm 2 ô res 8 chỉ cách 0,98 km: **4.862/6.350 ô** (72,1% khối lượng · 894.956 người) có đường ngay ở **vành 1**. Lỗi **THANG ĐO**, không phải lỗi dữ liệu — cùng bẫy `poi_coords_in_vn` (7a) / `POP_DENSITY_OUTLIER` (7f). Thêm bậc `access_tier` (DIRECT/ADJACENT/NEAR/ISOLATED) + 2 cột vành; loại cứng **chỉ** ISOLATED (**6.350 → 723 ô**). Neo ngoại vi: 99,43% trạm đang vận hành ở DIRECT, **15 trạm ở ADJACENT** ⇒ ADJACENT tới được THẬT, nhưng **không** tương đương DIRECT | 🟡   | **DONE**              | Giang           | **2026-07-30** | ☑           |
| **E-DQ8b** | E     | **Dân ở ô không có lối vào chưa được dời** — dùng lại đúng bộ máy 7f (trọng tài DANSO → rải theo built-up → kế toán theo TỔNG) nhưng **ngược kết luận về khối lượng**: chỉ **18,5%** khối lượng nằm trong xã RETOTAL (7f: 63%) ⇒ mặc định là **REPLACE bảo toàn khối lượng**, không phải gỡ người ma. Dời **6.244 ô** sang ô DIRECT có built-up cùng xã; khối lượng roadless **1.241.833 → 42.249 (−96,6%)**; gỡ 110.855 người ma; `pop` **bất biến từng bit**. Trọng số ô nhận có xét lối vào ⇒ **sửa luôn hồi quy D4 của 7f** (7f tự sinh 6.350→6.467 ô roadless). 8 cổng QA | 🟠   | **DONE**              | Giang           | **2026-07-30** | ☑           |
| **E-DQ8c** | E     | **Dân KHÔNG phục vụ được — bài toán MẪU SỐ, không phải làm sạch.** Dư sau 8b: **225 ô / 42.576 người** không dời được (222 ô ngoài mọi polygon xã VNSDI · 3 ô ở xã không có đất vừa built-up vừa DIRECT). Cụm lõi là xóm kênh rạch ĐBSCL (9,8–10,0 N / 104,9 E, `frac_water` 0,43–0,66) — người **thật**, đi lại bằng thuyền, xe không vào được. Phải gắn `demand_servable=False` và **trừ khỏi `coverage_pop`** kèm số công bố, không để đọng thành mẫu số không thể phủ | ⚪   | DOC → policy          | Giang/Kỳ       | —                   | ☐           |
| **E-DQ7d** | E     | **Proxy cầu chưa kiểm chứng ngoại vi** — audit 29/07: trần đo được của target ρ = **0,865**, proxy chỉ đạt **0,33** (38% tín hiệu khả dụng); **trọng số KHÔNG phải nút thắt** (fit tốt nhất 0,329 vs **đảo trọng số 0,266** vs `pop` đơn 0,261); target thô **77% là công suất** (ρ(occ, số súng) = **0,773**); **644** ô (không phải 983) có sạc thật mà mọi input = 0, **488** ô trong đó có xe sạc thật                                                                                                     | 🔴   | **FIX (chặn)** | **Kỳ**  | —                   | ☐           |
| **E-DQ4**  | E     | Cấu hình khuyết (`current_type`, `max_power_kw`, `total_power_kw`, `num_connectors=0`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 🟡   | FIX                   | Giang           | —                   | ☐           |
| **E-DQ5**  | E     | Trường`operator` bẩn                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | 🟡   | FIX                   | Giang           | —                   | ☐           |
| **E-DQ6**  | E     | Text tự do bẩn (`name`, `address`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | ⚪   | SIMPLIFY              | Giang           | —                   | ☐           |
| **E-DQ3**  | E     | Cột admin trống (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | 🟡   | FIX                   | Giang           | —                   | ☐           |

---

## 3. Bộ giải pháp triển khai

### A. Demand Target & Data Science

#### P1 — Heuristic weights vs fit model 18,6M occupancy

`🟠 SIMPLIFY · ☐ Open · Owner: Kỳ` — **gộp vào [E-DQ7d](#e-dq7d--proxy-cầu-chưa-kiểm-chứng-ngoại-vi-bước-7)** (29/07)

> ⚠️ **Đính chính 29/07 — tiền đề của P1 đã bị bác bỏ bằng đo đạc.** P1 giả định vấn đề nằm ở
> **trọng số** ("heuristic thay vì fit"). Audit E-DQ7d fit đúng cái mà P1 đề xuất — NNLS không âm trên
> log1p, 20 cột (10 feature × k0/k-ring 1), spatial CV **leave-one-province-out** 64 tỉnh, 11.628 ô cung
> — và được **ρ = 0,329**. Cùng lúc: `pop` **đơn độc** cho **0,261**, và **đảo ngẫu nhiên chính bộ trọng
> số vừa fit** vẫn cho **0,266**. Tức là toàn bộ công sức "fit có giám sát" mua được **+0,07 so với không
> làm gì** và **+0,06 so với trọng số vô nghĩa**, trong khi trần đo được của target là **0,865**.
>
> ⇒ **Nút thắt không phải trọng số mà là TẬP FEATURE.** 10 cột hiện có mô tả *cư dân và cửa hàng*; còn
> occupancy do *xe đang di chuyển* và *thời gian đỗ* quyết định. Fit lại trọng số trên đúng tập cột này
> **không thể** đóng được khoảng cách 0,33 → 0,865, dù dùng model gì.

**P1 đổi mục tiêu** (không còn là "fit trọng số"): bổ sung **feature dòng chảy** dẫn từ `.pbf` **đã
freeze** (betweenness centrality mạng đường · khoảng cách tới nút giao cao tốc · 91 đối tượng
`highway=services|rest_area` mà E-DQ7b đã tìm ra) + **số hạng catchment k-ring** đồng bộ `R = 3 km`
(**P4**), rồi mới nói chuyện trọng số. Chi tiết chẩn đoán, seam bàn giao và bộ cổng:
[E-DQ7d](#e-dq7d--proxy-cầu-chưa-kiểm-chứng-ngoại-vi-bước-7).

**Giữ lại từ bản cũ (chưa kiểm chứng lại sau E-DQ7a/7b/7c):** hai công thức Proxy A & B cho gợi ý vị
trí tương đồng **91%** ($r = 0,91$). ⚠️ Con số này **không** chứng minh "heuristic đã ổn định" — hai
công thức cùng sai theo một hướng thì vẫn tương đồng cao; nó chỉ đo **độ nhạy giữa hai bộ trọng số**,
đúng thứ mà C3 của E-DQ7c cảnh báo là phải đo bằng **top-K overlap**, và đúng thứ mà cổng
`proxy_beats_scramble` bây giờ đo được **ngoại vi** thay vì nội tại.

### B. Spatial Geometry & Siting Mechanics

#### P4 — Bán kính suy biến & không phù hợp với ô tô

`🔴 FIX (chặn) · ☑ chốt 2026-07-24 · Owner: Kỳ + Giang`

**Chẩn đoán:** lỗi nằm ở **tỷ lệ** giữa bán kính phục vụ và độ mịn lưới, không phải ở một trong hai:

$$
\text{tỷ lệ} = \frac{R}{d}, \quad d = \text{khoảng cách giữa tâm 2 ô H3 kề nhau}
$$

Tỷ lệ < 1 ⇒ mỗi trạm chỉ phủ đúng ô chứa nó ⇒ mọi trạm trong cùng 1 ô là như nhau ⇒ MCLP suy biến thành `sort top-p`. Cấu hình cũ: `R = 500 m`, `d(res 8) = 0,98 km` → **tỷ lệ 0,51**. Chỉ có **2 đòn bẩy**: (i) tăng `R`, hoặc (ii) **thu nhỏ ô** (đi xuống res mịn hơn).

**Cách xử lý:**

- GIỮ lưới `H3 res 8`.
- CHỐT `R = 3 km` (baseline), quét dải {1,5 · 2 · 3 · 5} km.

#### P5 — Candidate set chưa định nghĩa & thiếu lọc land-use (hồ/núi/đất cấm)

`🟡 SIMPLIFY · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:** P5 thực chất là **3 câu hỏi độc lập**: (a) candidate sinh từ đâu, (b) điểm nào phải loại, (c) candidate là điểm hay ô H3. Giải chi tiết ở **[candidate-sites.md](data-layer/candidate-sites.md)**; tóm tắt bên dưới.

**Cách xử lý:**

- **(c) Granularity — mô hình lai.** Với `R = 3 km`, `d = 0,98 km` → `R/d = 3,07`, hai điểm bất kỳ trong cùng ô H3 phủ gần như y hệt tập ô demand → giữ nhiều điểm/ô gây MCLP **tie-degenerate** (biến thể ẩn của **P4**). Chốt: candidate = **một điểm thực** (giữ toạ độ để explainability), nhưng **tối đa 1 candidate/ô H3 res 8**; coverage tính theo `h3_r8`.
- **(a) Sinh candidate — phân tầng anchor.** T0 trạm hiện có (brownfield, `is_existing=True` — ràng buộc thiết kế: incumbent bắt buộc mở) · T1 `parking`/`fuel` · T2 `mall`/`retail`/`apartments` · **T4 gap-fill tổng hợp** (ô demand cao, buildable, chưa có anchor → centroid `SYNTHETIC`). T4 **bắt buộc** để chống thiên vị đô thị của OSM (POI thưa ở vùng ven → nếu không có T4 thì MCLP không thể chọn ở đó → mâu thuẫn mục tiêu "phủ công bằng" của Nhà nước). T3 rest_area/nút giao QL cần road-class từ `.pbf` → để roadmap.
- **(b) Bộ lọc land-use — 2 mức, `buildable_h3`.** Nền chính **ESA WorldCover 10m v200 (CC-BY)** vì OSM land-use ở VN quá thưa ("không có polygon nước" ≠ đất khô). *Loại cứng:* `frac_water≥0,5` · `water+wetland≥0,7` · `built_up_frac<0,05` (núi/rừng/chưa đô thị hoá) · cờ OSM MILITARY/PROTECTED/AIRPORT/WATER_OSM · `access_tier == ISOLATED` (không có đường trong ô **lẫn** vành 1/2 — **E-DQ8a** 30/07, thay `road_access_m≤0` vốn loại oan 4.862 ô có đường ở ô kề; nguồn vẫn là cột lối vào của **E-DQ7b**, GỒM `service`/`track`). *Phạt mềm:* đất nông nghiệp (`frac_crop≥0,6`) · hạ tầng mỏng · `NEEDS_ACCESS_ROAD` (đường chỉ ở vành — **E-DQ8a**) · `ROAD_ACCESS_INFORMAL` · `ROAD_BRIDGE_ONLY` · `pop>0 & road=0` (cờ chẩn đoán) · khoảng cách tới `power=substation` (proxy đấu nối lưới — Nhóm 2 #3).

**QA gate 5 cổng** (đóng P5 thật, không chỉ "có file candidate"): ① upper-bound coverage của toàn bộ candidate ≥ 90% demand lõi AOI (fail = candidate set chặn model) · ② `|candidates| ≥ 5×p` (tỷ lệ tự do) · ③ `|candidates| ≤ 3.000` (trần giải MCLP) · ④ **anti-degenerate** `unique(coverage_set)/|candidates| ≥ 0,9` (biến thể ẩn P4) · ⑤ gate lưới↔bán kính `R > d` (P4).

**Bàn giao Kỳ:** `data/processed/candidate_sites.{parquet,geojson}` — điểm chạm interop thứ 3. Cột `is_existing` + `capex_class` phục vụ ràng buộc ngân sách Sprint 3.

**Kết quả:**

- **MVP Hà Nội (24/07):** 1.672 candidate (T0 1.411 · T1 96 · T2 54 · T4 111); 79% ô AOI buildable, chỉ 17% ô `pop>0` bị loại (ngưỡng `BUILT_UP_MIN` hợp lý); **mọi gate PASS**.
- **Toàn quốc (national) — đã chạy 24/07:** trên **lưới `demand_h3` quốc gia (268.404 ô)** qua `--national` (`make landuse-national && make candidates-national`). Đã vector hoá/scale: WorldCover 16 tile đất + stride 8, OSM exclusion quadtree + STRtree, substation-dist BallTree, buildable numpy.

**Limitation (`DOC`):** quy hoạch sử dụng đất chính thức VN không public → WorldCover/OSM chỉ là **proxy** (điểm "buildable" vẫn có thể bị cấm theo quy hoạch địa phương); WorldCover 2021 vs 2026 (lệch vintage như **P10**); bias đô thị OSM giảm nhẹ bằng T4 nhưng không khử; candidate `SYNTHETIC` (T4) **không** trình bày như khuyến nghị chốt — phải kèm cảnh báo khảo sát thực địa.

### C. Master Data & Entity Resolution

#### P6 — Trùng PK & số trạm lệch giữa các báo cáo

`🟡 FIX · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:**

1. **Trùng PK (236 dòng).** Catalog evcs gộp từ 3 tab (`cs`/`other`/`bss`); enumerate quét lưới
   chồng lấn → cùng `station_code` xuất hiện nhiều lần.
2. **Số trạm lệch (28.417 vs 28.625).** Không phải lỗi dữ liệu mà là **doc-drift**: tài liệu ghi
   snapshot cũ **28.417**, còn file thực tế là snapshot chốt **28.625** (crawl lại 2026-07-21/22).

**Cách xử lý:**

- **Dedup có kiểm soát.** `merge_catalog.py` giữ **first-wins** (ưu tiên `cs > other > bss`),
  **đếm rõ** số dòng trùng bị bỏ (tách trong-tab vs chéo-tab) và in ra — **không bao giờ gộp/cộng
  công suất** giữa các bản trùng (nguyên tắc E-DQ2). `validate.py` có **cổng CRITICAL** bắt buộc
  `station_code` unique → pipeline **fail** nếu trùng PK tái xuất. Master hiện: **0 trùng**.
- **Đối soát số trạm về một snapshot chốt.** Neo **28.625** (snapshot 2026-07-21/22) là con số chính
  thức; chênh **+208** so với 28.417 = crawl lại tab `cs` (19.219 → 19.427). Đồng bộ mọi tài liệu
  ([evcs.md](sources/evcs.md), [schema-contract.md](schema/schema-contract.md)) + neo **chuỗi đối soát tầng**
  để dứt điểm câu hỏi "số nào đúng":

  $$
  \underbrace{28.625}_{\text{raw catalog}} \;-\; \underbrace{9.118}_{\text{BSS (lọc, --keep-bss để giữ)}}
  \;=\; \underbrace{19.507}_{\text{canonical car-only}} \;=\; \underbrace{19.427}_{cs} + \underbrace{80}_{other}
  $$

**Kết quả.** Master 28.625 trạm, PK `station_code` **unique** (0 CRITICAL), lineage ghi ở
`quality_report.json`. `by_station_type`: VINFAST_CS 19.427 · BATTERY_SWAP 9.118 · OTHER 80.

**Limitation (`DOC`):** đây chỉ giải **trùng PK nội bộ evcs** + đối soát số. Trùng **chéo nguồn**
(cùng 1 trạm vật lý lệch toạ độ giữa evcs và registry official) là **[E-DQ2](#e-dq2--trùng-chéo-nguồn-evcs--official-bước-2)** —
đã đóng 27/07 (identity resolution `physical_id`, **không** dedup H3 thô).

#### P7 — Nhiễm xe máy điện (dùng chung power tier)

`🟠 FIX · ☑ chốt 2026-07-24 · Owner: Giang`

**Chẩn đoán:** Gốc vấn đề là **nguồn tín hiệu**: `evse_powers` của evcs.vn
chỉ lộ **công suất (W)**, *không* lộ chuẩn cắm. Code cũ suy `AC/DC` từ một ngưỡng power tier
(`AC_MAX_W = 25 kW`) → hai hệ quả:

1. **Sai AC/DC ở dải 20-22 kW.** Đối chiếu registry chính thức VinFast cho thấy **20/22 kW
   là DC CCS2**, không phải AC. Ngưỡng 25 kW gán nhầm **1.588 connector (1.079 trạm)** thành AC.
2. **Không tách được xe máy/ô tô bằng công suất**

**Cách xử lý - chuẩn cắm là sự thật, không phải power tier.** `official_connectors.standard`
lộ chuẩn cắm IEC: `IEC_62196_T2_COMBO` = **CCS2**, `IEC_62196_T2` = **Type2**. Join theo
`(station_code, power_kw)` khớp **100%** (24.406/24.415 connector). Thêm 2 cột:

- `connectors.connector_standard` ∈ {`CCS2`, `TYPE2`, `UNKNOWN`}
- `connectors.vehicle_class` + roll-up `stations.vehicle_class` ∈ {`CAR`, `UNVERIFIED`, `UNKNOWN`}

`current_type` giờ **suy từ `power_type` chính thức** (AC/DC/MIXED), không từ ngưỡng kW nữa.

**Kết quả.** Sau khi lọc BSS (9.118 trạm đổi pin — hạ tầng 2 bánh thật), **100% connector khớp official đều là chuẩn ô tô** (CCS2 8.641 · Type2 15.765)

**Limitation (`DOC`):** chuẩn cắm chỉ xác minh được cho trạm khớp registry VinFast

#### P8 — Lọc trạng thái vận hành & access (private vs public)

`🟡 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** pipeline **chưa bao giờ lọc** trạm theo trạng thái vận hành hay quyền truy cập
→ trạm **đã ngừng** (OutOfService) vẫn tính là cung, trạm **tư nhân** (Restricted) vẫn tính là cung
công khai, và null (`status` 72 · `is_public` 80) bị **giữ ngầm** không tường minh. Hai trục **độc lập**:
(1) trạng thái vận hành, (2) access public/private.

**Cách xử lý — resolve official-first, tường minh, không xoá dòng.** Registry VinFast là
ground-truth ([[vinfast-official-join-key]]); `status` của evcs chỉ là **snapshot telemetry**
(trạng thái tức thời lúc polling occupancy) nên **không** lật ngược registry (vd evcs `Available`
một khoảnh khắc vs official `INACTIVE` → theo official). Thêm 3 cột canonical vào `stations`:

- **`op_status`** ∈ {`OPERATIONAL`, `MAINTENANCE`, `OUT_OF_SERVICE`, `UNKNOWN`} — official-first,
  fallback evcs khi trạm evcs-only. Gom telemetry occupancy (ACTIVE/BUSY ← Available/AllBusy) về
  `OPERATIONAL`; INACTIVE ← Maintaining → `MAINTENANCE`; OUTOFSERVICE/UNAVAILABLE → `OUT_OF_SERVICE`.
- **`access`** ∈ {`PUBLIC`, `RESTRICTED`, `UNKNOWN`} — official-first (Public/Restricted), fallback `is_public`.
- **`is_operational`** (bool) — **lọc cứng DUY NHẤT:** loại `OUT_OF_SERVICE` (trạm đã ngừng, không
  còn là cung thực). **MAINTENANCE + UNKNOWN GIỮ** (có hạ tầng vật lý / không có ground-truth) — chỉ
  flag để model quyết loc thêm (**chạy 2 chiều** ở bước xử lý khuyết, `E-DQ4`).

Cờ tường minh gắn vào `quality_flags`: `NOT_OPERATIONAL` · `UNDER_MAINTENANCE` · `STATUS_UNKNOWN` ·
`NON_PUBLIC` · `ACCESS_UNKNOWN`. `build_candidates._load_stations` loại **OUT_OF_SERVICE ∪ RESTRICTED**
khỏi anchor **T0** (T0 = incumbent *bắt buộc mở*, CapEx=0 → không được ép mở trạm đã ngừng/tư nhân).

**Kết quả** (19.507 trạm car-only). `op_status`: OPERATIONAL **16.014** · MAINTENANCE **3.392** ·
UNKNOWN **59** · OUT_OF_SERVICE **42**. `access`: PUBLIC **19.418** · UNKNOWN **67** · RESTRICTED **22**.
Cung công khai khả dụng (`is_operational & access=PUBLIC`) = **19.377**. T0 national loại **63 trạm**
(OUT_OF_SERVICE ∪ RESTRICTED) → **19.444**; candidate national **mọi gate PASS**.

**Limitation (`DOC`):** `MAINTENANCE` (3.392, ~17%) là quyết định giữ-làm-cung (siting chiến lược đa
năm coi hạ tầng bảo trì là brownfield hiện hữu); model có thể loại qua cờ `UNDER_MAINTENANCE`. UNKNOWN
(evcs-only, không khớp registry) không có ground-truth → giữ + flag, không suy đoán.

#### P9 — Lệch thời điểm giữa các đợt cào dữ liệu

`🟡 FIX + DOC · ☐ Open · Owner: Giang`

**Cách xử lý:** khóa cố định mốc thời điểm cung sạc chính thức là **2026-07-20** và dữ liệu telemetry occupancy **07/2026**.

### D. Covariates & Feature Engineering

#### P10 — WorldPop 2020 lỗi thời (6 năm)

`🟡 DOC · ⊘ Won't-fix · Owner: Giang`

- Thừa nhận hạn chế (`DOC`).
- **Hiệu chỉnh Pha 5:** Kết hợp WorldPop với số liệu dân số chính thức mới nhất của Tổng cục Thống kê (GSO) cấp tỉnh để tính toán chỉ số `coverage_pop` (% dân số được phủ trạm sạc thực tế).

#### P11 — Model tổng dân số vs mật độ sở hữu ô tô

`🟠 SIMPLIFY · ☐ Open · Owner: Giang`

- Giả thuyết: dữ liệu mật độ dân số chính là proxy cho dữ liệu mật độ sở hữu ô tô.

### E. Data Quality & Cleaning (từ `data-layer-overview.md §7`)

Các dòng **E-DQ** trong [Bảng tổng hợp §2](#2-bảng-tổng-hợp-vấn-đề-đã-gộp) đã được **sắp theo thứ tự xử lý** (trên → dưới) — mỗi bước làm nhỏ tập lỗi cho bước sau:

> `E-DQ10` freeze inputs ✅ → `E-DQ9` clip MVP city ✅ → `E-DQ2` dedup chéo nguồn ✅ → `E-DQ1` sửa toạ độ ✅ →
> **`E-DQ7a` clip biên giới VN ✅** → **`E-DQ7b` retype road ✅** → **`E-DQ7c` retype POI ✅** →
> **`E-DQ7e` hiệu chuẩn tuyệt đối ✅** → **`E-DQ7f` sửa dồn cục dasymetric ✅** →
> **`E-DQ8a` bậc lối vào ✅** → **`E-DQ8b` dời dân ô roadless ✅** → `E-DQ8c` mẫu số không phục vụ được →
> `E-DQ7d` kiểm chứng ngoại vi (**gate của `demand_weight`** — chẩn đoán xong 29/07, **bàn giao Kỳ**) → `E-DQ4` xử lý khuyết →
> `E-DQ5`+`E-DQ6` chuẩn hoá categorical → `E-DQ3` enrich admin (cũng trọng tài `COORD_ADDR_MISMATCH` của E-DQ1).

**Ba ràng buộc thứ tự trong nhóm `E-DQ7`** (lý do tách 6 dòng `E-DQ7a`–`E-DQ7f` thay vì 1):

- ~~**`E-DQ7b` phải xong trước `E-DQ8`.**~~ **Ràng buộc này đã TAN (28/07) — và lý do nó tồn tại chính là bằng
  chứng phương án cũ sai.** Lập luận gốc: bỏ `track`+`service` khỏi `road_len_m` làm **tăng** số ô `road=0` nên
  đo E-DQ8 trước = phải đo lại lần hai. Điều đó chỉ đúng nếu 7b dùng **một cột duy nhất**. E-DQ7b đã chốt theo
  hướng **hai cột** (`road_access_m` cho lối vào, `road_len_m` cho cầu — xem [E-DQ7b](#e-dq7b--road_len-sai-ngữ-nghĩa-bước-5)):
  E-DQ8 đo trên `road_access_m` (xóm chỉ có đường mòn **vẫn có** đường) nên con số **đứng yên ở 6.350 ô**,
  đúng bằng giá trị sau 7a. E-DQ8 nay **đo được ngay**, có thêm 2 tập con để phân loại:
  27.828 ô lối vào phi chính thức (850.207 dân) và 100 ô có trạm sạc thật nhưng OSM không có đường nào.
  *(Cập nhật 28/07: dự đoán rằng **7a** làm xê dịch E-DQ8 cũng đã **sai** — clip biên giới xoá 14.369 ô nhưng
  gần như không ô nào có dân, nên E-DQ8 chỉ đi từ **6.352 → 6.350 ô**. Cả hai dự đoán xê dịch đều không xảy ra.)*
  *(⚠️ Đính chính 30/07: **số dân của dòng này lỗi thời** — "1.268.026" tính trên raster UN-**unadjusted**
  trước E-DQ7e. Trên artefact đang dùng: **6.350 ô / 1.241.833 người**. Số **ô** thì đúng như đã ghi. Cùng
  họ lỗi lỗi-thời-vì-7e với các con số của 7f, xem [E-DQ8a](#e-dq8a--lối-vào-đo-ở-thang-sai-bước-10).)*
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
- **`E-DQ7a` mở khoá `E-DQ3`.** Để clip POI theo biên giới phải trích **polygon `admin_level=2`** từ chính `.pbf`
  đã freeze — đúng artefact mà `E-DQ3` cần để spatial-join admin, và do đó cũng giải phóng **758 `COORD_ADDR_MISMATCH`**
  mà E-DQ1 cố ý hoãn. Một artefact, ba issue → làm 7a **sớm nhất** dù E-DQ3 nằm cuối hàng. *(Đã xong 28/07:
  `vn_boundary.parquet` chứa sẵn **40 polygon `admin_level=4`**; `in_vn` đã thăng cấp **4/758** mismatch thành
  lỗi toạ độ xác nhận.)*

Thứ tự này thay cho *kế hoạch làm sạch §8* trước đây ở `data-layer-overview.md` (đã gỡ — thứ tự nay nằm ngay ở bảng). Nguyên tắc chung không đổi: **flag dòng, không xoá**; đối soát `input = output + quarantined + merged` ở mọi bước.

#### E-DQ10 — Freeze snapshot & provenance (bước 0)

`🟡 FIX · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** provenance có nhưng **rời rạc & không tái lập được** — `.pbf` mang tên
`vietnam-**latest**` (không phải phiên bản), không có checksum nào chứng minh một file thô
là **bất biến**, mốc thời gian chỉ nằm rải trong `quality_report.json`/`locators_meta.json`, và
**không sản phẩm dẫn xuất nào ghi nó dựng từ snapshot nào**. Vì `E-DQ10` là **bước 0**
(`freeze → clip → dedup → …`), mọi bước phía sau giả định input bên dưới không đổi; nếu nguồn âm
thầm đổi giữa sprint, đối soát `input = output + quarantined + merged` trở nên **vô nghĩa** và
không thể tái lập "28.625 trạm" hay số coverage. Đây cũng là chỗ **vận hành hoá [P9](#p9--lệch-thời-điểm-giữa-các-đợt-cào-dữ-liệu)**:
P9 *quyết* ngày freeze, E-DQ10 làm nó **có checksum & tái lập**.

**Cách xử lý — một snapshot bất biến, content-addressed, có cổng chặn drift.**

- **`snapshot_id = 2026-07-20`** (neo P9). Trùng khớp `osmosis_replication_timestamp` của bản `.pbf`
  (`2026-07-20T20:21:16Z`, seq **4852**) → chính mốc này **pin** nguồn OSM "latest" về một phiên bản
  cụ thể (giải quyết lỗ hổng tái lập lớn nhất mà **không** cần đổi tên file / churn `roads_pbf.py`).
- **`data/raw/MANIFEST.json`** — khai báo tập trung **mọi nguồn thô** + provenance (URL, giấy phép,
  vintage/version, phạm vi không/thời gian). File đơn băm `sha256` nội dung; thư mục nhiều file
  (details 23.240 file, worldcover 17 tile…) cuộn thành **1 bản ghi** `tree_sha256` để manifest gọn
  (9,5 KB) mà vẫn content-addressed. Version tự rút từ nguồn: official `generation 16 · count 58.577`,
  WorldCover `v200/2021`, WorldPop `2020 constrained`.
- **Lineage version-hoá trong git.** Blob thô vẫn `.gitignore`, nhưng `.gitignore` được sửa để
  **re-include đúng `MANIFEST.json`** → checksum + provenance **được commit** dù dữ liệu thì không.
- **Khoá read-only.** `freeze_snapshot` bỏ cờ ghi trên **23.280 file** thô (chống sửa vô tình; re-crawl
  = snapshot mới, phải unlock có chủ đích).
- **Cổng chặn drift 2 tầng.** `validate.py` (cổng QA evcs, đã chặn pipeline) nạp manifest và đối chiếu
  *nhanh* (tồn tại + bytes + số file, không đọc nội dung) mỗi lần chạy → **drift = CRITICAL**; chưa
  freeze = WARN (không chặn pipeline cũ). Đối chiếu *đầy đủ* (băm lại nội dung / `tree_sha256`) chạy
  theo yêu cầu: `make verify-snapshot HASHES=1`. Mọi `quality_report.json` nay mang `snapshot_id` +
  `snapshot_integrity`.

**QA gate (đóng E-DQ10 thật, không chỉ "có file manifest"):** ① mọi nguồn có `version/vintage` non-null
(không còn `latest`/undated) · ② `retrieved`/`bytes`/`sha256` đầy đủ · ③ re-hash on-disk == manifest
(lệch = FAIL) · ④ `snapshot_id` xuất hiện trên `quality_report.json` dẫn xuất · ⑤ manifest được git track
dù `/data/` bị ignore.

**Kết quả** (chạy 27/07): snapshot **2026-07-20**, **5 nguồn / 10 member / ~2,19 GB** đóng băng; verify
nhanh **PASS**, verify content-hash **PASS**, drift test (thêm 1 file lạ) bắt đúng **FAIL**, lock read-only
xác nhận (ghi vào file thô → *Permission denied*). Lệnh: `make freeze` / `make verify-snapshot`.

> **Cập nhật 29/07 — khoá read-only đã bắt được một lỗi thật.** Khi dựng lại chuỗi downstream của
> [E-DQ7e](#e-dq7e--pop-chưa-hiệu-chuẩn-tuyệt-đối-bước-8), `landuse/osm_exclusion.py` **crawl lại Overpass và
> ghi đè** `data/raw/landuse/osm_exclusion/*.json` → bị chặn bằng `PermissionError`. Tức bước **dẫn xuất** này
> vốn **không tái lập được** (Overpass trả khác nhau theo thời điểm) và âm thầm phá snapshot ở mọi lần chạy
> trước. Đã sửa: `_load_or_fetch` đọc thẳng snapshot đã freeze, `--refetch` mới crawl lại. Snapshot nay
> **5 nguồn / 11 member** (worldpop 1 → **2**: raster UNadj + bản unadjusted legacy, tổng **44,1 MB**);
> `make freeze` + `make verify-snapshot HASHES=1` đều **PASS** (23.281 file khoá).

**Limitation (`DOC`):** git giữ **manifest + checksum**, không giữ blob (WorldPop/OSM hàng trăm MB) → tái
lập đảm bảo *khi có cùng file nguồn*; nếu upstream (Geofabrik, WorldPop) xoay URL thì re-fetch là
best-effort — chính vì thế phải chốt `retrieved_at` + hash **ngay bây giờ**. Cổng ở tầng nhanh soát
bytes/số file (không đọc nội dung) để không làm chậm mỗi lần chạy; đổi nội dung mà **giữ nguyên kích
thước** chỉ bị bắt ở `--hashes` (CI/theo yêu cầu).

#### E-DQ9 — Grid toàn quốc vs MVP 1 thành phố (bước 1)

`🟡 SIMPLIFY · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** `demand_h3` được build ở **quy mô toàn quốc** (**268.404 ô** res 8 phủ toàn VN), nhưng
MVP chỉ cần chạy trên **1 thành phố**. Nếu mọi bước hạ nguồn (land-use, buildable, candidate, coverage)
đọc thẳng toàn bảng thì (a) chi phí giải MCLP nổ vượt trần 3.000 candidate (**P5** cổng ③), và (b) demand
ở **rìa AOI** bị coi là "chưa phủ" oan vì trạm phủ nó có thể nằm ngoài cửa sổ. Cần một cơ chế **cắt lưới
về đúng vùng nghiên cứu** mà **không** fork code giữa chế độ MVP-thành-phố và toàn-quốc — nếu không, hai
đường chạy sẽ trôi khỏi nhau (biến thể **doc-drift** của **P6**).

**Cách xử lý — một trừu tượng AOI, duck-typed, một đường code cho cả hai chế độ.** Trọn bộ nằm ở
[`src/ev_siting/aoi.py`](../../src/ev_siting/aoi.py):

- **`AOI`** = `tròn(tâm, radius_km) + vành buffer_km` (mặc định 5 km). `radius_km` = **lõi** (nơi đo
  coverage/DoD); `buffer_km` = vành ngoài, candidate **được phép** đặt nhưng gắn cờ `in_core=False`
  (trạm rìa vẫn phủ lõi → không bị tính "chưa phủ" oan). `CITY_PRESETS` chốt sẵn 5 TP
  (hanoi/hcm/danang/haiphong/cantho); `.cells()` sinh đĩa H3 quanh tâm rồi lọc theo bán kính thật.
- **`NationalAOI`** = **cùng giao diện** (`bbox()`/`contains()`/`in_core()`/`cells()`/`to_dict()`) nhưng
  `.cells()` đọc thẳng lưới quốc gia từ `demand_h3`. Nhờ duck-typing, **mọi module hạ nguồn không biết**
  đang chạy city hay national — không có nhánh `if national` rải rác.
- **Một điểm điều phối:** `add_aoi_args`/`aoi_from_args`/`resolve_aoi` cắm cùng nhóm cờ CLI
  (`--city <preset>` ↔ `--national`) vào **mọi** pipeline tiêu thụ AOI: `landuse/worldcover.py`,
  `landuse/build_buildable_h3.py`, `landuse/osm_exclusion.py`, `features/build_covered0.py`,
  `features/build_candidates.py`. Đổi phạm vi = đổi **một cờ**, không đụng logic.
- **Không đụng độ mịn lưới.** Clip chỉ **chọn tập ô**, vẫn giữ `H3 res 8` → **không** phá tỷ lệ `R/d`
  của **P4** (clip ≠ đổi resolution).

**QA gate (đóng E-DQ9 thật, không chỉ "có class AOI"):** ① một đường code chạy được **cả** `--city` lẫn
`--national` trên cùng module (không fork) · ② clip là **hàm tất định của hình học AOI** (mọi consumer
lọc qua cùng `aoi.contains`/`aoi.cells` → không phân kỳ giữa các bước) · ③ tách bạch `in_core` (đo phủ)
vs buffer (được đặt) để demand rìa không bị phạt oan · ④ `|candidate|` sau clip nằm trong trần MCLP của
**P5** · ⑤ metadata AOI (`to_dict()`) ghi vào report/sidecar để truy vết cấu hình mỗi lần chạy.

**Kết quả** (chạy 27/07): cùng một pipeline, hai phạm vi kiểm chứng:

- **MVP Hà Nội:** AOI = lõi 25 km + buffer 5 km (bán kính ngoài 30 km) → **3.141 ô** res 8 (từ
  268.404 ô quốc gia, **~1,2%**). Candidate build trên AOI này ra **1.672 candidate**, **mọi gate P5 PASS**.
- **Toàn quốc:** `--national` chạy trên đủ **268.404 ô** (đã vector hoá/scale — xem **P5**).

**Limitation (`DOC`):** AOI hiện là **tròn(tâm, bán kính)**, **không** phải ranh giới hành chính thật
(cột admin còn null — **E-DQ3**). Bán kính lõi mỗi TP chọn theo phạm vi đô thị hoá liên tục chứ không
theo địa giới, nên rìa AOI là **xấp xỉ**. Khi **E-DQ3** enrich xong, chỉ cần thay `AOI.cells()` bằng
spatial-join với polygon xã/tỉnh — mọi module tiêu thụ AOI **không phải sửa** (đó chính là lý do trừu
tượng hoá duck-typed).

#### E-DQ2 — Trùng chéo nguồn (evcs ↔ official) (bước 2)

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
[`dedup_crosssource.py`](../../src/ev_siting/data/evcs/dedup_crosssource.py):

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
  `is_primary` (giống `is_operational` của P8) — [`build_candidates._load_stations`](../../src/ev_siting/features/build_candidates.py)
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

#### E-DQ1 — Toạ độ placeholder / trùng khít (bước 3)

`🟠 FIX · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán — đo trên canonical car-only (19.507).** Toạ độ **không thiếu** (0 null · 0 zero · 0 ngoài
bbox VN — mọi điểm "hợp lệ về hình thức") nhưng **sai**: **204 nhóm toạ độ trùng khít** phủ **478 trạm**;
cụm lớn nhất **35 trạm** dồn về **một điểm HCM** `(10.773106, 106.694794)` trong khi địa chỉ toàn **Hà Nội /
Bắc Ninh / Hưng Yên** (charger "Tư nhân"). `lat/lng` là **khoá join của mọi bước hạ nguồn** (`h3_r8`,
coverage/gap, anchor **T0**, demand proxy) → 35 trạm Hà Nội bị tính là **cung HCM** ⇒ phủ ảo ở HCM + gap giả
ở Hà Nội ⇒ MCLP khuyến nghị **sai chỗ**. Đây là poisoning hàm mục tiêu, không phải lỗi cosmetic.

**Phát hiện quyết định (định hình lời giải):** cả **35/35 `official_matched`**, và **registry official cũng
ghi đúng điểm placeholder đó** (111 store official chung 1 điểm, 100% prefix mã `HNO`). ⇒ **"snap về official"
(official-first như P7/P8) KHÔNG cứu được E-DQ1** — official sai ở đúng trường này. Nhưng `province_code`
(rút từ prefix mã `C.HNO…` → HNO, **độc lập toạ độ**) lại là ground-truth tỉnh đáng tin.

**Hai detector — KHÁC nhau về mức độ chắc chắn "toạ độ là trường sai":**

| Detector                            | Tín hiệu                                                                                                                                                                                | Chắc chắn                            | Xử lý                                                                                                            |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **A `COORD_PLACEHOLDER`**   | nhóm exact-coord ≥`STACK_MIN=5` `physical_id` khác nhau **VÀ** điểm chung **cách centroid-tỉnh của các thành viên > 100 km** (∪ `DUP_COORD_SUSPECT` E-DQ2) | **toạ độ chắc chắn sai**    | `coord_resolved=False`, `h3_r8=NULL`, **loại khỏi cung**                                               |
| **B `COORD_ADDR_MISMATCH`** | toạ độ ↔`province_code` lệch (Voronoi: centroid gần nhất là tỉnh **khác** & gần hơn centroid-gốc ≥ `MARGIN=75 km`)                                                | **không rõ trường nào sai** | **ADVISORY** — giữ toạ độ & `h3_r8` & giữ trong cung; **E-DQ3 trọng tài** (point-in-polygon) |

**Tại sao A kết hợp 2 điều kiện (stack **VÀ** xa tỉnh), không chỉ "trùng toạ độ":** một **venue thật**
(mall/sân bay) cũng dồn nhiều trạm về 1 điểm POI **nhưng điểm đó GẦN tỉnh của nó** → **không** flag. Chỉ khi
≥5 trạm vật lý khác nhau dồn về 1 điểm **XA tỉnh của chúng** thì điểm chung mới là **artifact** (nhiều trạm
không thể cùng ngẫu nhiên sai `province_code` giống hệt). Đã kiểm: 35 trạm mã HNO ở điểm HCM **bị bắt**; **10
trạm thật ở Hải Phòng** (gần tỉnh) được **GIỮ** — detector còn tách đúng **per-station** một điểm vừa chứa 10
trạm thật vừa bị 3 trạm placeholder tỉnh khác dồn lên.

**Tại sao B chỉ ADVISORY, không loại:** trên **324 ca lệch > 300 km**, đối chiếu địa chỉ cho thấy toạ độ khớp
**địa chỉ** (⇒ `province_code` prefix mới là lỗi) **92 lần** vs khớp **`province_code`** (⇒ toạ độ mới là lỗi)
**113 lần** — **~50/50**, B **không thể tự quyết** trường nào sai. Loại nhầm ~92+ trạm toạ-độ-đúng khỏi cung
**hại coverage hơn** là bỏ sót. Trọng tài đúng là **E-DQ3** (spatial-join admin polygon trên toạ độ) — nhất
quán cách E-DQ2 **hoãn** `DUP_COORD_SUSPECT` sang E-DQ1.

**Cách xử lý — cây ground-truth toạ độ, FLAG không xoá** (nhất quán P6/P8/E-DQ2), ở
[`fix_coords.py`](../../src/ev_siting/data/evcs/fix_coords.py), chạy **sau** E-DQ2 (nhận sẵn `DUP_COORD_SUSPECT`):

- **Chỉ detector A điều khiển `coord_resolved`.** (1) không placeholder → `coord_src='evcs'`, giữ toạ độ. (2)
  placeholder nhưng official có toạ độ **tốt** (không placeholder, gần centroid-tỉnh) & đổi điểm → snap
  `coord_src='official'` (thực tế VN = **0** vì official mang cùng placeholder; giữ tier theo nguyên tắc
  official-first & phòng hộ). (3) placeholder không cứu được → `coord_resolved=False`, `h3_r8=NULL`, **loại
  khỏi cung** (không neo phủ ở vị trí chưa biết — giống `is_operational`/`is_primary`).
- **Provenance (đảo ngược & geocode tương lai):** `lat_raw`/`lng_raw` (giữ gốc), `coord_src`,
  `coord_fix_dist_m`, `coord_resolved`; **`h3_r8` tính lại** từ toạ độ đã resolve. Cung/coverage/**T0** thêm
  điều kiện `coord_resolved` ([`build_candidates._load_stations`](../../src/ev_siting/features/build_candidates.py)).

**QA gate 5 cổng** (chặn trong `transform_canonical`, FAIL = raise): ① `provenance_complete` (mọi dòng có
`coord_src` + `lat_raw/lng_raw`; đối soát `input=output` giữ nguyên 19.507 dòng) · ② `unresolved_no_h3`
(placeholder ⇒ `h3_r8` NULL) · ③ `no_unfixed_placeholder_in_supply` (`COORD_PLACEHOLDER & coord_resolved`
chỉ hợp lệ khi đã snap official) · ④ `placeholder_labeled` (placeholder → `coord_src ∈ {placeholder, official}`) · ⑤ `h3_consistent` (`h3_r8` khớp toạ độ đã resolve).

**Kết quả** (chạy 28/07, **giữ nguyên 19.507 dòng**): **`COORD_PLACEHOLDER` 38** (35 HNO@HCM + 3 TNG) →
`coord_resolved=False`, `h3_r8=NULL`, loại cung · **`COORD_ADDR_MISMATCH` 758** (advisory, giữ toạ độ →
E-DQ3) · snap official **0** · **214 `DUP_COORD_SUSPECT`** của E-DQ2 được **phân xử**: **38 xác nhận
placeholder** (loại) + **176 minh oan** là venue thật (giữ). Cung công khai khả dụng
(`is_operational & PUBLIC & is_primary & coord_resolved`) = **19.015** (= 19.053 − 38). **Mọi gate PASS.**
Inspect độc lập: `python -m ev_siting.data.evcs.fix_coords --dump` → `fix_coords_{report.json,flagged.csv}`.

**Limitation (`DOC`):**

- **Không geocode street-level** (snapshot đóng băng offline + địa chỉ bẩn E-DQ6): placeholder không cứu được
  bằng official → để `coord_resolved=False` (loại cung) + giữ `lat_raw/lng_raw` để **relocate sau** (commune
  centroid khi E-DQ3 có polygon / geocoder roadmap). **Không đoán** toạ độ giả.
- **`COORD_ADDR_MISMATCH` (758) chưa trọng tài** trong scope E-DQ1 — cố ý hoãn sang **E-DQ3** (point-in-polygon
  là trọng tài đúng); B **không** loại trạm khỏi cung để tránh bỏ nhầm ~50% ca toạ-độ-đúng.
- Detector A dùng `STACK_MIN=5` (khớp E-DQ2) → **bảo thủ**: stack 2–4 `physical_id` cùng điểm **không** bị loại
  (có thể co-located thật); đánh đổi recall lấy an toàn cung. `official`-first bị lật **duy nhất** ở trường toạ
  độ cho charger tư nhân (placeholder upstream) — ghi rõ để không mâu thuẫn P7/P8.

#### E-DQ7a — POI ngoài lãnh thổ VN (bước 4)

`🔴 FIX (chặn) · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán.** `overpass_poi.py` query bằng `VN_BBOX = (8, 102, 23.7, 110)` — hộp này chứa **trọn** Phnom Penh,
Viêng Chăn, Nam Ninh/Sùng Tả (Quảng Tây) và Hải Nam → **20.256/37.362 POI (54,2%) không nằm trong lãnh thổ VN**.
Nặng hơn: cổng QA `poi_coords_in_vn` của [`osm/validate.py`](../src/ev_siting/data/osm/validate.py) kiểm "POI
nằm trong `VN_BBOX`" — **kiểm đúng cái hộp sinh ra lỗi** ⇒ PASS suốt từ đầu. Một cổng chỉ có giá trị khi nó
**có thể FAIL**. `demand_h3` là hàm mục tiêu của MCLP nên đây là poisoning, không phải lỗi cosmetic.

**Ba nguồn rò rỉ, ba hình học khác nhau** (đo trên snapshot `2026-07-20`) — lý do không thể dùng một chính sách chung:

| Nguồn                  | Khối lượng ngoài VN         | Hình học rò rỉ                                                                | Nguyên nhân                                                             |
| ----------------------- | ------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| POI (Overpass)          | 20.256 điểm (**54,2%**) | ~99%**sâu** trong nước bạn (chỉ 195 POI trong vòng 10 km quanh biên) | bbox thô, không clip                                                    |
| `road_len` (`.pbf`) | **8.934 km** (1,2%)       | **96% trong 10 km quanh biên**                                             | Geofabrik cắt bằng polygon**có đệm**, không cắt đúng biên |
| `pop` (WorldPop)      | 6.472 người (0,0065%)         | 100% trong ~2 km quanh biên                                                      | hiệu ứng mép raster                                                    |

> ⚠️ **Sửa nhận định cũ.** [overview.md §7](data-layer/overview.md) từng ghi "`road` lấy từ Geofabrik (**đã clip
> theo quốc gia**)" → **sai**. E-DQ7a vì thế xử lý **cả road**, không chỉ POI.

**Hai quyết định thiết kế (đều đo được, không suy đoán):**

1. **Clip POI ở mức ĐIỂM, phân loại lưới ở mức Ô.** Clip POI theo ô sẽ vừa **giữ** POI nước ngoài (ô có tâm rơi
   vào VN) vừa **xoá** POI VN (ô có tâm rơi ra ngoài). Chỉ điểm mới có lãnh thổ xác định.
2. **Test ô = LỤC GIÁC ∩ POLYGON, không phải TÂM Ô ∈ POLYGON.** Ô res 8 có bán kính nội tiếp 0,49 km nên ô vắt
   biên rơi tâm về bên nào cũng được. Đo thật: test theo **tâm ô** xoá mất **74.642 dân VN thật**; test theo
   **giao lục giác** chỉ xoá **6.472** (0,0065%) — cùng một ranh giới, lệch **11 lần**. Ô vắt biên (`BORDER`)
   **giữ** kèm `frac_in_vn` (tỉ lệ diện tích thuộc VN) để `demand_weight` tự quyết chính sách chia tỉ lệ —
   1.391 ô biên có `frac_in_vn < 0,5` và chứa **69.527 dân**, quá lớn để xử lý ngầm bằng một cờ nhị phân.

**Cách xử lý — polygon trích từ chính `.pbf` đã freeze**, ở [`osm/vn_boundary.py`](../src/ev_siting/data/osm/vn_boundary.py):

- **Nguồn:** relation OSM `admin_level=2` **id 49915** trong `vietnam-latest.osm.pbf` (E-DQ10, `snapshot_id=2026-07-20`)
  → **không thêm nguồn thô mới**, không đụng MANIFEST, tái lập được. **Không** re-crawl Overpass bằng bộ lọc
  `(poly:…)`: polygon 614 way làm query cực nặng, và re-crawl là **phá snapshot** — clip là bước **dẫn xuất**
  trên raw bất biến.
- **Tự ráp ring, không dùng `FileProcessor.with_areas()`.** Đã thử: bộ ráp area của osmium trả về **rỗng** cho
  relation 49915 vì **15/614 way outer bị Geofabrik cắt** ở mép extract → ring không khép, assembler bỏ qua
  **im lặng**. `linemerge` + `polygonize` chịu được khuyết đó. Chính vì chế độ lỗi là "im lặng" nên cổng ④ (neo
  điểm) là **bắt buộc**.
- **Cùng một lượt đọc `.pbf` ráp luôn polygon `admin_level=4`** (**40 tỉnh** phía VN) — đúng artefact **E-DQ3**
  cần để spatial-join admin. Một lượt đọc, hai issue.
- **FLAG không xoá** (nhất quán E-DQ1/E-DQ2): `in_vn` (bool, mức điểm) trên `osm_poi_points.parquet` — dòng ngoài
  VN **được giữ**, chỉ **không được đếm** vào `n_poi`/`n_parking`/`n_fuel`. `cell_state ∈ {INSIDE, BORDER, OUTSIDE}` + `frac_in_vn` trên `demand_h3`; ô `OUTSIDE` tách sang `demand_h3_clipped_out.parquet` để đối soát
  `input = output + clipped`.
- Không đụng độ mịn lưới (vẫn `H3 res 8`) → **không** phá tỷ lệ `R/d` của **P4**.

**QA gate — 6 cổng ở `vn_boundary.py` + 6 cổng ở `build_demand_h3.py`** (đóng E-DQ7a thật, không chỉ "có file
polygon"): ① `boundary_valid` (bắt chế độ lỗi assembler-trả-rỗng) · ② `boundary_area_km2` trong dải
450–560 nghìn km² · ③ `boundary_mainland_share ≥ 0,9` · ④ **`boundary_anchor_points`** — 6 điểm VN phải **trong**,
5 điểm Phnom Penh/Viêng Chăn/Nam Ninh/Ubon/Savannakhet phải **ngoài** (mọi điểm "ngoài" đều nằm **trong**
`VN_BBOX`, tức cổng này test đúng lỗ hổng) · ⑤ `boundary_ways_resolved` (way khuyết ≤ 5%) · ⑥
`provinces_assembled` (E-DQ3). Phía lưới: ⑦ **đối soát `input = output + clipped`** trên cả 6 đại lượng · ⑧
`demand_unique_h3` · ⑨ non-negative · ⑩ `road_mt_le_total` · ⑪ **`clip_pop_loss_negligible < 0,1%`** (clip ăn vào
dân số ⇒ polygon sai hoặc lỡ dùng test tâm-ô) · ⑫ `no_outside_cell_in_grid`. `osm/validate.py` thay cổng
`poi_coords_in_vn` (vô dụng) bằng `counts_match_in_vn_poi` — số đếm phải **bằng đúng** số POI `in_vn`.

**Kết quả** (chạy 28/07 — `make boundary && make osm && make demand`):

| Đại lượng          | Trước    | Sau                  | Ghi chú                                                                                                        |
| ---------------------- | ---------- | -------------------- | --------------------------------------------------------------------------------------------------------------- |
| POI được đếm      | 37.362     | **17.106**     | `n_poi` 19.588→**9.679** · `n_parking` 7.121→**2.463** · `n_fuel` 10.653→**4.964** |
| Ô lưới`demand_h3` | 268.404    | **254.035**    | −7.000 ô "ma" chỉ-có-POI (biến mất ở mức điểm) − 7.369 ô`OUTSIDE`                                 |
| `pop`                | 99,627 M   | **99,621 M**   | mất 6.472 người (**0,0065%**)                                                                          |
| `road_len_m`         | 730.719 km | **721.785 km** | −8.934 km (1,2%)                                                                                               |

Polygon: **506.834 km²**, 4 phần, mainland share 0,977, 15/614 way khuyết (2,4%) — **mọi cổng PASS**.
`buildable_h3` national đã dựng lại trên lưới mới (254.035 ô, 59.768 buildable, gate PASS). Ô `BORDER`: **2.977**
(trung vị `frac_in_vn` 0,54).

**Hiệu ứng phụ đã kiểm chứng — thang `penalty` của P5 từng bị ô nước ngoài định đoạt.** `dist_term` trong
[`build_buildable_h3`](../src/ev_siting/data/landuse/build_buildable_h3.py) chuẩn hoá theo `dmax = max(dist_substation_m)` **trên toàn lưới**; lưới cũ chứa ô sâu trong Campuchia/Lào (rất xa mọi trạm biến áp VN)
nên `dmax` bị thổi phồng ⇒ mọi `penalty` bị nén xuống. Sau clip, candidate Hà Nội **giữ nguyên 1.711 điểm và
nguyên phân bố tier** (T0 1.409 · T4 130 · T1 112 · T2 60, mọi gate PASS) — khác biệt **duy nhất** là `penalty`
nhích lên (vd 0,003 → 0,004), tức thang phạt mềm nay được chuẩn hoá trên lãnh thổ VN thay vì trên ô nước ngoài.

**Kiểm chứng chéo độc lập** (polygon **không** được dựng từ dữ liệu này): chiếu **19.507 trạm canonical** lên
polygon → **19.503 trong VN, 4 ngoài** (0,02%), và cả 4 đều là **lỗi toạ độ có thật** mà **E-DQ1** đã nghi:
`vn-c-hno16032` "xã Bất Bạt, **Hà Nội**" ở `(20.077, 104.771)` = **Lào**; `vn-c-hcm17024` "Xã Hóc Môn, **TP.HCM**"
và `vn-c-hye12380` "**Hưng Yên**" đều rơi sang **Campuchia**; `vn-c-dna10968` "**Đà Nẵng**" rơi ra **vịnh Bắc Bộ**.
⇒ `in_vn` **thăng cấp 4/758 `COORD_ADDR_MISMATCH`** từ advisory lên lỗi xác nhận, và tỉ lệ dương-tính-giả 0,02%
trên tập 19,5k điểm độc lập là bằng chứng polygon đáng tin.

**Limitation (`DOC`):**

- Polygon `admin_level=2` **bao gồm lãnh hải** (506.834 km² so với 331.212 km² đất liền) → mask **rộng có chủ
  đích**: không bao giờ xoá nhầm POI ven biển/hải đảo, nhưng cũng **không** đánh dấu ô ngoài khơi là "không phải
  đất". Lọc đất/nước là việc của WorldCover trong **P5** (`buildable_h3`) — **không gộp hai khái niệm**.
- Mask kế thừa cách OSM thể hiện các vùng biển tranh chấp (relation có ring Hoàng Sa/Trường Sa) → phải mô tả là
  "OSM `admin_level=2` tại snapshot `2026-07-20`", **không** phải tuyên bố chủ quyền chính thức.
- Ô `BORDER` hiện **giữ nguyên giá trị `pop`/`road_len`** (chưa chia tỉ lệ theo `frac_in_vn`) — cố ý hoãn sang
  bước `demand_weight` để chính sách chia tỉ lệ nằm cùng chỗ với công thức trọng số.
- `.pbf` snapshot chứa **cả đơn vị hành chính sau sáp nhập 2025 lẫn bản "cũ"** (`Tỉnh Lào Cai` **và** `Tỉnh Lào Cai cũ`, tương tự Quảng Trị / An Giang) → 40 polygon adm4 cần **quy tắc phân định** trước khi dùng cho
  **E-DQ3**; E-DQ7a chỉ dùng adm2 nên không bị ảnh hưởng.

#### E-DQ7b — `road_len` sai ngữ nghĩa (bước 5)

`🟠 FIX · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán — ba triệu chứng, một lỗi thiết kế.** Register tách 3 triệu chứng (`track`+`service` tính là đường
sinh cầu · double-count 2 chiều · `_MAJOR` gộp 3 cấp), nhưng gốc chung là: **`road_len_m` phải phục vụ hai định
nghĩa mâu thuẫn cùng lúc**.

- [`build_buildable_h3.py`](../src/ev_siting/data/landuse/build_buildable_h3.py) dùng `road_len_m <= 0` làm bộ
  lọc **cứng** `NO_ROAD_ACCESS` → cần định nghĩa **rộng**: đường đất vẫn là lối vào.
- Proxy cầu cần định nghĩa **hẹp**: đường mòn không sinh nhu cầu sạc.

Vì vậy "bỏ `track`+`service`" chỉ đúng một nửa, và nửa sai thì đắt. Đo trên lưới hiện tại: bỏ chúng khỏi **một
cột duy nhất** đẩy số ô `road=0` từ **6.350 → 34.178** (+27.828); trong đó **2.474 ô chứa 850.207 dân** và **36 ô
chứa 145 trạm sạc đang vận hành** — tức bộ lọc khả thi sẽ loại đúng những chỗ đã **chứng minh** là xây được.

**Thành phần `road_len_m` đo trên `.pbf` đã freeze** (tổng 730.718,5 km — khớp bit-level bảng cũ):

| Lớp                                |      km |     % |      `oneway` | `lanes` có tag |     Ô | `pop` trung vị/ô |
| ----------------------------------- | ------: | ----: | --------------: | ----------------: | -----: | -------------------: |
| LOCAL (residential/unclassified/…) | 449.236 | 61,5% |            0,7% |              0,6% |     — |                   — |
| **TRACK**                     |  74.487 | 10,2% |            0,0% |             0,03% |     — |                   — |
| **SERVICE**                   |  70.667 |  9,7% |            1,2% |              0,3% |     — |                   — |
| TERTIARY                            |  57.252 |  7,8% |            6,2% |              5,6% |     — |                   — |
| SECONDARY                           |  30.842 |  4,2% |           16,4% |             17,4% | 33.339 |                  216 |
| TRUNK                               |  23.511 |  3,2% |           31,2% |             50,4% | 22.554 |                  312 |
| PRIMARY                             |  17.660 |  2,4% |           31,7% |             40,6% | 17.673 |                  374 |
| MOTORWAY                            |   7.004 |  1,0% | **96,9%** |             97,4% |  4.165 |         **73** |

**Bốn quyết định thiết kế (đều đo được):**

1. **R1 — tách TRÍCH XUẤT khỏi CHÍNH SÁCH.** `_EXCLUDE`/`_MAJOR` nằm ngay trong vòng lặp stream: đổi định nghĩa
   "đường" = stream lại 325 MB (~7 phút) và **không hoàn tác được** vì bảng ra chỉ còn 2 số. Nay
   [`roads_pbf.py`](../src/ev_siting/data/osm/roads_pbf.py) ghi **km + lane-mét + lane-mét-có-tag của TỪNG LỚP**
   cho mỗi ô; mọi cột vô hướng do `road_semantics.derive()` suy ra ⇒ đổi chính sách = tính lại **vài giây**.
2. **R2 — hai cột, hai nhiệm vụ.** `road_access_m` (mọi đường lái xe được, **gồm** `service`+`track`) cho **lối
   vào**; `road_len_m` (**trừ** chúng) cho **cầu**. `road_access_m` **bằng đúng** `road_len_m` cũ ⇒ chuyển
   `buildable_h3` sang cột mới là đổi 1 dòng, **không lệch hành vi** (xác nhận: 59.768 buildable · 6.350
   `NO_ROAD_ACCESS`, y hệt trước). 27.828 ô chỉ-có-`service`/`track` thành **cờ phạt mềm**
   `ROAD_ACCESS_INFORMAL`, không phải xoá ngầm.
3. **R3 — sửa double-count bằng lane-mét, KHÔNG nhân 0,5.** Đường đôi có dải phân cách vẽ thành 2 way một chiều
   ⇒ 1 hành lang tính 2 lần, còn đường 4 làn không phân cách chỉ tính 1 lần: `road_len` **không** tỉ lệ với năng
   lực thông hành. Nhân 0,5 cho mọi way `oneway` là **sai** — 3.028 km `oneway` thuộc LOCAL là cặp phố một chiều
   thật (và cách này cắt `_MAJOR` tới **20,5%**: 48.176 → 38.312 km). Lane-mét xử lý tận gốc và là số **đo
   được** đúng ở nơi cần: `lanes` có tag ở **97,4% motorway · 50,4% trunk · 40,6% primary** nhưng chỉ **0,6%
   residential** ⇒ chỉ dùng lane-mét cho trục lớn, giữ km tim đường cho lớp địa phương.
4. **R4 — tách `_MAJOR`, khai tử `road_len_mt_m`.** Trên ô có `_MAJOR>0`: ρ_Spearman(`road_len_mt_m`, motorway)
   = **0,31** còn với trunk+primary = **0,70** — cột cũ thực chất là "trục đô thị", tín hiệu cao tốc bị chìm
   (motorway chỉ 14,8% km `_MAJOR`). Hai lớp gần như không chồng lấn (3.311 ô chỉ-motorway vs 37.574 ô
   chỉ-trunk/primary) và ngữ nghĩa ngược nhau: ô motorway `pop` trung vị **73** (liên tỉnh, dừng lâu, DC công
   suất cao) vs trunk/primary **312–374** (trục đô thị). **Đổi tên thay vì đổi nghĩa ngầm** để consumer cũ gãy
   to — cùng nguyên tắc với cổng `poi_has_in_vn_flag` của E-DQ7a.

**Schema sau E-DQ7b** (`osm_roads_h3.parquet` giữ 28 cột lớp; `demand_h3` giữ 5 cột suy ra):

| Cột                   | Định nghĩa                                             | Consumer                                |
| ---------------------- | --------------------------------------------------------- | --------------------------------------- |
| `road_access_m`      | mọi đường lái xe được (gồm`service`+`track`) | `access_tier` (E-DQ8a) → `buildable_h3` |
| `road_len_m`         | mạng lái xe**trừ** `service`+`track`         | proxy cầu                              |
| `road_lane_mw_m`     | lane-mét cao tốc                                        | hành lang liên tỉnh                  |
| `road_lane_ar_m`     | lane-mét`trunk`+`primary`                            | trục đô thị                         |
| `road_bridge_m`      | km cầu/hầm (**tập con** của `road_access_m`)  | P5 — không đặt trụ trên mặt cầu |
| ~~`road_len_mt_m`~~ | **khai tử**                                        | —                                      |

**Kết quả** (chạy 28/07 — `roads_pbf && make osm && make demand && landuse-national && candidates`):

| Đại lượng          | Trước          | Sau                        | Ghi chú                                                            |
| ---------------------- | ---------------- | -------------------------- | ------------------------------------------------------------------- |
| `road_access_m`      | —               | **721.785 km**       | =`road_len_m` cũ **chính xác** ⇒ lối vào không đổi |
| `road_len_m`         | 721.785 km       | **578.473 km**       | −143.311 km (`service`+`track`)                                |
| `road_len_mt_m`      | 46.824 km        | **khai tử**         | →`road_lane_mw_m` 13.849 km + `road_lane_ar_m` 82.484 km       |
| `road_bridge_m`      | —               | **4.345 km**         | mới; 50 ô có đường duy nhất là mặt cầu                    |
| Ô`NO_ROAD_ACCESS`   | 6.350            | **6.350**            | không đổi (đúng thiết kế R2)                                 |
| `buildable` national | 59.768           | **59.768**           | không đổi                                                        |
| Candidate Hà Nội     | 1.711 (5/5 gate) | **1.711 (5/5 gate)** | T0 1.409 · T4 130 · T1 112 · T2 60                               |

**QA gate — 6 cổng mới ở [`osm/validate.py`](../src/ev_siting/data/osm/validate.py) + 2 ở `build_demand_h3.py`.**
Cổng cũ `road_mt_le_total` bị gỡ vì **vô dụng**: `_MAJOR ⊂` mọi đường là đúng theo *xây dựng* nên nó không bao
giờ FAIL được — cùng lỗi thiết kế với `poi_coords_in_vn` của E-DQ7a. Thay bằng cổng **có thể FAIL**:
① `roads_h3_has_tier_columns` (chặn artefact cũ) · ② **`road_tiers_sum_eq_access`** — đối soát Σ lớp, bắt lệch
nhãn cột · ③ `road_len_le_access` + `road_bridge_le_access` · ④ `road_lane_invariants` (`lane_m ≥ m` vì mọi way
≥1 làn; `lane_obs_m ≤ lane_m`) · ⑤ **`major_lane_observed_share ≥ 0,40`** — nếu lane-mét trục lớn chủ yếu là số
**suy đoán** thì feature hết là số đo (thực đo: **59,4%**) · ⑥ **`supply_cells_have_road_access`** — cổng
**ngoại vi** duy nhất của tầng đường: ô chứa trạm sạc đang vận hành phải có đường (WARN >1%, FAIL >2%).

> ⚠️ **Cổng ② và ④ đã bắt lỗi thật ngay trong lúc dựng.** Bản đầu ghi accumulator theo thứ tự xen kẽ nhưng đặt
> tên cột theo thứ tự gộp ⇒ **lệch nhãn toàn bộ bảng lớp**: số vẫn không âm và vẫn cộng ra tổng "đẹp", nhưng
> `road_access_m` ra **205.936 km** thay vì 730.718 km và `lanes có tag` ra **229%**. Nay chỉ số slot tra thẳng
> từ `TIER_COLUMNS.index(...)` nên hai bên không thể lệch, kèm test khoá layout
> ([`tests/test_road_semantics.py`](../tests/test_road_semantics.py)).

**Phát hiện phụ (không có trong register):**

- **`service` không tách được theo subtype ở VN:** **86%** (61.032/70.667 km) **không** có tag `service=*`;
  `parking_aisle` chỉ **214 km**. ⇒ phương án "giữ lối đi bãi đỗ, bỏ lối vào nhà" **không khả thi** — phải xử lý
  `service` như một khối. Ghi lại để không ai đề xuất lại.
- **`track` 74,6% `unpaved` rõ ràng** (55.576 km) — vừa xác nhận loại khỏi cầu, vừa xác nhận **vẫn là** lối vào.
- **4.178 km cầu + 203 km hầm.** Ô mà đường duy nhất là mặt cầu vẫn đang lọt bộ lọc lối vào → thêm
  `road_bridge_m` + cờ mềm `ROAD_BRIDGE_ONLY` (**50 ô**).
- **`highway=services`/`rest_area`: 91 đối tượng, 49 km.** Trạm dừng nghỉ cao tốc là vị trí sạc hạng nhất nhưng
  đang bị đếm như đường thường → **ứng viên T3** cho P5 (hiện `build_candidates.py` ghi "để roadmap").
- **108 trạm đang vận hành nằm ở ô OSM không có bất kỳ đường nào** (100 ô, 0,78% ô có trạm) — hoặc OSM thiếu
  đường, hoặc toạ độ còn sai sau E-DQ1. Đây chính là cổng ⑥ ở trên, và là đầu vào cho **E-DQ7d**.

**Hệ quả thứ tự — ràng buộc "7b trước 8" đã tan.** [§ thứ tự](#e-data-quality--cleaning-từ-data-layer-overviewmd-7) lập luận E-DQ8 phải đo sau 7b vì bỏ
`track`+`service` làm **tăng** số ô `road=0`. Điều đó chỉ đúng với phương án **một cột**. Với R2, E-DQ8 đo trên
`road_access_m` (một xóm chỉ có đường mòn **vẫn có** đường) nên con số **đứng yên: 6.350 ô / 1.268.026 dân** —
đúng bằng giá trị sau E-DQ7a. Nói cách khác, lý do "phải làm 7b trước" chính là bằng chứng phương án một cột
sai. E-DQ8 nay **đo được ngay**, và có thêm hai tập con để phân loại: 27.828 ô lối vào phi chính thức (850.207
dân) và 100 ô có trạm thật nhưng không có đường.

> ✅ **Chốt 30/07.** Hai tập con ấy đã thành hai dòng register riêng: `road_access_m` được **giữ nguyên** làm nguồn, nhưng câu hỏi "có lối vào không?" nay đo ở thang **lân cận** (`access_tier`, [E-DQ8a](#e-dq8a--lối-vào-đo-ở-thang-sai-bước-10)) và khối lượng dân ở ô không lối vào đã được **dời** ([E-DQ8b](#e-dq8b--dời-dân-ở-ô-không-có-lối-vào-bước-10b)). 27.828 ô `ROAD_ACCESS_INFORMAL` vẫn đúng như R2 định — và cờ đó **nay mới thật sự có trọng số** trong `penalty` (trước 30/07 nó được phát ra nhưng công thức bỏ qua).

**Limitation (`DOC`):**

- **Lane-mét ở lớp địa phương là số suy đoán** (mặc định 1 làn nếu một chiều, 2 nếu hai chiều) vì `lanes` chỉ
  có ở 0,6% `residential` → **không** dùng `lane_m_LOCAL` làm feature; cổng ⑤ chỉ canh lớp trục lớn.
- **`oneway` không đồng nghĩa đường đôi.** Lane-mét né được vấn đề này (đếm làn, không đếm hành lang) nhưng nếu
  sau này cần **số hành lang**, phải ghép cặp way song song bằng hình học — chưa làm.
- **`motorway` của OSM ở VN rộng hơn "cao tốc" chính thức**: 7.004 km tim đường (3.612 km nếu nhân đôi-halve) so
  với ~2.000+ km cao tốc đang khai thác, vì OSM gắn `motorway` cho cả đường trên cao đô thị/vành đai. Vì vậy
  **không** đặt cổng cứng theo số liệu chính thức — muốn dùng phải chốt nguồn chính thức và freeze vào
  `data/external/` trước.
- **Trọng số gap-fill T4 vẫn đặt tay** (`0,025·road_lane_ar_m + 0,05·road_lane_mw_m`, cao tốc nặng gấp đôi vì ô
  cao tốc `pop` trung vị chỉ 73 nên vô hình trong hạng `pop`) — **E-DQ7d/P1** sẽ hiệu chuẩn bằng 18,6M bản ghi
  occupancy.

#### E-DQ7c — POI thiếu & lẫn đơn vị (bước 6)

`🟠 FIX + DOC · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán — register ghi 3 triệu chứng, đo được 5, và số thứ ba không tái lập.** Audit trên artefact sau
E-DQ7a (17.106 POI `in_vn`) cho kết quả:

| # | Triệu chứng                                                                         | Đo được                                                                                                                                                                                                                                                  |
| - | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1 | `n_poi` lẫn đơn vị 1:1                                                          | apartments**53,5%** · retail **32,1%** · mall **14,5%**; ở **top-100 ô theo `n_poi`, 84,8% số đếm là apartments**                                                                                                          |
| 2 | **Lẫn đơn vị BÊN TRONG từng nhóm crawl** *(không có trong register)* | `retail` = **1.698 chợ** (`marketplace`) + **1.409 siêu thị**; `mall` = **1.137 `department_store`** + 262 `shop=mall`; `parking` = 376 surface / **146 street_side** / 93 underground / 42 multi-storey / 20 lane    |
| 3 | 1 khu chung cư = N toà = N POI*(không có trong register)*                         | **60,8%** polygon chung cư nằm trong cụm ≥5 thành viên trong 200 m; tên lặp nhiều nhất đúng là `block b` · `lô a` · `ct1` · `a2`                                                                                              |
| 4 | POI thiếu                                                                            | recall**fuel 35,9%** · **parking 8,6%** (đo ngoại vi — xem dưới)                                                                                                                                                                           |
| 5 | 496 trùng node/way                                                                   | **không tái lập được**: đo lại được **259** @30 m · **311** @50 m · **427** @100 m (`in_vn`), 438 @50 m chưa clip. Con số chốt của bản vá là **335** bản trùng (254 trong VN) theo định nghĩa ở C3 |

Cộng thêm **hai lỗi thiết kế** không phải triệu chứng dữ liệu:

- **Cổng `poi_no_dup` không bao giờ FAIL được — ca thứ BA của cùng một lỗi.** Nó kiểm
  `duplicated(["osm_type","osm_id","category"])` trong khi `build_osm_h3` gọi `drop_duplicates` trên **đúng ba
  khoá đó** ngay dòng trước khi ghi file. Nó PASS trên một hằng đúng suốt từ đầu trong khi 335 bản trùng node/way
  đi qua. Tệ hơn: khoá **có** `category` nên nó *cố ý cho phép* một đối tượng OSM được đếm hai lần nếu lọt vào hai
  nhóm crawl — đo được **13 đối tượng** (8 `in_vn`), trong đó **4/5 tổ hợp cùng dồn vào `n_poi`**. Cùng chế độ
  lỗi với `poi_coords_in_vn` (E-DQ7a) và `road_mt_le_total` (E-DQ7b).
- **Provenance POI sai trong MANIFEST.** POI lấy từ **Overpass API trực tiếp** (21/07) nhưng nằm dưới nguồn `osm`
  mang `vintage = replication_timestamp` của `.pbf` (`2026-07-20T20:21:16Z`). Bytes thì đã freeze, nhưng **dẫn
  xuất thì không tái lập được**: chạy lại `overpass_poi.py` hôm nay ra dữ liệu khác. Road và boundary đều lấy từ
  `.pbf` đã freeze — POI là tầng OSM **duy nhất** không lấy.

**Đo độ phủ bằng nguồn ĐỘC LẬP, không bằng số liệu chính thức.** Register ghi "OSM chỉ phủ ~30% cây xăng" —
số ngoại lai (~17.000 cửa hàng bán lẻ). E-DQ7b đã chốt nguyên tắc **không đặt cổng theo số liệu chính thức chưa
freeze** (xem limitation `motorway`), và MOIT chỉ công bố **thương nhân đầu mối/phân phối**, không công bố danh
sách cửa hàng bán lẻ **có toạ độ**. Thay vào đó dùng dữ liệu đã có: trong 19.015 trạm cung, **1.408 trạm** có
`name`/`address` nêu đích danh một cây xăng và **845 trạm** nêu một bãi đỗ ⇒ mỗi trạm là **bằng chứng thực địa**
rằng ở đó có cây xăng/bãi đỗ. Hỏi ngược OSM:

| Lớp            | n đối chiếu |   recall @100 m | @200 m | @300 m | **tỉ số thiên lệch** (pop cao / pop thấp) |
| --------------- | -------------: | --------------: | -----: | -----: | ---------------------------------------------------: |
| `FUEL`        |          1.408 | **35,9%** |  36,9% |  37,6% |                    **1,12** — gần như ĐỀU |
| `PARKING_OFF` |            845 |  **8,6%** |  10,7% |  13,4% |              **2,67** — lệch đô thị nặng |

Recall gần như không đổi khi nới bán kính ⇒ **thiếu POI thật**, không phải dung sai khoảng cách. Con số fuel xác
nhận "~30%" bằng đường độc lập; **con số parking là phát hiện mới** — `n_parking` tệ hơn `n_fuel` khoảng **4 lần**.

> **Cái đáng lo là THIÊN LỆCH, không phải độ phủ tuyệt đối.** Với một covariate *tương đối*, thiếu **đều** 64% chỉ
> là hằng số tỉ lệ — vô hại. Fuel thiếu đều (1,12) ⇒ lỗ hổng lành tính. Parking thiếu **lệch theo mật độ dân**
> (2,67) ⇒ `n_parking_off` là feature **độ tin thấp**, E-DQ7d phải biết trước khi fit.

**Bảy quyết định thiết kế (đều đo được):**

1. **C1 — tách TRÍCH XUẤT khỏi CHÍNH SÁCH** (nguyên tắc R1 của E-DQ7b, áp cho POI). `_COUNT_COL` cũ gộp 5 nhóm
   crawl thành 3 vô hướng **ngay trong hàm gộp**. Nay `build_osm_h3.py` ghi **bảng lớp** `osm_poi_h3.parquet`
   (một cột/lớp tag) và mọi cột vô hướng do [`poi_semantics.derive()`](../src/ev_siting/data/osm/poi_semantics.py)
   suy ra ⇒ đổi chính sách = tính lại **vài giây**, không phải crawl lại Overpass. `tags` vẫn nằm trong raw JSON
   nên **không cần re-crawl** để phân lớp lại — cũng là lý do không phải phá snapshot.
2. **C2 — `n_poi` và `n_parking` KHAI TỬ, đổi tên thay vì đổi nghĩa ngầm.** Consumer đọc `n_poi` hôm nay đang đọc
   "mật độ toà chung cư ở HN/HCM". Cùng nguyên tắc `road_len_mt_m` của E-DQ7b: phải gãy to.
3. **C3 — KHÔNG chọn trọng số ở bước này.** Cám dỗ là gán `mall=5, retail=2, apartments=1`. Đo thật: đổi bộ trọng
   số **hoán đổi 147–254 trong top-500 ô** ⇒ đây là quyết định mô hình có hậu quả, mà **E-DQ7d/P1 có 18,6M bản
   ghi occupancy để *fit*** nó. Việc của 7c là **giao ra các cột tách rời fit được**.
   *(Lưu ý đo đạc: ρ_Spearman **vô dụng** ở đây — 98,8% ô bằng 0 nên ρ = 1,000 cho cả những bộ trọng số đảo lộn
   1/3 top-500. Dùng **top-K overlap**.)*
4. **C4 — khử trùng là PHÂN GIẢI DANH TÍNH, không phải xoá.** Tái dùng khuôn E-DQ2: `poi_physical_id` +
   `is_poi_primary`, **giữ mọi dòng**. Chỉ ghép cặp **khác kiểu hình học** (node ↔ way/relation) cùng lớp trong
   **30 m** — hai node gần nhau / hai polygon liền kề là **hai đối tượng thật**. Chọn 30 m vì từ 30→100 m số cặp
   `parking` nhảy 36→84 và phần tăng chủ yếu là bãi đỗ liền kề có thật (đổi recall lấy an toàn, cùng đánh đổi với
   `STACK_MIN=5` của E-DQ1). Bản chính là **area** (mang hình học), node là bản mô tả điểm.
5. **C5 — một đối tượng OSM = MỘT lớp.** `CLASS_PRIORITY`: venue thắng vỏ nhà (toà vừa `shop=mall` vừa
   `building=apartments` là **một** TTTM). Đóng đúng lỗ hổng mà khoá cũ cố ý để mở.
6. **C6 — gộp toà chung cư về KHU trước khi cân theo quy mô.** Đơn liên kết 150 m: **5.157 toà → 1.370 khu**
   (hệ số **3,76×**). Khu gán theo **trọng tâm** khu, không theo từng toà — một khu vắt qua 2 ô mà đếm ở cả hai
   thì lại nhân đôi đúng cái vừa gộp.
7. **C7 — kích thước ở đâu ĐO được thì ghi.** `building:levels` có ở **36,1%** toà (trung vị 18 tầng) →
   `apartment_levels_sum` là số **đo**, ô không có tag để **0**, **không nội suy**. Ngược lại `building:flats`
   chỉ 6% và **`capacity` của bãi đỗ chỉ 1,3% (55/2.463)** ⇒ **`capacity` không dùng được** — ghi lại để không ai
   đề xuất lại (cùng kiểu ghi chú với `service` subtype 86% khuyết của E-DQ7b).

**Schema sau E-DQ7c** (`osm_poi_h3.parquet` giữ 19 cột lớp; `demand_h3` giữ 10 cột suy ra):

| Cột                                 | Định nghĩa                                                        | Ghi chú                                                                             |
| ------------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `n_fuel`                           | `amenity=fuel`                                                     | ngữ nghĩa**không đổi**, chỉ thêm khử trùng (4.964 → **4.830**) |
| `n_parking_off`                    | bãi đỗ ngoài lòng đường,**trừ** `access=RESTRICTED` | **2.147**                                                                      |
| `n_parking_street`                 | đỗ ven đường/lòng đường                                     | **149** — tách ra vì **không đặt được trụ**                    |
| `n_mall`                           | `shop=mall`                                                        | **252**                                                                        |
| `n_dept_store`                     | `shop=department_store`                                            | **1.133**                                                                      |
| `n_supermarket`                    | `shop=supermarket`                                                 | **1.386**                                                                      |
| `n_market`                         | `amenity=marketplace` (chợ)                                       | **1.661**                                                                      |
| `n_apartment`                      | toà chung cư                                                       | **5.157**                                                                      |
| `n_apartment_complex`              | **khu** chung cư (gộp 150 m)                                 | **1.370** ⟵ đơn vị đúng để sánh với `n_mall`                       |
| `apartment_levels_sum`             | Σ`building:levels` quan sát được                              | **34.691** (36,1% toà có tag)                                                |
| ~~`n_poi`~~ · ~~`n_parking`~~ | **khai tử**                                                   | —                                                                                   |

**QA gate — bỏ 1 cổng vô dụng, thêm 8 cổng có thể FAIL** ở
[`osm/validate.py`](../src/ev_siting/data/osm/validate.py): ① `poi_points_has_class_columns` (chặn artefact cũ) ·
② **`poi_object_once`** — một đối tượng OSM = một dòng (khoá cũ có `category` nên cho phép 2) ·
③ **`poi_dup_resolved`** — đối soát `bản chính + bản trùng = tổng dòng`, không bản trùng nào mồ côi ·
④ `apartment_levels_observed_share ≥ 0,25` (proxy quy mô phải là số **đo**; thực đo **36,1%**) ·
⑤ **`poi_layer_sum_eq_points`** — Σ bảng lớp = số bản chính `in_vn` theo lớp (bắt **lệch nhãn cột**, đúng vai cổng
② của E-DQ7b) · ⑥ **`poi_complex_sum_eq_groups`** — Σ khu trên lưới = số `complex_id` phân biệt (ai đổi sang đếm
theo toà là FAIL ngay) · ⑦ `components_has_poi_columns` (chặn artefact còn `n_poi`/`n_parking`) ·
⑧ **`poi_recall_fuel ≥ 0,30`** và ⑨ **`poi_recall_bias_* ≤ 2,0`** — hai **cổng ngoại vi** duy nhất của tầng POI.
`counts_match_in_vn_poi` viết lại theo lớp + trừ RESTRICTED.

**Kết quả** (chạy 28/07 — `make osm && make demand && make candidates CITY=hanoi`):

| Đại lượng                         | Trước          | Sau                        | Ghi chú                                                                                                         |
| ------------------------------------- | ---------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `n_poi`                             | 9.679            | **khai tử**         | →`n_mall` 252 + `n_dept_store` 1.133 + `n_supermarket` 1.386 + `n_market` 1.661 + `n_apartment` 5.157 |
| `n_parking`                         | 2.463            | **khai tử**         | →`n_parking_off` 2.147 + `n_parking_street` 149 (−34 trùng, −133 RESTRICTED)                             |
| `n_fuel`                            | 4.964            | **4.830**            | −134 bản trùng node/way                                                                                       |
| Toà chung cư →**khu**        | 5.157            | **1.370**            | hệ số**3,76×** — đơn vị mới sánh được với `n_mall`                                          |
| Ô lưới`demand_h3`                | 254.035          | **254.035**          | không đổi (E-DQ7a/7b giữ nguyên bit-level)                                                                  |
| `pop` · `road_access_m` · E-DQ8 | —               | **không xê dịch** | 99,621 M · 721.785 km · 6.350 ô *(số dân của dòng này là tiền-7e; xem [E-DQ8a](#e-dq8a--lối-vào-đo-ở-thang-sai-bước-10) cho 1.241.833)* |
| Candidate Hà Nội                    | 1.711 (5/5 gate) | **1.707 (5/5 gate)** | T0 1.409 · T4 130 · T1**108** · T2 60                                                                   |

**Mọi cổng PASS**, đúng **một WARN có chủ đích**: `poi_recall_bias_parking_off = 2,665` — cổng đang làm đúng
việc của nó (báo rằng `n_parking_off` lệch đô thị, không phải báo pipeline hỏng).

**Hiệu ứng phụ đã kiểm chứng — 4 candidate Hà Nội biến mất, và cả 4 đều đúng.** T1 đi từ 112 → 108: bãi đỗ
`access=private/employees/permit` không còn làm anchor (T1 không phải chỗ sạc công cộng), và bản node/way trùng
của cùng một cây xăng không còn thành hai anchor. T2 **giữ nguyên 60** nhưng thành phần thì đọc được hẳn:
trước là `mall 3 / retail 30 / apartments 27`, nay là `market 21 · apartment 20 · supermarket 14 · dept_store 5`
— cùng một tập điểm, nhưng nay biết **21 cái là chợ truyền thống**, thứ mà thang cầu sạc ô tô phải đối xử khác
siêu thị.

**Phát hiện phụ (không có trong register):**

- **Recall parking (8,6%) tệ hơn fuel (35,9%) khoảng 4 lần** *và* lệch đô thị (2,67 vs 1,12). Register chỉ nói về
  cây xăng; hoá ra tầng POI yếu nhất lại là tầng `parking`, mà nó vừa là covariate vừa là **anchor T1**.
- **80% bãi đỗ không có tag `access`** ⇒ UNKNOWN là đa số và **được giữ** (loại ngầm cái không biết chính là lỗi
  P8 đã sửa cho `evcs`). Chỉ **133** POI bị trừ vì `RESTRICTED` tường minh.
- **`shop=department_store` áp đảo `shop=mall` 4,5:1** ở VN (1.137 vs 262) — nhóm crawl `mall` thực chất là
  "cửa hàng bách hoá", không phải "trung tâm thương mại". Gộp hai thứ này 1:1 là lỗi cùng loại với `n_poi`, chỉ
  nhỏ hơn một bậc.
- **8 POI `in_vn` từng được đếm hai lần** (13 toàn cầu) vì nằm ở hai nhóm crawl.

**Limitation (`DOC`):**

- **Không thêm nguồn POI mới trong scope này.** Overture Maps (CDLA-Permissive 2.0, ~61M POI, release **có version**
  — hợp E-DQ10 hơn hẳn `latest`) và Foursquare OS Places (Apache 2.0, ~104M POI) đều freeze được và **độc lập với
  OSM** nên dùng làm nguồn đối chiếu thì tốt. **Google Maps thì không**: ToS chỉ cho lưu `place_id` vĩnh viễn và
  toạ độ **30 ngày**, đồng thời cấm tạo dataset dẫn xuất — một snapshot có checksum commit vào MANIFEST **chính là**
  dataset dẫn xuất, tức E-DQ10 và ToS của Google **không tương thích về cấu trúc**, không phải về giá. Nếu thay
  tầng POI thì phải làm **trước E-DQ7d** (xem [§ thứ tự](#e-data-quality--cleaning-từ-data-layer-overviewmd-7)).
- **Không nguồn nào không thiên lệch.** Overture/FSQ suy từ POI thương mại nên **cũng** lệch đô thị, có khi hơn OSM
  ở nông thôn VN. Vì vậy doctrine giữ nguyên bất kể nguồn: **không bao giờ lọc cứng theo việc VẮNG POI**, và
  **T4 gap-fill vẫn bắt buộc** — đây chính là biện minh định lượng cho câu "OSM thưa ở vùng ven" ở
  [`build_candidates.py`](../src/ev_siting/features/build_candidates.py).
- **Recall KHÔNG được nhân/chia vào feature.** Nó suy ra từ vị trí **cung** (trạm sạc), còn feature thì để dự đoán
  **cầu** ⇒ hiệu chỉnh bằng nó là **rò rỉ mục tiêu**, và E-DQ7d khi hiệu chuẩn với occupancy sẽ đo lại chính cái rò
  rỉ đó. Recall chỉ dùng để **mô tả** thiên lệch.
- **Recall không đo được theo từng ô** — và đó là *thiết kế*, không phải giới hạn kỹ thuật. 1.408 điểm đối chiếu
  nằm trên ~1.200 ô trong **254.035** ô ⇒ >99% ô mẫu rỗng; ô có 1–2 điểm chỉ cho ra 0%/100% (nhiễu thuần). Vì vậy
  recall phân **tầng** (tam phân vị `pop`), và cổng canh **tỉ số giữa tầng**, không canh mức tuyệt đối.
- **Ngưỡng 150 m của khu chung cư là tham số đặt tay.** Chọn theo quan sát "60,8% toà nằm trong cụm ≥5 ở 200 m";
  chưa kiểm chứng ngoại vi (không có danh sách khu đô thị có toạ độ để đối chiếu). Đổi ngưỡng = chạy lại vài giây
  nhờ C1, và cổng ⑥ sẽ bắt nếu ai đó đổi cách đếm.
- **Tên POI không dùng làm bằng chứng khử trùng.** 45% cây xăng và 88% bãi đỗ **không có `name`**, và trong 141 cặp
  ứng viên ở 50 m chỉ 51 cặp trùng tên ⇒ quyết định phải dựa vào **khoảng cách + lớp**. Đây là lý do ngưỡng phải
  chặt (30 m) thay vì dựa vào tên để nới.
- **Provenance POI vẫn là Overpass trực tiếp.** Bản vá này **không** dựng lại POI từ `.pbf` đã freeze — đó là việc
  riêng (được cả tái lập lẫn **diện tích polygon**, thứ mà `building:levels` ở 36% chỉ xấp xỉ được). Ghi vào
  roadmap; rủi ro đã biết: `with_areas()` của osmium trả **rỗng im lặng** (E-DQ7a) nên phải tự tính diện tích
  bằng shoelace trên toạ độ node.

#### E-DQ7e — `pop` chưa hiệu chuẩn tuyệt đối (bước 8)

`🟡 FIX + DOC · ☑ chốt 2026-07-29 · Owner: Giang`

> **Tách đôi (29/07).** Dòng register cũ "`pop` chưa hiệu chuẩn" gộp **hai khuyết tật độc lập về cả nguyên nhân,
> hậu quả lẫn cách sửa**: một phép **rescale toàn quốc** (mức tuyệt đối sai, thứ hạng đúng) và một lỗi **phân bổ
> trong ô** (mức tuyệt đối quốc gia đúng, thứ hạng sai). Gộp chúng buộc phải chọn một mức độ ưu tiên duy nhất cho
> hai thứ khác hẳn nhau, và — nghiêm trọng hơn — làm cờ `POP_DENSITY_OUTLIER` được thiết kế cho vế thứ hai lại
> **đo bằng đại lượng của vế thứ nhất**. Vế phân bổ nay là **[E-DQ7f](#e-dq7f--pop-phân-bổ-sai-chỗ-trong-ô-dasymetric-spike-bước-9)**.

**Chẩn đoán.** [`paths.py`](../src/ev_siting/data/worldpop/paths.py) trỏ vào `vnm_ppp_2020_constrained.tif` —
bản **UN-unadjusted**. WorldPop phát hành song song bản `vnm_ppp_2020_UNadj_constrained.tif` neo tổng dân số
về UN WPP. Chênh lệch không phải chuyện làm tròn: mọi phát biểu **tuyệt đối** của dự án (`coverage_pop` "X% dân
được phủ", đối chiếu GSO ở **P10**) đều thừa hưởng sai số này.

**Đã tải bản UNadj về và differ từng pixel** (cùng lưới, `transform` trùng khít — kiểm tra được, không suy đoán):

| Đại lượng                                 | Giá trị                                            |
| --------------------------------------------- | ---------------------------------------------------- |
| tổng bản unadjusted (đang dùng)           | **99,627 M**                                   |
| tổng bản UNadj                              | **97,569 M**                                   |
| chênh lệch                                  | **+2,11%** (+2,058 M)                          |
| tỉ số UNadj/unadj theo**từng pixel** | min = p1 = trung vị = p99 = max =**0,979344** |
| độ lệch chuẩn của tỉ số                | **2,5e-08** (2,64M pixel có dân)             |

⇒ **UN-adjustment là một vô hướng quốc gia, không phải một phép nắn không gian.** Hệ quả trực tiếp: thứ hạng ô
**bất biến từng bit**, nên [§ thứ tự](#e-data-quality--cleaning-từ-data-layer-overviewmd-7) nói đúng khi xếp `E-DQ7d` chạy trước — nhưng trước 29/07
đó là *giả định* ("gần đơn điệu"), nay là **số đo**.

> ⚠️ **Sửa con số của register cũ.** Dòng cũ ghi "+2,35% so 97,34M". **97,34 M là UN WPP**, không phải sản phẩm
> WorldPop nào cả — so sai đối tượng. So với **file UNadj mà ta thực sự có thể tải và checksum**, chênh lệch là
> **+2,11%** và mốc đúng là **97,569 M**. GSO 2020 (dân số trung bình) là **97,58 M**, tức bản UNadj **khớp GSO
> tốt hơn** cả hai con số trong register cũ.

**Cách xử lý — đổi FILE NGUỒN, tuyệt đối không hardcode hệ số** (đã thi hành 29/07):

1. **`WORLDPOP_URL` → `…/vnm_ppp_2020_UNadj_constrained.tif`** (HTTP 200, 17,6 MB, cùng grid 8.789×17.796,
   cùng `transform`, **cùng 2.644.884 pixel có dân**). Nhân `pop` với `0,979344` trong code cho ra **đúng cùng
   một mảng số**, nhưng biến một hằng số ma thuật không truy vết được thành thứ mà **E-DQ10 checksum được**.
   Cùng doctrine "clip là bước dẫn xuất trên raw bất biến" của E-DQ7a: hiệu chuẩn phải là **thuộc tính của
   nguồn**, không phải của pipeline.
2. **GIỮ bản unadjusted trên đĩa** (`population_raster_unadjusted_legacy` trong MANIFEST). Không phải vì tiếc
   26 MB: không có nó thì cổng ③ không chạy được, và khẳng định "đơn điệu ⇒ E-DQ7d không bị chặn" quay về
   trạng thái **lời hứa**.
3. **MANIFEST + `vintage`** cập nhật ở [`manifest.py`](../src/ev_siting/data/provenance/manifest.py); đổi nguồn
   thô ⇒ **bắt buộc** đi qua E-DQ10 (`make freeze`), không sửa lặng.
4. **Cổng chặn TRƯỚC khi ghi đè.** `worldpop_pop.py` chấm 3 cổng rồi mới `to_parquet` — FAIL thì artefact cũ
   **còn nguyên** (nhất quán "flag dòng, không xoá"), kèm `worldpop_pop_report.json`.

**QA gate — 3 cổng, kèm giá trị ĐO ĐƯỢC khi chạy 29/07** (mỗi cổng canh **một** giả định, và đều FAIL được):

| Cổng                           | Ngưỡng                                           | Đo được 29/07                                                   | Bắt được lỗi gì                                                           |
| ------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `pop_total_matches_unadj`     | lệch ≤**0,01%** so Σ file UNadj đã băm | **2,7e-11** (Σ = 97.569.444)                                 | tải nhầm lại bản unadjusted; lỗi gộp raster                               |
| `pop_rank_invariant`          | Spearman(pop cũ, pop mới) =**1,000**       | **1,000000** trên **104.171** ô, tập ô trùng khít | "hiệu chuẩn" bằng một phép**phi tuyến** (winsorize/log/chuẩn hoá) |
| `pop_scale_ratio_is_constant` | std(tỉ số theo pixel) <**1e-6**            | **2,4e-08**; min = max = **0,979344** (2,64M pixel)     | WorldPop đổi cách UNadj ở phiên bản sau ⇒ giả định đơn điệu tan   |

> Cổng ② là phép đo **duy nhất** biến "rescale đơn điệu nên không ảnh hưởng MCLP" từ lập luận thành **số**: nó
> so `pop` mới với artefact **ngay trước khi ghi đè**, tức tại lần migrate này nó so đúng bản dẫn từ raster
> unadjusted. Cổng ③ thiếu file legacy thì hạ xuống **WARN có lý do**, không im lặng PASS — bài học `poi_no_dup`
> của E-DQ7c (cổng kiểm đúng cái vừa chạy nên không bao giờ FAIL).

**Đã chứng minh cả 3 cổng FAIL được** (doctrine của dự án: dự án này từng ship 3 cổng không bao giờ FAIL được —
`poi_coords_in_vn` · `road_mt_le_total` · `poi_no_dup`). Bơm lỗi cố ý vào `qa_gates`:

| Lỗi bơm vào                                      | Cổng bắt                      | Kết quả                                        |
| --------------------------------------------------- | ------------------------------- | ------------------------------------------------ |
| chia lại cho 0,979344 (= quay về bản unadjusted) | `pop_total_matches_unadj`     | **FAIL** (lệch 2,11e-02)                  |
| winsorize đỉnh phân vị 99,9%                    | `pop_rank_invariant`          | **FAIL** (1−ρ = 5,12e-10)                |
| xoá 5 ô khỏi lưới                              | `pop_rank_invariant`          | **FAIL** ("tập ô ĐÃ ĐỔI")            |
| tỉ số theo pixel hết là hằng (std 4,2e-03)     | `pop_scale_ratio_is_constant` | **FAIL**                                   |
| thiếu raster legacy / chưa có artefact trước   | ③ / ②                         | **WARN** (không chặn, không PASS ngầm) |

> ⚠️ Chính phép thử này bắt được **hai lỗi trong bản cổng đầu tiên**: (a) winsorize chỉ kéo ρ xuống ~1e-10 nên
> `{rho:.6f}` in ra "1,000000" **ngay trên một dòng FAIL** — log tự mâu thuẫn, nay in 9 chữ số kèm `1−ρ`;
> (b) hai nhánh "không kiểm được" ban đầu trả `True` nên hiện **PASS**, tức lại đúng cái bệnh cổng-không-thể-FAIL
> mà E-DQ7e đang sửa — nay trả WARN tường minh.

**Kết quả** (chạy 29/07 — `worldpop_pop` → `make demand` → `build_buildable_h3 --national` → `make freeze`):

| Đại lượng                       | Trước        | Sau                  | Ghi chú                                                                              |
| ----------------------------------- | -------------- | -------------------- | ------------------------------------------------------------------------------------- |
| Σ`pop` (`worldpop_pop_h3`)     | 99.627.388     | **97.569.444** | −2,058 M (−2,07%);**104.171 ô** không đổi                                 |
| Σ`pop` (`demand_h3`, sau clip) | 99.620.916     | **97.563.106** | lưới vẫn**254.035** ô                                                       |
| dân bị clip ngoài VN (E-DQ7a)    | 6.472          | **6.338**      | = 6.472 × 0,979344 ⇒ clip**không** đổi hành vi                            |
| thứ hạng ô                       | —             | **bất biến** | Spearman 1,000000;`demand_h3` sắp xếp y hệt                                      |
| `buildable_h3` (national)         | 59.768 ô      | **59.768 ô**  | `pop` mới; **mọi cờ loại cứng/phạt mềm y nguyên**                     |
| `candidate_sites` (Hà Nội)      | 1.707          | **1.707**      | **trùng khít từng `candidate_id`** (T0 1.409 · T4 130 · T1 108 · T2 60) |
| cổng QA                            | 0 (không có) | **3**          | + 7 cổng`demand_h3` cũ vẫn PASS                                                  |

Mọi cổng của `make demand`, `osm/validate.py`, `landuse/validate.py` và `build_candidates` **PASS** sau khi đổi
nguồn (WARN duy nhất là `poi_recall_bias_parking_off` = 2,665 — vốn có từ E-DQ7c, không liên quan).
`make verify-snapshot HASHES=1` **PASS** sau `make freeze`.

**Dòng cuối cùng của bảng là điểm đáng giá nhất của E-DQ7e:** T4 gap-fill chấm điểm **tuyến tính theo `pop`** rồi
cắt theo **quantile**, nên một phép rescale đơn điệu **phải** cho ra đúng tập ứng viên cũ. Nó đúng như vậy — 1.707
`candidate_id` trùng khít. Đây là kiểm chứng **thực nghiệm** cho lập luận "7e không chặn 7d", thay vì chỉ suy từ
tính đơn điệu.

**Hiệu ứng phụ đã phát hiện & sửa — `osm_exclusion.py` crawl lại Overpass mỗi lần chạy và GHI ĐÈ raw đã freeze.**
Lộ ra khi dựng lại `buildable_h3`: bước này gọi Overpass rồi ghi đè `data/raw/landuse/osm_exclusion/*.json`, và
lần này **bị chặn bởi chính khoá read-only của E-DQ10** (`PermissionError`). Đó là lỗi doctrine: bước **dẫn xuất**
không được đụng vào raw bất biến, và Overpass trả kết quả khác nhau theo thời điểm nên bước này vốn **không tái
lập được**. Nay `_load_or_fetch` đọc thẳng snapshot đã freeze (`--refetch` mới crawl lại, kèm cảnh báo phải
`make freeze`). Cùng bài học "re-crawl là phá snapshot" mà **E-DQ7a** đã rút ra khi từ chối query Overpass bằng
`(poly:…)`.

**Limitation (`DOC`):**

- **UNadj neo về UN WPP, không neo về GSO.** Hai hệ thống thống kê khác nhau; chọn UNadj là chọn tính **so sánh
  quốc tế được**, không phải chọn "đúng hơn". Mọi con số công bố phải ghi rõ neo vào đâu.
- **"UNadj" ≠ đúng bằng UN WPP.** Tổng đo được của raster UNadj là **97,569 M**, còn UN WPP (bản duyệt 2019) cho
  Việt Nam 2020 là **97,34 M** — vẫn lệch **0,24%**. Nghĩa là hệ số 0,979344 là **thuộc tính của file WorldPop
  phát hành**, không phải một phép chia về đúng một con số WPP nào. Vì vậy cổng `pop_total_matches_unadj` phải
  neo vào **tổng của chính file đã checksum**, tuyệt đối không neo vào một con số WPP chép tay.
- **Vẫn là dữ liệu 2020, target occupancy là 2026.** E-DQ7e sửa **mức**, không sửa **niên đại** — đó là **P10**
  (⊘ won't-fix) và mốc lệch thời gian ở **P9**. Đây là phần dư lớn hơn +2,11% rất nhiều.
- **KHÔNG hiệu chuẩn theo tỉnh trong phạm vi 7e.** Nắn theo GSO cấp tỉnh **có** xê dịch thứ hạng (đô thị hoá
  lệch), nên hấp dẫn — nhưng vướng đúng hai thứ: (a) nó là hiệu chỉnh **niên đại** (P10/P11) chứ không phải hiệu
  chuẩn; (b) [`vn_boundary.geojson`](../data/interim/osm/vn_boundary.geojson) đang có **40 polygon adm4** gồm cả
  ba bản "cũ" (`An Giang cũ`, `Lào Cai cũ`, `Quảng Trị cũ`) so với **34 tỉnh** sau sáp nhập 2025 ⇒ phải qua quy
  tắc phân định của **E-DQ3** trước. Làm sớm = nắn dân số bằng một bảng ranh giới **chồng lấn**.

#### E-DQ7f — `pop` phân bổ sai chỗ trong ô (dasymetric spike) (bước 9)

`🟠 FIX · ☑ Xử lý 2026-07-29 · Owner: Giang · Chẩn đoán → cài đặt: 29/07`

> ⚠️ **Sửa con số của register cũ (đo lại trên artefact UNadj sau E-DQ7e).** Mọi số "146 ô / 792.118 dân /
> đỉnh 29.337 / 67 ô mật độ / 82.426 km²" ở bản trước **tính trên raster UN-UNADJUSTED** (trước khi 7e đổi
> nguồn cùng ngày). Trên artefact `worldpop_pop_h3` **thực đang dùng** (UNadj), tỉ số 0,979344 kéo mọi ngưỡng
> tuyệt đối xuống: **139 ô / 745.283 dân (0,764%)**, đỉnh pixel **28.731**, **61 ô** mật độ >48.000/km²
> (đỉnh **80.724/km²**), **giao vẫn = 0**. Bài học phụ: **detector KHÔNG bất biến theo scale** — một phép
> rescale đơn điệu (7e) dịch 7 ô ra/vào tập cờ vì ngưỡng đặt tuyệt đối. Vì vậy detector nay **buộc chạy lại**
> mỗi khi đổi nguồn (`make demand` gọi `reconcile_dasymetric` trước `build_demand_h3`).

**Chẩn đoán.** WorldPop *constrained* (BSGM) rải tổng dân cấp xã xuống **chỉ pixel mặt nạ built-settlement cho là
có người**. Nơi mặt nạ **bỏ sót** (núi đá vôi Đông Bắc/Tây Bắc, đảo), cả xã dồn vào 1–5 pixel — đỉnh **28.731
người trên MỘT pixel 100 m** = 2,9 triệu người/km². Đó không phải mật độ, đó là artefact.

**Detector mật độ cũ (`POP_DENSITY_OUTLIER` >48.000/km²) bắt nhầm tập hoàn toàn — giao = 0:**

| Bộ phát hiện                            |        Số ô | `pop` | trung vị max/pixel | trung vị top-3 |
| ------------------------------------------ | ------------: | ------: | ------------------: | --------------: |
| **pixel bất khả thi** (lỗi thật) | **139** | 745.283 |     **1.252** |  **1,00** |
| mật độ > 48.000/km² (đặc tả cũ)    |  **61** |  2,96 M |                 585 |           0,035 |
| **giao hai tập**                    |   **0** |      — |                  — |              — |

61 ô "mật độ cao" nằm **liền khối** trong lõi TP.HCM (~100 pixel/ô, 500–800 người/pixel — quận nội thành thật);
139 ô hỏng có mật độ **cấp ô** trung vị chỉ **~3.100/km²**, **không ô nào chạm 48.000**. Lỗi **không quan sát
được** ở thang mật-độ-ô mà đặc tả cũ chọn — chỉ lộ ở **cấp pixel**. Cùng họ lỗi `poi_coords_in_vn` của E-DQ7a:
**một cổng đo bằng đại lượng không chứa thông tin về lỗi**.

**BƯỚC NGOẶT — đối chiếu VNSDI DANSO lật đổ tiền đề "chỉ sai chỗ".** Trước 29/07, register giả định *tổng cấp
xã đúng, chỉ vị trí sai* — và tự ghi nhận không nguồn nào trong dự án kiểm được. Nay đã **crawl nguồn dân số cấp
xã ĐỘC LẬP** ([`data/vnsdi/`](../src/ev_siting/data/vnsdi/), ArcGIS VNSDI 34DVHC layer 2, **3.321 xã**, DANSO
2025). Spatial-join 2,64M pixel WorldPop → xã (**99,88% gán được**, 0,16% khối lượng ngoài polygon) rồi so tổng
mỗi xã:

| Kiểm chứng                                                                       | Đo được                                                                            |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1 ô nhiều dân hơn**CẢ XÃ** (bất khả thi — chống lệch niên đại) | **16/139 ô · 321.684 dân (43%)**                                              |
| xã có WorldPop >**1,5× DANSO** (dồn thừa)                               | **50 ô · 468.593 dân (63%)**                                                  |
| cụm đảo Hòn Nghệ + Sơn Hải (An Giang)                                       | WorldPop**117.126** vs DANSO **5.335** (~**22×**)                   |
| tổng WorldPop vs Σ DANSO / Spearman xã                                          | 97,57 M vs 113,63 M · ρ=**0,827**; tỉ số/xã p10–p90 = **0,28–1,36** |

⇒ Với **63% khối lượng bị cờ, `pop` cấp xã CHÍNH NÓ sai** (dồn thừa), không chỉ sai vị trí. **Rải lại giữ nguyên
khối lượng ở đó = rải NGƯỜI MA.** Đây là lý do đặc tả D1–D6 cũ (rải trong ô, bảo toàn khối lượng WorldPop) bị
thay: sửa phải **TÁCH theo tổng độc lập**.

**Hậu quả (đo trên artefact UNadj) — bơm rác vào đúng đỉnh hàm mục tiêu:** **16/139** ô trong top-500 `pop` toàn
quốc · **42/139** ô `buildable=True` (ứng viên T4 khi chạy national) · **5** ô `POP_NO_ROAD` giả (E-DQ8, nay là 5/6.350 và đã dời ở [E-DQ8b](#e-dq8b--dời-dân-ở-ô-không-có-lối-vào-bước-10b)) · chỉ
**14/12.811** ô cung ⇒ **không** chặn E-DQ7d.

---

**Cách xử lý (ĐÃ CÀI ĐẶT) — [`reconcile_dasymetric.py`](../src/ev_siting/data/worldpop/reconcile_dasymetric.py).**
Giữ `pop` bất biến từng bit (UN-anchored, cổng 7e còn xanh); thêm cột song song `pop_adj` (đã đặt lại chỗ) +
cờ `pop_pixel_implausible`.

1. **D1 — thống kê pixel + gán xã.** Đọc raster (nơi duy nhất còn pixel), xuất `n_px`, `max_px`, `top3_px_share`,
   `n_eff = (Σp)²/Σp²`, `pop_per_eff_px = Σp²/Σp`, trọng tâm `pop_lat`/`pop_lon`; gán pixel → xã bằng `STRtree`.
2. **D2 — detector cứng** (khuôn hai-detector E-DQ1): `max_px > 1.000` **hoặc** (`pop > 2.000` & `top3 > 0,8`)
   → **139 ô**. Ngưỡng 1.000 nay **neo ngoại vi**: `pop_per_eff_px` của ô lõi TP.HCM đã kiểm chứng dày thật có
   p99 = **737**; ô bị cờ trung vị **1.201** — 1.000 nằm đúng khe đo được, không còn là số đặt tay thuần.
3. **D3 — phân lớp theo tổng độc lập** (trung hoà niên đại bằng tỉ số quốc gia 0,859 = 97,569/113,626):
   **RETOTAL** (WorldPop > 1,5×DANSO → **17 xã**) vs **REPLACE** (còn lại → **53 xã**); **70 xã** ảnh hưởng.
4. **D4 — rải lại theo built-up WorldCover 10 m** trong ranh giới xã (KHÔNG winsorize: cắt ngọn san phẳng lõi
   TP.HCM mà không chạm ô hỏng). RETOTAL: hạ tổng về **0,859·DANSO** rồi rải (gỡ người ma); REPLACE: **giữ tổng
   cấp xã**, chỉ đổi chỗ. 3.771 ô built-up trước đó `pop=0` nhận khối lượng dịch sang.
5. **D5 — neo khối lượng + consumer.** `pop` cho phát biểu **tuyệt đối** (`coverage_pop`, GSO); `pop_adj` cho
   consumer **XẾP HẠNG** (MCLP `demand_weight`, T4). Σ`pop_adj` quốc gia **97,083 M** (−0,499% = 486.399 người
   ma gỡ khỏi đảo/núi) — hệ quả CÓ CHỦ Ý, có cổng canh. **KHÔNG** cân bằng người ma sang xã thiếu toàn quốc
   (việc đó kéo thứ hạng cả lưới theo số 2025, trộn hiệu chỉnh niên đại P10 vào lỗi phân bổ — ngoài scope 7f).
6. **D6 — chặn downstream.** [`build_demand_h3`](../src/ev_siting/data/worldpop/build_demand_h3.py) mang `pop_adj`
   + cờ vào `demand_h3`; [`_gapfill`](../src/ev_siting/features/build_candidates.py) chấm điểm bằng `pop_adj` **và**
     loại ô `pop_pixel_implausible` không có đường trục/POI xác nhận.

**Cổng QA — 7 cổng, giá trị đo khi chạy 29/07 (mỗi cổng FAIL được):**

| Cổng                                | Đo được 29/07                                                                    |
| ------------------------------------ | ------------------------------------------------------------------------------------ |
| `pop_bit_invariant`                | max\|Δ\| = **0,0** (không đụng cột UN-anchored)                           |
| `no_unflagged_implausible_pixel`   | **0** ô `max_px>1.000` không cờ                                           |
| `flagged_mass_share_lt_1pct`       | **0,764%**                                                                     |
| `retotal_reduces_mass`             | gỡ**486.399** (removed 651.049 − target 164.651) — chỉ HẠ                 |
| `global_mass_accounted`            | \|Σpop_adj − kỳ vọng\| = **0,000 người** (kế toán độc lập nhãn ô) |
| `pop_adj_national_drift_lt_1pct`   | **0,499%**                                                                     |
| `commune_join_coverage` (advisory) | pixel không gán =**0,16%**                                                   |

> Cổng `global_mass_accounted` là chỗ tinh tế: ô nhận vắt biên thuộc **hai** xã nên bảo toàn theo NHÃN ô không
> giữ (lệch 5,2e-3); kế toán theo **TỔNG** trong lượt rải (REPLACE net 0, RETOTAL hạ đúng phần người ma) cho
> residual **0,000 người**. Cùng bài học "đo ở thang mà đại lượng thực sự bảo toàn" của các cổng E-DQ trước.

**Kết quả** (`make demand` → `build_candidates`):

| Đại lượng                        | Trước (`pop`) | Sau (`pop_adj`)                                                      |
| ------------------------------------ | ----------------- | ---------------------------------------------------------------------- |
| ô đảo Hòn Nghệ`8865a30cd5f…` | **28.731**  | **493** (xã 2.546 dân)                                         |
| ô bị cờ trong top-500 quốc gia   | **16**      | **0**                                                            |
| ô built-up bị cờ → ứng viên T4 | 42                | **21 loại · 21 chấm lại** (trung bình 8.727 → 1.834)       |
| `candidate_sites` (Hà Nội MVP)   | 1.707             | **1.707** (không đổi — 7f chạm núi/đảo, không chạm HN) |
| Σ`pop` (UN-anchored)              | 97.563.106        | **97.563.106** (bất biến, cổng 7e xanh)                       |

`make verify-snapshot` **PASS**; mọi validator `osm/validate`, `demand_h3`, `build_candidates` **PASS**.

**Limitation (`DOC`):**

- **DANSO là dân số ĐĂNG KÝ 2025** (+16,5% vs WorldPop 2020; Σ 113,63 M vs GSO 2024 ~101 M). Trung hoà lệch mức
  quốc gia bằng ×0,859 nhưng **lệch niên đại/đô-thị-hoá theo từng xã còn lại** — chính vì thế RETOTAL chỉ kích
  hoạt ở `r > 1,75` (vượt xa mức niên đại giải thích được), và 16 ô "1 ô > cả xã" là lõi **chống lệch niên đại**.
- **Không sửa được nguyên nhân gốc.** Lỗi ở mặt nạ built-settlement của BSGM; ta chỉ **phát hiện + rải lại** theo
  WorldCover. Dựng lại phân bổ tử tế cần lớp built-up độc lập tốt hơn (Microsoft/Google footprints) — roadmap.
- **6/139 ô không có built-up để rải** → giữ tại chỗ, `pop_src = UNREPAIRED_NO_BUILTUP` (đo 29/07: 0 ô — mọi ô
  bị cờ đều có built-up trong xã; nhánh vẫn còn để phòng snapshot sau).
- **Thứ hạng bị xê dịch ⇒ khác E-DQ7e về bản chất** — lý do phải tách hai dòng: 7e an toàn với mọi downstream,
  7f thì không (nên có cột `pop_adj` riêng, không đè `pop`).

#### E-DQ8a — Lối vào đo ở thang SAI (bước 10)

`🟡 FIX · ☑ Xử lý 2026-07-30 · Owner: Giang`

**Chẩn đoán.** `buildable_h3` và E-DQ8 hỏi *"ô này có đường không?"* bằng cách xét **đúng ô đó**
(`road_access_m <= 0`). Ô res 8 rộng 0,75 km² và tâm hai ô kề cách **0,98 km**: một xóm mà đường vào nằm ở
**ô bên cạnh** bị kết luận "không có đường". Tách 6.350 ô của E-DQ8 theo vành:

| Bậc         | Điều kiện                          |     Ô |     `pop` | % khối lượng |
| ----------- | ---------------------------------- | -----: | ---------: | -----------: |
| `ADJACENT`  | có đường ở **vành 1** (~1,0 km)    | **4.862** | 894.956 | **72,1%** |
| `NEAR`      | chỉ có ở vành 2 (~2,0 km)          |    923 | 159.831 |      12,9% |
| `ISOLATED`  | không có đường trong cả hai vành   |    565 | 187.047 |      15,1% |

⇒ **72,1% khối lượng E-DQ8 không phải lỗi dữ liệu, mà lỗi THANG ĐO.** Đây đúng là cái bẫy mà **E-DQ7a đã gỡ ở
tầng biên giới** ("test là **giao lục giác** ∩ polygon, KHÔNG phải tâm-ô-trong-polygon" — vì ô vắt biên rơi tâm
về bên nào cũng được); tầng đường chưa từng được xử lý cùng cách. Cùng họ với `poi_coords_in_vn` (7a) và
`POP_DENSITY_OUTLIER` (7f): **một đại lượng không chứa thông tin về câu hỏi được hỏi**.

**Neo ngoại vi — 19.015 trạm đang vận hành.** Bậc mới phải được kiểm bằng thực địa, không tự tuyên bố:

| Bậc của ô chứa trạm | Trạm | % trạm | % dân số ở bậc đó |
| ------------------- | ----: | -----: | ----------------: |
| `DIRECT`            | 18.907 | **99,432%** | 98,727% |
| `ADJACENT`          |    **15** |  0,079% |  **0,917%** |
| `NEAR`              |     5 |  0,026% |  0,164% |
| `ISOLATED`          |     1 |  0,005% |  0,192% |
| *không có dòng trong lưới* | **87** | 0,458% | — (xem [E-DQ8c](#e-dq8c--dân-không-phục-vụ-được-mẫu-số-bước-10c)) |

Đọc đúng bằng chứng này quan trọng hơn cả con số: **15 trạm thật ở ô `ADJACENT` ⇒ ô như thế xây được**, nên loại
cứng chúng là sai. Nhưng `ADJACENT` giữ 0,917% dân mà chỉ nhận 0,079% trạm — **dưới mức dân số ~11×** — nên bằng
chứng **không** đủ để nói `ADJACENT` tương đương `DIRECT`. Vì vậy đáp án là **bậc có thứ tự + phạt mềm**, không
phải nới bộ lọc thành nhị phân.

**Cách xử lý (ĐÃ CÀI ĐẶT) — [`osm/access_tiers.py`](../src/ev_siting/data/osm/access_tiers.py).**

1. **A1 — hai cột vành + một cột bậc.** `road_access_nb1_m`, `road_access_nb2_m` (Σ `road_access_m` của vành 1/2,
   **trừ** chính ô) → `access_tier` ∈ `DIRECT|ADJACENT|NEAR|ISOLATED`. Vào `demand_h3`.
2. **A2 — tính TRƯỚC khi clip lãnh thổ.** Ô bên kia biên vẫn là láng giềng **có đường thật** (8.934 km đường rò
   của Geofabrik, E-DQ7a); clip trước khi tính vành sẽ báo `ISOLATED` giả cho đúng những ô biên.
3. **A3 — loại cứng CHỈ `ISOLATED`** (`buildable_h3`: **6.350 → 723 ô**). `ADJACENT`/`NEAR` nhận phạt mềm
   `NEEDS_ACCESS_ROAD` (**7.072 ô**) — phải **làm** đường vào là chi phí thật, không phải lý do loại bỏ.
4. **A4 — bậc phải được TÍNH, không mặc định.** Ô AOI không có dòng trong `demand_h3` (AOI thành phố sinh đĩa
   hình học; ô `OUTSIDE` đã tách sang `demand_h3_clipped_out`) trước đây rơi về `road_access_m = 0` ⇒ loại cứng.
   Nay tra bậc từ `osm_demand_components_h3` qua `tiers_from_lookup()`. Lý do là **đo được**: 76 ô không-dòng
   chứa **83 trạm đang vận hành**, và tính từ bảng đường ra **50 `ADJACENT` · 8 `NEAR` · 18 `ISOLATED`** — mặc
   định `ISOLATED` loại cứng đúng những ô đã có bằng chứng thực địa là xây được. `classify()` là **nơi duy nhất**
   định nghĩa bậc để hai đường tính không thể lệch (bài học cổng ② của E-DQ7b).

**Phát hiện phụ — bộ lọc cũ gần như vô ích.** `NO_ROAD_ACCESS` loại 6.350 ô, nhưng chỉ **134 ô** bị loại **RIÊNG**
bởi nó; phần còn lại đã vướng `NOT_BUILT_UP`/`WATER`/`WETLAND`:

```
('NOT_BUILT_UP','NO_ROAD_ACCESS')                      4.408
('NOT_BUILT_UP','NO_ROAD_ACCESS','WATER','WETLAND')      749
('NOT_BUILT_UP','NO_ROAD_ACCESS','WATER')                520
('NOT_BUILT_UP','NO_ROAD_ACCESS','WETLAND')              481
('NO_ROAD_ACCESS',) một mình                             134
```

⇒ Hệ quả **cung** của E-DQ8 gần bằng 0; hệ quả thật nằm ở **mẫu số cầu**, và đó là 8b/8c.

**Phát hiện phụ — bốn cờ mềm có trọng số 0.** `POP_NO_ROAD`, `ROAD_ACCESS_INFORMAL` (27.828 ô),
`ROAD_BRIDGE_ONLY` (50 ô), `NO_SUBSTATION` được **phát** vào `penalty_flags` nhưng công thức `penalty` chỉ gồm
`crop`/`low_built`/`dist` ⇒ chúng **không hề** ảnh hưởng điểm. Nay vào công thức
(`+0,2·needs_access +0,1·informal +0,1·bridge_only`). `access_tier` cũng được **xuất ra** `buildable_h3`: không
audit được một quyết định loại bỏ bằng cột không có trong artefact.

**Cổng QA — 1 cổng mới ở `build_demand_h3` (FAIL được):** `access_tier_consistent` — mọi ô `road_access_m > 0`
phải là `DIRECT`, và mọi ô `ISOLATED` phải thật sự trống đường ở **cả hai** vành (đo: **0 · 0**). Kèm
[`tests/test_access_tiers.py`](../tests/test_access_tiers.py) — 11 test khoá ngữ nghĩa, trong đó ca `ADJACENT`
(ô mà bản cũ đánh sai) và ca ô mồ côi ở A4.

**Kết quả** (`make demand` → `landuse-national` → `candidates`):

| Đại lượng                                | Trước       | Sau                    |
| ---------------------------------------- | ------------ | ---------------------- |
| ô loại cứng vì "không đường"           | 6.350        | **723** (`ISOLATED`) |
| `buildable` national                     | 59.768       | **59.927**       |
| cờ `NEEDS_ACCESS_ROAD`                 | —           | **7.072 ô**      |
| `candidate_sites` (Hà Nội MVP)         | 1.707        | **1.707** (không đổi) |
| `demand_h3`                              | 254.159 ô   | **255.480 ô** (thêm ô nhận của 8b) |

**Limitation (`DOC`):**

- **`ADJACENT` ≠ `DIRECT`, và phạt 0,2 là số ĐẶT TAY.** Bằng chứng 15 trạm chỉ chứng minh *tới được*; độ lớn chi
  phí làm đường vào chưa có nguồn. Nếu muốn số đo, phải có capex đường theo lớp — chưa freeze nguồn nào.
- **Vành ≠ khoảng cách.** `grid_disk(1)` là ~0,98 km theo tâm ô, không phải khoảng cách tới **mép** đường. Muốn
  chính xác phải tính `dist_to_road_m` từ hình học way — chưa làm; vành là bản rẻ và đủ để phân bậc.
- **Lưới vẫn KHÔNG phải tessellation.** A4 chữa *mặc định sai*, không chữa *ô thiếu*: 76 ô / 83 trạm vẫn không có
  dòng ở bất kỳ bảng lưới nào. Xem [E-DQ8c](#e-dq8c--dân-không-phục-vụ-được-mẫu-số-bước-10c).

#### E-DQ8b — Dời dân ở ô không có lối vào (bước 10b)

`🟠 FIX · ☑ Xử lý 2026-07-30 · Owner: Giang`

**Tiền đề.** Sau 8a, `ADJACENT`/`NEAR`/`ISOLATED` là ô mà **xe không vào được tận nơi** nhưng vẫn mang
`pop_adj > 0`. Để MCLP nhìn thấy đúng cầu, khối lượng đó phải **dời sang ô đặt trụ được**, không phải bị xoá và
cũng không được để đọng. Dùng lại **đúng bộ máy E-DQ7f** (trọng tài bằng tổng độc lập cấp xã → rải theo built-up →
kế toán khối lượng theo TỔNG), khác 7f ở ba chỗ và **cả ba đều do đo được**:

**① Phạm vi khác.** Detector 7f là detector **dồn cục** (`max_px > 1.000` ∨ `pop>2.000 & top3>0,8`) → 139 ô. Tập
E-DQ8 là 6.350 ô và **giao chỉ 109 ô**. Hai lỗi khác nhau: 7f = "cả xã nhồi vào 1 pixel", 8b = "người ở ô mà xe
không vào được".

**② Khối lượng phần lớn là THẬT — ngược hẳn 7f.** Chạy **cùng phép trọng tài DANSO** trên tập E-DQ8 (join ô→xã
96,7%):

| Phân lớp xã                                 |    Ô |     Người | % khối lượng | 7f để so |
| ------------------------------------------- | ----: | ---------: | -----------: | -------: |
| `RETOTAL` (WorldPop\_xã > 1,5×DANSO ⇒ người ma) |   765 | 229.224 | **18,5%** | **63%** |
| `REPLACE` (DANSO xác nhận tổng ⇒ chỉ sai chỗ)   | 5.373 | 944.229 | **81,5%** |     37% |

⇒ Với 8b, mặc định là **REPLACE (bảo toàn khối lượng, chỉ đổi chỗ)**. Nếu bê nguyên chính sách của 7f sang đây
thì sẽ **gỡ mất ~800k người thật**.

> **Một tiền đề suýt dẫn tới phép sửa sai — ghi lại để không ai đề xuất lại.** Giả thuyết ban đầu: "dân ở ô
> roadless mà WorldCover không thấy built-up là dasymetric smear" (đo thô ủng hộ: khối lượng ở ô `built_up_frac=0`
> chiếm **47,6%** trong nhóm roadless so với **2,0%** trong nhóm có đường — chênh 24×). **Đo phân bố thì tiền đề
> sụp:** ô `built_up_frac = 0` mà **có** đường có p50 = 97 · p90 = 558 · p99 = **1.779** người; ô `built_up_frac = 0`
> mà **không** đường có p50 = 70 · p90 = 391 · p99 = **1.183** — **đuôi NHẸ HƠN**. Tức "dân trên đất không có
> built-up" là **thuộc tính toàn quốc của cặp WorldPop×WorldCover** (12.182 ô · 2,50 M người); nhóm roadless chỉ
> chiếm 24% của nó, và chênh 24× kia là chênh **tỉ trọng trong tầng**, không phải bất thường **theo ô**. Kết luận
> vận hành: **built-up là TRỌNG SỐ ô nhận, không bao giờ là detector.** Cùng bài học "đại lượng phải chứa thông
> tin về lỗi" của 7a/7f — lần này bắt được *trước* khi cài đặt.
>
> Cùng lúc phát hiện `POP_BUILTUP_DENSITY_CEIL = 750` trong `worldpop/paths.py` là **hằng số CHẾT có docstring
> sai**: 737 vốn là `pop_per_eff_px` (người/pixel hiệu dụng), **không** phải người/ha built-up. Đo đúng đại lượng:
> p99 mật độ built-up lõi TP.HCM r=12 km là **904** (max 1.491). Dùng 750 làm detector gắn cờ **15.056 ô / 8,97 M
> người (9,2% toàn quốc)**, gồm **26 ô lõi TP.HCM/Hà Nội THẬT** ⇒ vô dụng. Đã ghi cảnh báo tại chỗ, **không** đấu
> dây vào cổng nào.

**③ Ô nhận phải ĐẶT TRỤ ĐƯỢC — và điều này sửa một hồi quy của 7f.** D4 của 7f rải theo built-up **không xét lối
vào**, nên nó **đổ người vào ô roadless**: số ô `pop>0 & road_access=0` đi từ **6.350** (`pop`) lên **6.467**
(`pop_adj`).
Ở 8b trọng số ô nhận là `built_ha × 1{access_tier == DIRECT}`.

**Cách xử lý (ĐÃ CÀI ĐẶT) — [`reallocate_roadless.py`](../src/ev_siting/data/worldpop/reallocate_roadless.py).**

1. **R1 — lưới hợp nhất + bậc.** `pop ∪ đường ∪ built-up`, tính `access_tier` trên lưới hợp nhất (tổng vành phụ
   thuộc láng giềng nên **không** tính được trên tập con). Loại 191.506 ô đệm ngoài VN do tile WorldCover kéo vào.
2. **R2 — phạm vi:** `pop_adj > 0` & `access_tier ≠ DIRECT` → **6.469 ô / 1.183.197 người**.
3. **R3 — trọng tài cấp xã** (dùng lại `POP_RETOTAL_RATIO=1,5` + `POP_WORLDPOP_OVER_DANSO=0,859`): **92 xã**
   `RETOTAL` · **855 xã** `REPLACE`.
4. **R4 — ô nhận = built-up ∧ `DIRECT`, cùng xã**, trọng số theo `built_ha`. **KHÔNG có nhánh dự phòng** "rải vào
   built-up bất kỳ": bản đầu có nhánh đó và **cổng ② bắt ngay** — nó đổ dân sang một ô roadless KHÁC, tức tự sinh
   lại đúng lỗi đang sửa. Xã không có ô nào vừa built-up vừa `DIRECT` ⇒ **giữ tại chỗ có nhãn**, đầu vào 8c.
5. **R5 — chính sách khối lượng** (kế toán theo TỔNG, bài học cổng ⑤ của 7f):
   `REPLACE`: `target = removed` (bảo toàn tuyệt đối) · `RETOTAL`: `target = removed × (0,859·DANSO / wp_xã) < removed`.
   RETOTAL ở đây **chỉ hạ phần khối lượng đang dời**, KHÔNG viết lại cả xã như 7f — 8b sửa *vị trí của khối lượng
   roadless*, không sửa *tổng của xã*, để hai phép sửa không tranh nhau cùng khối lượng.
6. **R6 — `pop` bất biến từng bit**; mọi thay đổi vào `pop_adj` (hợp đồng D5 của 7f). Artefact mới
   `worldpop_pop_acc_h3.parquet`; `build_demand_h3` nạp theo thang **8b → 7f → 7e**, mỗi bậc in cảnh báo.

**Sổ cái `pop_src`** (kiểm được, không phải tự khai):

| `pop_src`                          |      Ô | Ý nghĩa |
| ---------------------------------- | ------: | ------- |
| `WORLDPOP`                         | 252.529 | không đụng |
| `MOVED_TO_ACCESSIBLE`              | **6.244** | dời sang ô `DIRECT` cùng xã (8b) |
| `REDISTRIBUTED` / `RETOTALED_DANSO` | 2.915 / 936 | ô do 7f xử lý |
| `UNREPAIRED_NO_COMMUNE`            |     222 | ngoài mọi polygon xã → 8c |
| `UNREPAIRED_NO_ACCESSIBLE_BUILTUP` |       3 | xã không có đất vừa built-up vừa `DIRECT` → 8c |

**Cổng QA — 8 cổng, giá trị đo khi chạy 30/07 (mỗi cổng FAIL được):**

| Cổng | Đo được 30/07 |
| ---- | ------------- |
| `pop_bit_invariant` | max\|Δpop\| = **0,0** |
| `no_unlabelled_roadless_pop` | 225 ô còn dân, **0 ô KHÔNG nhãn** |
| `retotal_only_reduces` | gỡ **110.855** người ma (removed 196.865 − target 86.009) |
| `global_mass_accounted` | \|Σpop_adj − kỳ vọng\| = **0,000 người** |
| `national_drift_lt_1pct` | **0,114%** so `pop_adj` sau 7f |
| `roadless_mass_strictly_decreases` | 1.183.197 → **42.576** (**−96,4%**) |
| `all_received_mass_landed_direct` | **0** ô không-`DIRECT` nhận thêm dân |
| `supply_ranking_shift` (advisory) | **2.541/12.811** ô cung đổi `pop_adj` (19,83%) |

> **Hai cổng đã bắt lỗi thật trong lúc dựng** — và đó là lý do chúng được viết để FAIL được. Lần chạy 1: cổng ②
> đỏ với **224 ô** bị bỏ qua im lặng (không gán được xã ⇒ không vào vòng lặp). Lần chạy 2: vẫn đỏ với **2 ô** —
> chính là ô nhận của nhánh dự phòng "built-up bất kỳ", tức phép sửa đang **tái tạo** lỗi. Gỡ nhánh đó xong mới
> xanh. Cổng ⑦ ban đầu đo bằng **nhãn `pop_src`** — nhưng nhãn là thứ code **tự ghi**, kiểm bằng nó thì cổng chỉ
> xác nhận code đồng ý với chính nó (đúng lỗi `poi_coords_in_vn` của 7a); đã đổi sang so `pop_adj` trước/sau trên
> chính các ô không-`DIRECT`.

**Kết quả:**

| Đại lượng | `pop` (UN-anchored) | `pop_adj` (sau 7f+8b) |
| --------- | ------------------: | --------------------: |
| khối lượng ở ô roadless | 1.241.833 | **42.249** (**−96,6%**) |
| Σ toàn quốc | **97.563.106** (bất biến) | 96.965.852 (−0,612% cộng dồn) |
| ô `pop>0 & road_access=0` do phép sửa TỰ SINH | 7f: **+117** | 8b: **0** (cổng ⑦) |

`make demand` PASS · `osm/validate` PASS · `landuse/validate` PASS · `candidates` Hà Nội **1.707** (không đổi) ·
40 test PASS.

**Limitation (`DOC`):**

- **Không sửa được nguyên nhân gốc** — vẫn là mặt nạ built-settlement của BSGM (7f) cộng với OSM thiếu đường. 8b
  chỉ **đặt lại chỗ** theo WorldCover; muốn phân bổ tử tế cần lớp built-up độc lập tốt hơn (Microsoft/Google
  footprints) — roadmap, cùng dòng với limitation của 7f.
- **Ranh giới xã là ranh giới dời dân, không phải nhãn hành chính.** Gán ô→xã ở 8b theo **tâm ô** còn 7f theo
  **pixel**, nên hai bảng có thể lệch ở ô vắt biên. Chấp nhận được vì kế toán theo TỔNG không lệ thuộc nhãn — và
  nhãn admin thật vẫn là việc của **E-DQ3**.
- **Dời trong xã có thể dời khá xa.** Không có ràng buộc khoảng cách: một xã dài thì người có thể nhảy vài km sang
  ô built-up khác. Đúng về mặt "ai phục vụ được họ", nhưng nếu Sprint 3 cần khoảng cách đi lại thật thì phải thêm
  trần khoảng cách vào R4.
- **`ADJACENT` bị dời khối lượng dù chỉ cách 1 vành.** Có thể tranh luận nên **chia tỉ lệ** thay vì dời hết. Chưa
  làm vì chưa có nguồn nào đo được tỉ lệ đó — giữ dứt khoát để cổng kế toán còn kiểm được.

#### E-DQ8c — Dân KHÔNG phục vụ được: mẫu số (bước 10c)

`⚪ DOC → policy · ☐ Open · Owner: Giang/Kỳ`

**Không phải việc làm sạch.** Dư sau 8b: **225 ô / 42.576 người** giữ tại chỗ có nhãn — **222 ô** ngoài mọi polygon
xã VNSDI (đảo/vắt biên) và **3 ô** ở xã không có đất vừa built-up vừa `DIRECT`. Cụm lõi của nhóm cô lập thật là
xóm kênh rạch **ĐBSCL** (9,8–10,0 N / 104,9 E, `frac_water` 0,43–0,66, `built_up_frac` 0,006–0,099): người
**thật**, đi lại bằng **thuyền**. Không có phép làm sạch nào biến họ thành phục vụ được, và cố "sửa" là bịa.

**Quyết định phải ra (chưa ra) — 3 việc:**

1. **`demand_servable`** — cột boolean ở `demand_h3`, `False` cho ô `pop_src LIKE 'UNREPAIRED%'`.
2. **`coverage_pop` phải trừ nhóm này và CÔNG BỐ số bị trừ.** Để đọng thì mọi chỉ số coverage bị hạ ~0,04% bởi
   một khối lượng **không thể phủ theo định nghĩa** — và với `radius_m` hiện tại (500 m,
   [`config/params.yaml`](../config/params.yaml)) mỗi ô chỉ phủ chính nó, nên ô roadless là **chính xác không phủ
   được**. Mục tiêu coverage đặt trên mẫu số đó là không đạt được **theo cấu tạo**.
3. **Lưới phải thành tessellation** — việc còn lại của 8a/A4: **76 ô chứa 83 trạm đang vận hành** không có dòng ở
   `demand_h3`, `demand_h3_clipped_out`, lẫn `buildable_h3`, vì lưới là **hợp của các ô CÓ đặc trưng**
   (`pop>0` ∪ đặc trưng OSM), không phải phủ hình học. Chúng vô hình với optimizer ở **cả hai** vai cung và cầu,
   và bơm nhiễu vào tử số cổng ⑥ `supply_cells_have_road_access` (100/12.811). Bậc thật của chúng (tính từ bảng
   đường): **50 `ADJACENT` · 8 `NEAR` · 18 `ISOLATED`**.
   > ⚠️ **Thứ tự bắt buộc: A4 phải xong TRƯỚC bước này** — và nó đã xong. Làm tessellation trước A4 sẽ đưa 76 ô
   > đó vào lưới với bậc mặc định `ISOLATED` ⇒ loại cứng **76/76** ô đang chứa trạm thật, và bản sửa lưới sẽ trông
   > như một hồi quy. Cần cổng mới `grid_contains_all_supply_cells` (**FAIL**, không WARN).

**Chưa làm vì đây là thay đổi ĐỊNH NGHĨA LƯỚI**, kéo theo số dòng của `demand_h3`/`buildable_h3`/AOI national và
mẫu số của cổng ⑥ ⇒ cần chốt phạm vi trước (gộp vào **E-DQ3**, vốn cần cùng artefact polygon, là lựa chọn rẻ nhất).

#### E-DQ7d — Proxy cầu chưa kiểm chứng ngoại vi (bước 7)

`🔴 FIX (chặn) · ☐ Open · Owner: **Kỳ** (bàn giao 29/07) · Chẩn đoán: Giang (29/07)`

`demand_weight` là **hàm mục tiêu** của MCLP: một vô hướng/ô cho **254.035** ô, là điểm chạm interop #1
(Giang → Kỳ, hạn **01/08**). MCLP chọn p ô sao cho tổng `demand_weight` được phủ là lớn nhất ⇒ mọi kết
quả downstream (coverage %, đường cong ngân sách, danh sách vị trí đề xuất) là **hệ quả đơn điệu** của
con số này. E-DQ7d là ghi nhận rằng con số đó **chưa từng được đối chiếu với thực tế**, và lần đối chiếu
duy nhất trả về ρ ≈ 0,30.

18,6M bản ghi occupancy là **nguồn ngoại vi duy nhất của cả pipeline quan sát KẾT QUẢ** (xe thật đang
sạc) thay vì một proxy khác của cầu — cùng vai trò mà `poi_recall.py` đóng cho tầng POI ở E-DQ7c, nhưng
cho chính hàm mục tiêu.

**Chẩn đoán — register ghi 2 số, cả 2 đều không sống sót khi đo lại trên artefact sau 7a/7b/7c:**

| # | Register                                        | Đo lại 29/07                          | Kết luận                                                                        |
| - | ----------------------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------- |
| 1 | 18,6M occupancy                                 | **18.630.532** poll / 19.218 file | ✅ — nhưng cửa sổ chỉ**7,15 ngày** (13→20/07/2026), xem **P3** |
| 2 | ρ(proxy, occupancy) ≈ 0,30                    | **0,296**                         | ✅ tái lập —**nhưng chỉ bằng cách đo sai** (xem A)                  |
| 3 | **983** ô có sạc thật, mọi input = 0 | **644** (488 ô có `occ>0`)    | ❌ không tái lập — đúng khuôn "496 trùng → 335" của E-DQ7c              |

Phạm vi đo: cung = `is_operational & access=PUBLIC & is_primary & coord_resolved` → **19.015** trạm
(18.809 trạm có panel) trên **12.811 ô cung**.

**A — con số 0,296 là artefact của phép đo, không phải tính chất của proxy.** Nó tính trên cả 254.035 ô,
coi **95,67%** ô không có trạm là `occ = 0`. Những ô đó không phải *không có cầu*, chúng là **không quan
sát được** — không có trụ thì không có telemetry. ρ ấy chủ yếu đang đo "đô thị hay không". Trên tập
**đánh giá được thật** (12.811 ô cung), các proxy đặt tay cho **0,26–0,33**.

**B — target thô là 77% CUNG, không phải cầu.** Đây là phát hiện quyết định:

| Đại lượng                               | ρ_Spearman với`occ` |
| ------------------------------------------- | ----------------------: |
| **số súng trong ô**                |        **+0,773** |
| tổng kW trong ô                           |                  +0,768 |
| số trạm trong ô                          |                  +0,406 |
| **proxy cầu (equal-weight 10 cột)** |        **+0,331** |

`occ_mean` theo `current_type`: **AC 0,122** (n=12.973) · **DC 1,652** (n=3.469) · **MIXED 1,831**
(n=2.237) — chênh **13×**. `n_cars_charging` đo *VinFast đã lắp bao nhiêu súng và có phải DC không*,
không đo *có bao nhiêu cầu ở đó*. Đặt cổng trên ρ thô = **đặt cổng lên công suất lắp đặt**; tệ hơn, fit
trọng số trên nó là **học lại chính sách siting của VinFast** rồi trả về như một kiểm chứng độc lập.

**C — trần của target là 0,865, nên 0,33 không đổ được cho nhiễu.** Cắt đôi panel **theo thời gian**
(nửa đầu vs nửa sau cửa sổ) rồi tương quan hai nửa theo ô: ρ = **0,865**; riêng ô được poll dày
(≥500 poll, n=6.234) là **0,948**. Target rất ổn định ⇒ proxy đang nắm **38%** lượng tín hiệu **chứng
minh được là nắm được**. Đây là phép "gate theo tỉ số, không theo mức tuyệt đối" mà E-DQ7c đã dựng cho
recall, nay áp cho hàm mục tiêu: báo cáo **`skill = ρ_proxy / ρ_ceiling`**.

**D — trọng số KHÔNG phải nút thắt; tập feature mới là** (kết quả bác bỏ **P1**, xem mục đó). NNLS không
âm trên log1p, 20 cột (10 feature × k0/k-ring 1), LOPO 64 tỉnh, 11.628 ô (`polls ≥ 100`):

| Cấu hình                                                  |               ρ |
| ----------------------------------------------------------- | ---------------: |
| NNLS fit đầy đủ,**LOPO**                          | **+0,329** |
| NNLS fit đầy đủ, in-sample                              |           +0,335 |
| `pop` + road (fit)                                        |           +0,287 |
| **đảo ngẫu nhiên chính bộ trọng số vừa fit** | **+0,266** |
| `pop` đơn độc                                         |           +0,261 |
| **trần (split-half)**                                | **+0,865** |

Đảo trọng số chỉ mất **0,06**. Fit tối ưu hơn "không làm gì" **+0,07**. Trọng số fit được đổ chủ yếu vào
`n_mall_k0` (0,50), `n_fuel_k0` (0,19), `n_parking_off_k0` (0,14) — và `n_parking_off` chính là feature
mà E-DQ7c đã cảnh báo **recall 8,6% + thiên lệch đô thị 2,67**.

**E — lỗ hổng support: 644 ô, và nó là lỗi cấu trúc chứ không phải thiếu dữ liệu.** 644 ô cung có **mọi**
input proxy = 0 (686 trạm); **488** ô trong đó có xe sạc thật. Trong MCLP, trọng số 0 nghĩa là **không
bao giờ được chọn** ⇒ model **mù cấu trúc** với đúng những nơi đã có bằng chứng trực tiếp là có người
dùng. Toàn bộ 644 ô có `pop = 0`, nhưng **99,9% CÓ `road_access_m > 0`** ⇒ **không phải E-DQ8**, mà là
tập feature không có số hạng nào sống sót ngoài khu dân cư. Số hạng **catchment k-ring** vá được phần
lớn:

|                 | ô zero-input | (có`occ>0`) | ρ equal-weight |
| --------------- | ------------: | -------------: | --------------: |
| k0 (hiện tại) | **644** |            488 |          +0,320 |
| k1              | **168** |            124 |          +0,282 |
| k2              |  **74** |             56 |          +0,253 |

⚠️ Đọc kỹ: k-ring **vá support nhưng làm nhoè phân biệt** khi dùng trọng số đặt tay. Vì vậy phải **thêm
cột k-ring BÊN CẠNH k0**, để bước fit tự chọn — bản fit thực tế đã đặt trọng số lên **cả hai** khối
(`n_mall_k0` 0,50 **và** `n_apartment_complex_k1` 0,078). Tuyệt đối **không thay** k0 bằng k-ring.

**F — hai khuyết tật của target làm hỏng mọi phép fit ngây thơ:**

- **Thiên lệch số lần poll.** ρ(`n_polls`, `occ_mean`) = **+0,501**; `occ_mean` = **0,115** ở trạm
  <200 poll (n=4.885) so với **1,729** ở trạm ≥1000 poll (n=4.850). Poll **không phải mẫu thời gian
  đều** ⇒ trung bình-theo-dòng là ước lượng **chệch** của trung bình-theo-thời-gian.
- **Kiểm duyệt phải (right-censoring) 65,8%.** 65,8% trạm chạm trần số súng trong tuần (trung vị số
  súng = 1); **0,7%** *vượt* trần — đây là **lỗi join/dữ liệu thật**, cần cổng riêng. Ô bận nhất chính
  là ô bị cắt ngọn nhiều nhất.

Ngoài ra: **1.779/12.811** ô cung không thấy một xe nào trong 7 ngày · **3.417/19.218** trạm có chuỗi
toàn 0 · **81** ô cung không có mặt trong lưới `demand_h3`.

**Vì sao vấn đề này chặn.** Ở trạng thái hiện tại `demand_weight` ≈ `pop` cộng trang trí, nên MCLP suy
biến về "phủ nhiều dân nhất" — đúng cái baseline ngây thơ mà cả dự án tồn tại để đánh bại. Một proxy hơn
**chính bộ trọng số bị đảo của nó** đúng 0,06 thì không đỡ nổi phát biểu "vị trí đề xuất tốt hơn xếp
hạng theo dân số". Và 488 ô mù xoá đúng nhóm vị trí mà proxy lẽ ra tạo ra giá trị vượt `pop`: hành lang
cao tốc và điểm dừng nghỉ.

**Seam bàn giao (29/07) — chia theo TẦNG, không theo vấn đề.** E-DQ7d nằm vắt qua ranh giới data/model
nên bàn giao nguyên khối sẽ đảo ngược điểm chạm interop #1 (Kỳ không thể vừa nhận `demand_weight` từ
Giang vừa sở hữu việc hiệu chuẩn nó). Chốt:

| Việc                                                                                                                                                           | Chủ                            | Lý do                                                              |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- | ------------------------------------------------------------------- |
| **Target `occ_h3`** — trung bình **có trọng số thời gian**, khử nhiễu công suất, cờ censoring, freeze vào MANIFEST (**E-DQ10**) | **Giang**                 | kỹ thuật dữ liệu trên telemetry evcs — thuần tầng dữ liệu |
| **Harness `features/demand_validation.py`** + bộ cổng QA                                                                                              | **Giang**                 | cùng khuôn`osm/validate.py`; là *cổng*, không phải model  |
| **`demand_weight`**: dạng hàm, trọng số, **feature dòng chảy mới**                                                                         | **Kỳ**                   | gộp với**P1**; là quyết định mô hình                  |
| Vá lỗ hổng support 644 ô (k-ring + flow)                                                                                                                    | **Kỳ** (Giang cấp cột) | —                                                                  |

⚠️ Seam này **cần Kỳ xác nhận ở buổi bàn giao 01/08** — nó là thoả thuận hai người, không phải quyết
định một chiều.

**Đề xuất xử lý (D1–D8) — Kỳ chốt:**

1. **D1 — tách HARNESS khỏi TRỌNG SỐ** (nguyên tắc R1 của E-DQ7b, lần áp thứ ba). `demand_validation.py`
   chấm điểm **bất kỳ** proxy nào; `build_demand_proxy.py` (hiện là stub 5 dòng) sinh trọng số. Đổi
   chính sách = chấm lại vài giây, không phải dựng lại target.
2. **D2 — dựng `occ_h3` cho tử tế.** Trung bình có trọng số thời gian (hình thang trên poll không đều)
   thay cho trung bình-theo-dòng; khử công suất bằng **offset `log(số súng)`** hoặc **phân tầng AC vs
   DC/MIXED** (hai quá trình cầu khác nhau, chênh 13×); loại trạm chết telemetry **tường minh** thay vì
   để nó đọc thành cầu = 0; coi trần súng là **kiểm duyệt phải** (Tobit/Poisson censored) và báo cáo tỉ lệ.
3. **D3 — chỉ đánh giá trên 12.811 ô cung, và nói thẳng điều đó.** Không bao giờ tính ρ trên 254k ô với
   số 0 ngầm. Phân tầng theo tỉnh và tam phân vị `pop`; câu hỏi đúng đắn là *"trong những ô đều đã có
   trụ, proxy có xếp ô bận lên trên không?"*. Ràng buộc chọn mẫu: xem **P2**.
4. **D4 — gate theo `skill = ρ/0,865`, không theo mức tuyệt đối.** Hiện tại **38%**.
5. **D5 — vá 644 ô bằng cấu trúc, không bằng sàn.** Sàn dương là **bịa ra cầu**; cách trung thực là một
   feature thật sự khác 0 ở đó. Thêm cột k-ring **bên cạnh** k0, k = 2–3 cho khớp `R = 3 km` / `d = 0,98 km` (**P4**).
6. **D6 — thêm covariate DÒNG CHẢY; phần tín hiệu còn thiếu nằm ở đó.** Dẫn từ `.pbf` **đã freeze**
   (không phá provenance, khác bài học Overpass ở 7c): betweenness centrality mạng đường · khoảng cách
   tới nút giao cao tốc · **91 đối tượng `highway=services|rest_area`** mà E-DQ7b đã tìm ra (đang chờ
   làm anchor **T3**).
7. **D7 — CẤM feature dẫn từ cung.** Riêng số súng đã cho ρ = 0,773: đưa vào sẽ được một ρ rất đẹp và
   một model vô dụng, phát biểu "hãy đặt trạm ở nơi đã có trạm". Cùng doctrine với "recall không được
   nhân/chia vào feature" của E-DQ7c.
8. **D8 — khuyến nghị: dùng occupancy làm TRỌNG TÀI, chưa phải THẦY.** Vì fit chỉ mua +0,07 (và +0,06
   so với trọng số đảo), trước mắt nên giao một chỉ số **minh bạch** `pop` + catchment + flow, và để
   đóng góp của 7d là **cái cổng**. Chỉ nâng lên `demand_weight` fit khi tập feature vượt cổng
   `proxy_beats_scramble` với biên thật. Cách này cũng né được thiên lệch chọn mẫu ở D3, thứ hiện
   **không có instrument** để hiệu chỉnh.

**QA gate đề xuất — 12 cổng, kèm giá trị HIỆN TẠI.** Dự án này đã ship **3 cổng không bao giờ FAIL được**
(`poi_coords_in_vn` · `road_mt_le_total` · `poi_no_dup`) ⇒ **mỗi cổng 7d phải được chứng minh là FAIL
trên một proxy cố ý làm hỏng** trước khi được tính là cổng.

| Cổng                                                                                               |                           Giá trị hiện tại | Trạng thái                                            |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------: | ------------------------------------------------------- |
| `no_zero_weight_where_charging`                                                                   |                               **488** ô | **FAIL**                                          |
| `proxy_beats_scramble ≥ δ` (LOPO)                                                               |                            +0,329 vs**+0,266** | **FAIL** ở mọi δ hợp lý                      |
| `target_poll_bias ≤ δ`                                                                          |                                **0,501** | **FAIL** (trước khi trọng số hoá thời gian) |
| `occ_not_capacity` — ρ(target, súng) sau khử                                                  |                                **0,773** | **FAIL**                                          |
| `proxy_beats_pop_only ≥ δ`                                                                      |                               **+0,069** | biên giới                                             |
| `skill_vs_ceiling = ρ/0,865`                                                                     |                                 **0,38** | mục tiêu gate                                         |
| `censoring_rate` (báo cáo + trần)                                                              | **65,8%** · **0,7%** vượt trần | WARN + FAIL phần vượt                                |
| `target_window_covers_week`                                                                       |              **7,15 ngày**, đủ 7 thứ | PASS (WARN mùa vụ —**P3**)                     |
| `no_supply_features` · `weights_nonneg` · `spatial_cv_only` · `demand_defined_on_254035` |                                             — | cơ học, chặn sửa đổi tương lai                  |

**Limitation (`DOC`) — đã có dòng register riêng, không nhân bản:**

- **Thiên lệch chọn mẫu** — occupancy chỉ tồn tại ở nơi VinFast **đã xây**, nên fit chỉ học được *"đã có
  trụ ở đây thì bận đến đâu"*, **không bao giờ** học được *"đặt trụ ở đây thì có bận không"*. Không có
  instrument ⇒ không hiệu chỉnh được trong scope. → **P2** (⊘ DOC → FUTURE).
- **Cửa sổ 7,15 ngày tháng 7/2026** ⇒ không thấy mùa vụ, Tết, thời tiết. → **P3** (⊘ DOC → FUTURE);
  mốc thời gian neo ở **P9**/**E-DQ10** (`snapshot_id = 2026-07-20`).
- **Phần dư tới trần 0,865 có phần KHÔNG thuộc về ô.** Giá, thương hiệu, trụ nằm ở cổng nào của TTTM,
  có chắn barrier hay không — những thứ ở **mức trạm**, một lục giác 0,83 km² không thể biết. Nghĩa là
  ngay cả tập feature hoàn hảo cũng **không** đạt 0,865.
- **`n_parking_off` là feature độ tin thấp** (recall 8,6%, thiên lệch đô thị 2,67 — E-DQ7c) nhưng bản
  fit lại đặt trọng số lớn thứ ba lên nó ⇒ phải theo dõi, đây là ứng viên hàng đầu cho hiện tượng
  trọng số bám vào nhiễu.
