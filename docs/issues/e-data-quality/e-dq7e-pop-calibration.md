# E-DQ7e — `pop` chưa hiệu chuẩn tuyệt đối (bước 8)

`🟡 FIX + DOC · ☑ chốt 2026-07-29 · Owner: Giang`

> **Tách đôi (29/07).** Dòng register cũ "`pop` chưa hiệu chuẩn" gộp **hai khuyết tật độc lập về cả nguyên nhân,
> hậu quả lẫn cách sửa**: một phép **rescale toàn quốc** (mức tuyệt đối sai, thứ hạng đúng) và một lỗi **phân bổ
> trong ô** (mức tuyệt đối quốc gia đúng, thứ hạng sai). Gộp chúng buộc phải chọn một mức độ ưu tiên duy nhất cho
> hai thứ khác hẳn nhau, và — nghiêm trọng hơn — làm cờ `POP_DENSITY_OUTLIER` được thiết kế cho vế thứ hai lại
> **đo bằng đại lượng của vế thứ nhất**. Vế phân bổ nay là **[E-DQ7f](e-dq7f-pop-dasymetric.md)**.

**Chẩn đoán.** [`paths.py`](../../../src/ev_siting/data/worldpop/paths.py) trỏ vào `vnm_ppp_2020_constrained.tif` —
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
**bất biến từng bit**, nên [§ thứ tự](../../known-issues.md#3-thứ-tự-xử-lý--ràng-buộc-phụ-thuộc) nói đúng khi xếp `E-DQ7d` chạy trước — nhưng trước 29/07
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
3. **MANIFEST + `vintage`** cập nhật ở [`manifest.py`](../../../src/ev_siting/data/provenance/manifest.py); đổi nguồn
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
  chuẩn; (b) [`vn_boundary.geojson`](../../../data/interim/osm/vn_boundary.geojson) đang có **40 polygon adm4** gồm cả
  ba bản "cũ" (`An Giang cũ`, `Lào Cai cũ`, `Quảng Trị cũ`) so với **34 tỉnh** sau sáp nhập 2025 ⇒ phải qua quy
  tắc phân định của **E-DQ3** trước. Làm sớm = nắn dân số bằng một bảng ranh giới **chồng lấn**.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
