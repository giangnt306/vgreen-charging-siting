# E-DQ4 — Cấu hình đọc ở tầng SAI: mảng SỐNG vs sổ TÀI SẢN (bước 11)

`🟠 DONE · ☑ chốt 2026-07-30 · Owner: Giang`

**Register cũ ghi triệu chứng, không ghi khuyết tật.** Dòng cũ: *"cấu hình khuyết
(`current_type`/`max_power_kw`/`total_power_kw` null, `num_connectors=0`)"* = **282 dòng (1,45%)**. Đo lại 30/07:
282 dòng ấy **có thật**, nhưng chúng chỉ là phần mà lỗi **tình cờ nhìn thấy được**. Khuyết tật thật chạm **8,1%
trạm** và **9,0% tổng số súng toàn quốc**, và **không một phép đếm null nào thấy được nó vì không có gì bị null**.

**Chẩn đoán — một cơ chế duy nhất giải thích cả bốn bậc.** [`build_master_evcs.py:33`](../../../src/ev_siting/data/evcs/build_master_evcs.py#L33)
ghi `totalEvse` là *"số súng THẬT"*. **Sai.** `evsePowers` là **mảng trạng thái SỐNG**: một EVSE chỉ xuất hiện khi nó
đang được đăng ký **và** đang báo cáo. Bằng chứng, crosstab `depot` (trạng thái sống) × `evse_powers` rỗng trên tab
VinFast:

| `depot`        |      n | `evse_powers` rỗng |
| ---------------- | -----: | --------------------: |
| `Available`    | 14.819 |           **0** |
| `AllBusy`      |  1.237 |           **0** |
| `Maintaining`  |  3.331 |                   177 |
| `OutOfService` |     40 |                    25 |

Registry chính thức **hành xử y hệt**: trong 282 dòng null, official có dòng EVSE cho đúng **25** trạm
`charging_status=OUTOFSERVICE` và **không có dòng nào** cho **177** trạm `INACTIVE`. ⇒ **CẢ HAI nguồn đều là feed
trạng thái sống, không phải sổ đăng ký tài sản.**

Vậy E-DQ4 là lỗi **NGỮ NGHĨA**, cùng họ với **E-DQ7b** (`road_len`) và **E-DQ8a** (đo ở thang sai) — **không** phải
lỗi thiếu dữ liệu. Tắt hết mảng → null; tắt **một phần** → đọc thiếu âm thầm; tắt **cả một loại dòng điện** →
`current_type` sai.

**Bốn bậc đo được** (artefact đã freeze, `snapshot_id=2026-07-20`; join `store_id == station_code`, phủ
**19.243/19.507 = 98,6%**):

| Bậc | Khuyết tật                            | Đo được                                                                                                                                                                                                                                                             |
| ---- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A    | null cả 4 trường (triệu chứng cũ) | **282**; **134** trong tập cung (19.015), **toàn bộ** `MAINTENANCE`; **60/12.811** ô cung đọc tổng công suất **= 0**; cả 130 ô có panel đều `occ_mean = 0,000`                                                          |
| B    | **đọc thiếu ÂM THẦM**        | **1.568 trạm (8,1%)** ít súng hơn registry, **0 trạm nhiều hơn** — bất đối xứng **một chiều** = dấu hiệu TRUNCATION, không phải nhiễu. Thiếu **6.249 súng (9,0%)**; tập cung **1.498 trạm / +6.055 súng (+9,9%)** |
| C    | `current_type` sai                    | **531** trạm; hầu hết là `DC` mà thật là **`MIXED`** (chính các súng AC bị thiếu)                                                                                                                                                           |
| D    | `total_power_kw` sai ngữ nghĩa      | **21.806** tủ (`physical_reference`) mang **≥2 hồng, 100% cùng rated kW + cùng standard** ⇒ hai hồng trên MỘT tủ. Σ theo súng **3.159.206 kW** vs Σ theo tủ **1.731.991 kW** = **1,82×**                                 |

**Lệch theo loại dòng điện — chính là lý do bậc C tồn tại.** Truncation **không đều**: AC (≤25 kW) thiếu **14,2%**
(30.026 vs 34.981) so với DC **3,8%** (32.868 vs 34.162); tier tệ nhất **7,0 kW thiếu 56,1%** (2.743 vs 6.255), rồi
250 kW **22,4%**. Vì AC bị tắt nhiều hơn, trạm MIXED mất hết phần AC và **trông như DC thuần**.

**Kiểm chứng NGOẠI VI — không cần registry** (đúng khuôn `poi_recall.py` của E-DQ7c và neo occupancy của E-DQ7d, nay
áp cho cấu hình): **159 trạm ô tô** (132 trong tập cung) ghi nhận **số xe sạc đồng thời > số súng lắp đặt**
(`ts_val_max > num_connectors`), vượt tới **11 súng** — **bất khả thi về vật lý**. Registry giải **132/132** trong tập
cung (official guns ≥ `ts_val_max` ở **mọi** trường hợp). Telemetry là **NHÂN CHỨNG** cho công suất lắp đặt, và
`ts_val_max` **đã có sẵn trong master** nên phép kiểm này miễn phí.

**Cách xử lý — tách tầng TÀI SẢN khỏi tầng TRẠNG THÁI SỐNG** (khuôn 2 cột của **E-DQ7b R1**; tuyệt đối **không ghi
đè**, **không xoá dòng**), ở [`resolve_config.py`](../../../src/ev_siting/data/evcs/resolve_config.py), chặn ở
`transform_canonical`:

- **LIVE (giữ nguyên):** `num_connectors` · `max_power_kw` · `total_power_kw` · `current_type` = *"đang báo cáo"*.
  `num_connectors = 0` được **giữ nguyên là giá trị LIVE ĐÚNG** (không có gì báo cáo) — sai lầm cũ là **đọc** nó
  thành "không có súng", không phải bản thân con số.
- **ASSET (8 cột mới):** `n_guns_installed` · `max_power_kw_asset` · `site_power_kw` · `nameplate_power_kw` ·
  `current_type_asset` · `config_src` · `config_resolved` · `n_guns_imputed`.
- **Quy tắc hợp giải: official-first CÓ HỢP `max()`.** Official-first theo **P8** + [[vinfast-official-join-key]];
  phần **mới** là `max()`: **cả ba nguồn đều là chặn DƯỚI**, nên phải **hợp** thay vì ghi đè —
  `n_guns_installed = max(registry, evcs Σ totalEvse, ts_val_max)`. `max()` phủ luôn 264 trạm không join được và
  đóng cả 159 mâu thuẫn vật lý. (Nếu evcs > registry thì registry mới là bản cũ ⇒ official-first **thô** sẽ sai;
  cổng ③ canh đúng tiền đề này.)
- **`site_power_kw` là đọc BẢO TOÀN:** Σ theo **tủ** = `max(rated)` trên từng `physical_reference`. 831 dòng registry
  có `physical_reference` NULL → không nhóm được → giữ per-gun ở đó (**không đoán**).
- **`current_type_asset`** suy từ tầng tài sản ⇒ sửa 531 trạm; **đây là cột E-DQ7d phải dùng để phân tầng**, không
  phải `current_type`.

**Cờ tường minh** (vào `quality_flags`): `CONFIG_TRUNCATED` **1.568** · `CURRENT_TYPE_CORRECTED` **531** ·
`POWER_CABINET_SHARED` **4.317** · `CONFIG_UNKNOWN` **256** · `CONFIG_LOWER_BOUND` **1**.

**Kết quả** (19.507 trạm; mọi số cũ **bất động**: 19.178 primary · 19.015 cung · 38 placeholder · 758 mismatch):

- `config_src`: `OFFICIAL` **19.243** · `UNKNOWN` **256** · `EVCS_LIVE` **7** · `TELEMETRY_BOUND` **1**.
- Súng **ĐANG BÁO CÁO → LẮP ĐẶT**: toàn bộ **62.924 → 69.174**; tập cung **61.372 → 67.427 (+9,9%)**.
- kW: LIVE `total_power_kw` **3.010.966** · ASSET nameplate **3.159.206** · ASSET **`site_power_kw` 1.731.991**
  ⇒ con số công bố được cho công suất lắp đặt là **~1,73 GW**, không phải ~3,0 GW.
- `config_resolved` trên tập cung **0,9929**; **8/8 cổng PASS**.

**CHÍNH SÁCH DƯ — 256 trạm không nguồn nào điền được** (176 VinFast `INACTIVE` + **80 mạng thứ ba**). Áp đúng khuôn
**E-DQ8c** ("công bố mẫu số", không để đọng):

1. `config_resolved=False`, `config_src=UNKNOWN`, cờ `CONFIG_UNKNOWN`, **mọi cột ASSET = NULL** (cổng ⑥ chặn việc
   điền ngầm).
2. **GIỮ** làm điểm phủ / anchor **T0** brownfield — chúng có hạ tầng vật lý, nhất quán quyết định **giữ
   `MAINTENANCE`** của **P8**.
3. **LOẠI khỏi mọi mẫu số CÓ TRỌNG SỐ CÔNG SUẤT**, và **công bố số bị loại** — đã cài ở
   `build_covered0._capacity_accounting` (khối `config_capacity` trong report).
4. `n_guns_imputed` (median theo tỉnh × loại trạm) **chỉ để phân tích độ nhạy**, **không bao giờ** là giá trị mặc
   định. Test `test_imputation_never_leaks_into_installed` khoá điều này.

**8 cổng QA CÓ THỂ FAIL.** Trước E-DQ4 **không có cổng nào cho cấu hình**: `INCOMPLETE_CONFIG` chỉ tồn tại dưới dạng
**comment** ở `transform_canonical.py`, và `validate.py` không kiểm một trường cấu hình nào (`REQUIRED_COLS` còn
không liệt kê chúng). Đây là khuôn *"cổng kiểm đúng cái sinh ra lỗi nên không bao giờ FAIL"* của **E-DQ7c**
(`poi_no_dup`) / **E-DQ7e** (dải "97–98 triệu") — ở E-DQ4 **còn tệ hơn: không có cổng nào cả**.

| #  | Cổng                             | Bắt được gì                                                                                 |
| -- | --------------------------------- | ------------------------------------------------------------------------------------------------ |
| ① | `guns_ge_observed_max`          | **NEO NGOẠI VI** — cổng duy nhất bắt truncation **không cần nguồn thứ hai** |
| ② | `no_silent_zero`                | đang vận hành + đã resolve mà 0 súng                                                      |
| ③ | `reporting_le_installed`        | tiền đề hợp`max()` bị vỡ (mảng sống vượt tầng tài sản)                            |
| ④ | `asset_layer_complete`          | dòng`config_resolved` mà thiếu cột ASSET                                                   |
| ⑤ | `site_power_le_nameplate`       | bậc D quay lại (site > Σ nameplate); report luôn tỉ số**1,82×**                     |
| ⑥ | `unknown_is_explicit`           | **điền ngầm** cho dòng UNKNOWN (đúng thứ chính sách dư cấm)                     |
| ⑦ | `row_reconciliation`            | `input == resolved + chặn dưới + unknown` (không dòng nào bốc hơi)                     |
| ⑧ | `config_resolved_rate ≥ 0,985` | đo trên tập**CUNG**, không trên toàn bảng                                           |

Thêm **cổng ngoại vi ở tầng master** (`validate.py`): `ts_val_max > num_connectors` → **WARN** kèm số, *không*
CRITICAL — 159 mâu thuẫn là **thuộc tính của NGUỒN**, master không sửa được; cổng CRITICAL đặt đúng chỗ sửa được là
① của `resolve_config`. Các cột cấu hình + `ts_val_max` cũng đã được thêm vào `REQUIRED_COLS`.
**19 test** khoá ngữ nghĩa ở [`tests/test_config_semantics.py`](../../../tests/test_config_semantics.py), trong đó **7 test
chứng minh từng cổng CÓ THỂ FAIL**.

**Ảnh hưởng lên `E-DQ7d` — nói đủ, không nói quá.** ρ(số súng trong ô, occ) đi **0,7711 → 0,7745**; ô poll dày
(≥500, n=6.236) **0,7937 → 0,8021**. E-DQ4 **KHÔNG cứu** proxy cầu (verdict **0,33/0,865** của 7d đứng nguyên) và
**không** đổi thứ hạng ô đủ để MCLP quan tâm. Nó sửa đúng hai thứ 7d cần: **biến phân tầng** (`current_type_asset`,
531 trạm) và **mẫu số exposure** để phát biểu được *"cầu trên mỗi súng"* — điều mà chẩn đoán **B** của 7d
("target thô **77%** là công suất") biến thành **điều kiện tiên quyết**, chứ không phải tuỳ chọn.

**Limitation (`DOC`):**

- **`site_power_kw` cần MỘT lần đối chiếu spec phần cứng.** Nhóm theo `physical_reference` cho thấy 21.806 tủ
  **≥2 hồng, 100% cùng rated kW + cùng standard** — rất mạnh nhưng **chưa phải bằng chứng** rằng tủ không cấp đủ
  rated cho cả hai hồng cùng lúc. Nếu VinFast **chia** công suất thì `max()` đúng; nếu **dual-power** thì `sum()`
  đúng. Cả hai đọc đều có sẵn (`site_power_kw` vs `nameplate_power_kw`) nên đổi kết luận **không phải chạy lại
  pipeline** — nhưng **đừng công bố `site_power_kw` trước khi đối chiếu**.
- **80 trạm mạng thứ ba** (BitCharge · Esky · EBOOST · EV One · ChargeLink · Rabbit EVC · EVPay · "Hỗ trợ cộng
  đồng" · "Trạm sạc Tiền mặt"): evcs.vn **không công bố cấu hình** cho mạng ngoài VinFast và chúng **không có** trong
  registry VinFast ⇒ không nguồn nào điền được. *(Phát hiện phụ cho **E-DQ5**: tên mạng của chúng nằm ở cột `evse`
  của catalog thô — cột đó chứa **tên network**, không phải số súng.)*
- **60 ô cung vẫn đọc công suất 0** sau khi sửa: chúng thuộc đúng 134 trạm `MAINTENANCE` không resolve được, nên
  đây là **giới hạn nguồn**, không phải lỗi hợp giải. Chính sách dư (mục 3) là cách xử lý đúng, không phải imputation.
- **Chỉ có MỘT snapshot.** Vì cả hai feed là trạng thái sống, công suất lắp đặt **chỉ khôi phục đầy đủ được bằng HỢP
  THEO THỜI GIAN**. Một lần crawl `evse_powers` ở ngày thứ hai, hợp bằng `max`, sẽ siết chặt thêm — nhưng nó phải vào
  như **input mới có checksum riêng** dưới **E-DQ10**, **không** được là phép sửa đổi `snapshot_id=2026-07-20`.
- **Nợ đã biết, cố ý KHÔNG sửa ở đây** (cần dòng register riêng): `build_covered0` vẫn lọc bằng `status`/`is_public`
  **thô** thay vì `op_status`/`access`/`is_operational` của **P8**, và `_DIRTY_COORD_FLAGS` vẫn tìm cờ `DUP_COORD`
  mà **E-DQ1** đã thay. Vì vậy `n_covered0` **15.451 ≠ 19.015** của tập cung canonical, và các tổng công suất trong
  `covered0_report.json` mang đúng sai lệch đó. Đã ghi cảnh báo vào docstring của module.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
