# E-DQ9 — Grid toàn quốc vs MVP 1 thành phố (bước 1)

`🟡 SIMPLIFY · ☑ chốt 2026-07-27 · Owner: Giang`

**Chẩn đoán:** `demand_h3` được build ở **quy mô toàn quốc** (**268.404 ô** res 8 phủ toàn VN), nhưng
MVP chỉ cần chạy trên **1 thành phố**. Nếu mọi bước hạ nguồn (land-use, buildable, candidate, coverage)
đọc thẳng toàn bảng thì (a) chi phí giải MCLP nổ vượt trần 3.000 candidate (**P5** cổng ③), và (b) demand
ở **rìa AOI** bị coi là "chưa phủ" oan vì trạm phủ nó có thể nằm ngoài cửa sổ. Cần một cơ chế **cắt lưới
về đúng vùng nghiên cứu** mà **không** fork code giữa chế độ MVP-thành-phố và toàn-quốc — nếu không, hai
đường chạy sẽ trôi khỏi nhau (biến thể **doc-drift** của **P6**).

**Cách xử lý — một trừu tượng AOI, duck-typed, một đường code cho cả hai chế độ.** Trọn bộ nằm ở
[`src/ev_siting/aoi.py`](../../../src/ev_siting/aoi.py):

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

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
