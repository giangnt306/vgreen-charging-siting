# E-DQ8c — Dân KHÔNG phục vụ được: mẫu số (bước 10c)

`⚪ DOC → policy · ☐ Open · Owner: Giang/Kỳ`

**Không phải việc làm sạch.** Dư sau 8b: **225 ô / 42.576 người** giữ tại chỗ có nhãn — **222 ô** ngoài mọi polygon
xã VNSDI (đảo/vắt biên) và **3 ô** ở xã không có đất vừa built-up vừa `DIRECT`. Cụm lõi của nhóm cô lập thật là
xóm kênh rạch **ĐBSCL** (9,8–10,0 N / 104,9 E, `frac_water` 0,43–0,66, `built_up_frac` 0,006–0,099): người
**thật**, đi lại bằng **thuyền**. Không có phép làm sạch nào biến họ thành phục vụ được, và cố "sửa" là bịa.

**Quyết định phải ra (chưa ra) — 3 việc:**

1. **`demand_servable`** — cột boolean ở `demand_h3`, `False` cho ô `pop_src LIKE 'UNREPAIRED%'`.
2. **`coverage_pop` phải trừ nhóm này và CÔNG BỐ số bị trừ.** Để đọng thì mọi chỉ số coverage bị hạ ~0,04% bởi
   một khối lượng **không thể phủ theo định nghĩa** — và với `radius_m` hiện tại (500 m,
   [`config/params.yaml`](../../../config/params.yaml)) mỗi ô chỉ phủ chính nó, nên ô roadless là **chính xác không phủ
   được**. Mục tiêu coverage đặt trên mẫu số đó là không đạt được **theo cấu tạo**.
3. **Lưới phải thành tessellation** — việc còn lại của 8a/A4: **76 ô chứa 83 trạm đang vận hành** không có dòng ở
   `demand_h3`, `demand_h3_clipped_out`, lẫn `buildable_h3`, vì lưới là **hợp của các ô CÓ đặc trưng**
   (`pop>0` ∪ đặc trưng OSM), không phải phủ hình học. Chúng vô hình với optimizer ở **cả hai** vai cung và cầu,
   và bơm nhiễu vào tử số cổng ⑥ `supply_cells_have_road_access` (100/12.811). Bậc thật của chúng (tính từ bảng
   đường): **50 `ADJACENT` · 8 `NEAR` · 18 `ISOLATED`**.
   > ⚠️ **Thứ tự bắt buộc: A4 phải xong TRƯỚC bước này** — và nó đã xong. Làm tessellation trước A4 sẽ đưa 76 ô
   > đó vào lưới với bậc mặc định `ISOLATED` ⇒ loại cứng **76/76** ô đang chứa trạm thật, và bản sửa lưới sẽ trông
   > như một hồi quy. Cần cổng mới `grid_contains_all_supply_cells` (**FAIL**, không WARN).
   >

**Chưa làm vì đây là thay đổi ĐỊNH NGHĨA LƯỚI**, kéo theo số dòng của `demand_h3`/`buildable_h3`/AOI national và
mẫu số của cổng ⑥ ⇒ cần chốt phạm vi trước (gộp vào **E-DQ3**, vốn cần cùng artefact polygon, là lựa chọn rẻ nhất).

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
