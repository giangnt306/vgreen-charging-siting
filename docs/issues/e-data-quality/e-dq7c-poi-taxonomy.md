# E-DQ7c — POI thiếu & lẫn đơn vị (bước 6)

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
   (một cột/lớp tag) và mọi cột vô hướng do [`poi_semantics.derive()`](../../../src/ev_siting/data/osm/poi_semantics.py)
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
[`osm/validate.py`](../../../src/ev_siting/data/osm/validate.py): ① `poi_points_has_class_columns` (chặn artefact cũ) ·
② **`poi_object_once`** — một đối tượng OSM = một dòng (khoá cũ có `category` nên cho phép 2) ·
③ **`poi_dup_resolved`** — đối soát `bản chính + bản trùng = tổng dòng`, không bản trùng nào mồ côi ·
④ `apartment_levels_observed_share ≥ 0,25` (proxy quy mô phải là số **đo**; thực đo **36,1%**) ·
⑤ **`poi_layer_sum_eq_points`** — Σ bảng lớp = số bản chính `in_vn` theo lớp (bắt **lệch nhãn cột**, đúng vai cổng
② của E-DQ7b) · ⑥ **`poi_complex_sum_eq_groups`** — Σ khu trên lưới = số `complex_id` phân biệt (ai đổi sang đếm
theo toà là FAIL ngay) · ⑦ `components_has_poi_columns` (chặn artefact còn `n_poi`/`n_parking`) ·
⑧ **`poi_recall_fuel ≥ 0,30`** và ⑨ **`poi_recall_bias_* ≤ 2,0`** — hai **cổng ngoại vi** duy nhất của tầng POI.
`counts_match_in_vn_poi` viết lại theo lớp + trừ RESTRICTED.

**Kết quả** (chạy 28/07 — `make osm && make demand && make candidates CITY=hanoi`):

| Đại lượng                         | Trước          | Sau                        | Ghi chú                                                                                                                                             |
| ------------------------------------- | ---------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `n_poi`                             | 9.679            | **khai tử**         | →`n_mall` 252 + `n_dept_store` 1.133 + `n_supermarket` 1.386 + `n_market` 1.661 + `n_apartment` 5.157                                     |
| `n_parking`                         | 2.463            | **khai tử**         | →`n_parking_off` 2.147 + `n_parking_street` 149 (−34 trùng, −133 RESTRICTED)                                                                 |
| `n_fuel`                            | 4.964            | **4.830**            | −134 bản trùng node/way                                                                                                                           |
| Toà chung cư →**khu**        | 5.157            | **1.370**            | hệ số**3,76×** — đơn vị mới sánh được với `n_mall`                                                                              |
| Ô lưới`demand_h3`                | 254.035          | **254.035**          | không đổi (E-DQ7a/7b giữ nguyên bit-level)                                                                                                      |
| `pop` · `road_access_m` · E-DQ8 | —               | **không xê dịch** | 99,621 M · 721.785 km · 6.350 ô*(số dân của dòng này là tiền-7e; xem[E-DQ8a](e-dq8a-access-tier.md) cho 1.241.833)* |
| Candidate Hà Nội                    | 1.711 (5/5 gate) | **1.707 (5/5 gate)** | T0 1.409 · T4 130 · T1**108** · T2 60                                                                                                       |

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
  tầng POI thì phải làm **trước E-DQ7d** (xem [§ thứ tự](../../known-issues.md#3-thứ-tự-xử-lý--ràng-buộc-phụ-thuộc)).
- **Không nguồn nào không thiên lệch.** Overture/FSQ suy từ POI thương mại nên **cũng** lệch đô thị, có khi hơn OSM
  ở nông thôn VN. Vì vậy doctrine giữ nguyên bất kể nguồn: **không bao giờ lọc cứng theo việc VẮNG POI**, và
  **T4 gap-fill vẫn bắt buộc** — đây chính là biện minh định lượng cho câu "OSM thưa ở vùng ven" ở
  [`build_candidates.py`](../../../src/ev_siting/features/build_candidates.py).
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

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
