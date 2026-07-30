# E-DQ1 — Toạ độ placeholder / trùng khít (bước 3)

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
[`fix_coords.py`](../../../src/ev_siting/data/evcs/fix_coords.py), chạy **sau** E-DQ2 (nhận sẵn `DUP_COORD_SUSPECT`):

- **Chỉ detector A điều khiển `coord_resolved`.** (1) không placeholder → `coord_src='evcs'`, giữ toạ độ. (2)
  placeholder nhưng official có toạ độ **tốt** (không placeholder, gần centroid-tỉnh) & đổi điểm → snap
  `coord_src='official'` (thực tế VN = **0** vì official mang cùng placeholder; giữ tier theo nguyên tắc
  official-first & phòng hộ). (3) placeholder không cứu được → `coord_resolved=False`, `h3_r8=NULL`, **loại
  khỏi cung** (không neo phủ ở vị trí chưa biết — giống `is_operational`/`is_primary`).
- **Provenance (đảo ngược & geocode tương lai):** `lat_raw`/`lng_raw` (giữ gốc), `coord_src`,
  `coord_fix_dist_m`, `coord_resolved`; **`h3_r8` tính lại** từ toạ độ đã resolve. Cung/coverage/**T0** thêm
  điều kiện `coord_resolved` ([`build_candidates._load_stations`](../../../src/ev_siting/features/build_candidates.py)).

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

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
