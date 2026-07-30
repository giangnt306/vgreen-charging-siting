# E-DQ7d — Proxy cầu chưa kiểm chứng ngoại vi (bước 7)

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

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
