# E-DQ7g — Đối chiếu tầng POI với nguồn thứ hai (Overture Places)

`🟠 FIX + DOC · ☑ chốt 2026-08-07 · Owner: Giang`

**Tiền đề khi mở.** E-DQ7c đo được recall OSM **fuel 35,9%** / **parking 8,8%** bằng bằng chứng thực địa nội
bộ, và kết luận "thiếu POI thật". Nhưng phép đo đó chỉ trả lời *thiếu bao nhiêu ở nơi đã có trạm sạc* — nó
không nói thiếu ở đâu trên cả nước, và **không có nguồn nào để bù**. Câu hỏi mở: một nguồn POI thứ hai có
vá được không?

---

## 0. Phát hiện đứng trước mọi phép đo: lớp `PARK` **chưa từng tồn tại**

Verify báo "thiếu công viên". Không phải OSM thưa — `overpass_poi.CATEGORIES` **không có nhóm nào sinh ra
công viên**: 5 nhóm crawl là `fuel` / `parking` / `mall` / `apartments` / `retail`, và
`poi_semantics.classify()` không có nhánh nào trả về `PARK`. Recall của một lớp không tồn tại là 0% theo định
nghĩa, và không phép đo nào phát hiện được vì mọi cổng QA đều lặp theo `CLASSES`.

Đã sửa: thêm nhóm crawl `park` (`leisure=park`) và lớp `PARK` **nối vào cuối** `CLASSES` (cột cũ không đổi
tên, độ ưu tiên cũ không đổi). Crawl 07/08 → **4.188 POI** trong `VN_BBOX`, **4.146** bản chính trong VN.

⚠️ **Cố ý KHÔNG đưa `n_park` vào `DERIVED_COLUMNS`.** Bảng LỚP ghi lại được số đo; biến nó thành covariate cầu
là quyết định của E-DQ7d, không phải hệ quả phụ của việc thêm một nhóm crawl (nguyên tắc C1/C3 của E-DQ7c).
`osm_demand_components_h3` và schema contract **không đổi**.

Hai nhóm cố ý **không** crawl: `leisure=garden` (vườn nhà, phần lớn là sân sau tư nhân) và
`leisure=nature_reserve` (khu bảo tồn — không sinh cầu sạc ô tô).

---

## 1. Nguồn thứ hai: chọn Overture, không chọn số liệu chính thức

Cùng lập luận E-DQ7b/E-DQ7c đã chốt: **không đặt cổng theo số liệu chính thức chưa freeze**, và danh sách
cửa hàng bán lẻ của Sở Công Thương là PDF/xlsx địa chỉ chữ mà E-DQ6 đã cho thấy không geocode được tin cậy.
Overture Places là nguồn duy nhất vừa **phủ toàn quốc**, vừa **có toạ độ**, vừa **dùng lại được về pháp lý**
(CDLA-Permissive-2.0 — *không* share-alike, khác ODbL của OSM; xem F1 trước khi publish).

Quét `s3://overturemaps-us-west-2` release **2026-07-22.0** bằng DuckDB + `httpfs` (predicate pushdown theo
cột `bbox`): **2.192.761** place trong `VN_BBOX`, 153 MB, ~6 phút. Raw giữ **nguyên category gốc** —
đổi định nghĩa lớp = chạy lại `build_poi` (vài giây), không crawl lại.

Sau ánh xạ taxonomy + khử trùng + clip lãnh thổ (fail-closed, cùng polygon `vn_boundary`): **43.446** POI
trong VN, **37,2%** bị cắt vì rơi vào Campuchia/Lào/Thái/TQ — cùng chế độ E-DQ7a, cùng cách xử lý.

---

## 2. Kiểm tra CHẶN: hai nguồn có độc lập không?

Overture hợp nhất Meta ∪ Microsoft ∪ Foursquare ∪ **OpenStreetMap**. Nếu phần lớn điểm ở VN đến từ OSM thì
"Overture nhiều hơn" chỉ là OSM đóng gói lại và mọi so sánh bên dưới vô nghĩa.

Đo: **0,0%** ở cả 8 lớp. Phân bố nguồn: `meta` 42.940 · `AllThePlaces` 362 · `Foursquare` 75 · `Microsoft` 48.
⇒ **Hai nguồn độc lập hoàn toàn ở VN.** Phép đối chiếu hợp lệ.

---

## 3. Số lượng và chồng lấn (trong VN, đã khử trùng, ghép cặp @50 m)

| Lớp | OSM | Overture | Ovt/OSM | trùng | chỉ OSM | chỉ Ovt | % OSM được Ovt phủ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `FUEL` | 4.830 | 2.768 | 0,57 | 805 | 4.025 | 1.967 | **16,7%** |
| `PARK` | 4.146 | 2.682 | 0,65 | 292 | 3.854 | 2.378 | 7,0% |
| `PARKING_OFF` | 2.265 | 637 | 0,28 | 25 | 2.240 | 617 | 1,1% |
| `APARTMENT` | 5.157 | 835 | 0,16 | 62 | 5.095 | 778 | 1,2% |
| `MARKET` | 1.661 | 1.414 | 0,85 | 88 | 1.573 | 1.326 | 5,3% |
| `DEPT_STORE` | 1.133 | 1.492 | 1,32 | 16 | 1.117 | 1.476 | 1,4% |
| `SUPERMARKET` | 1.386 | 6.086 | 4,39 | 308 | 1.078 | 5.725 | 22,2% |
| `MALL` | 252 | 5.758 | **22,85** | 112 | 140 | 5.617 | 44,4% |

**Chồng lấn thấp ở MỌI lớp, và nới bán kính không cứu được:** `FUEL` 16,7% → 20,3% (@100 m) → 23,0% (@200 m).
Nếu lệch là do sai số vị trí thì nới 4× bán kính phải kéo tỉ lệ lên mạnh; nó không. ⇒ **Hai nguồn thấy hai tập
địa điểm khác nhau**, không phải cùng một tập bị lệch toạ độ.

`PARKING_STREET` không có đối ứng bên Overture (taxonomy places không phân biệt đỗ ven đường) — ghi vào
`NO_OVERTURE_EQUIVALENT`, **không** báo "Overture = 0".

---

## 4. Cái bẫy: chênh lệch số lượng **không phải** độ phủ

`MALL` đông gấp **22,85 lần**. Đọc tên thì lộ ngay: `shopping_center` của Overture ở VN gom cả *Sơri Kids*,
*Nệm Anh Thư*, *Coffee FIN*, *Honda Ô Tô Hà Nội*. Đo được thay vì đoán:

| Lớp | OSM % tên có danh từ của lớp | Ovt % tên có danh từ của lớp | Ovt % tên **mâu thuẫn** lớp |
| --- | ---: | ---: | ---: |
| `FUEL` | 45,1% | **93,6%** | — |
| `MARKET` | 79,7% | 40,4% | — |
| `SUPERMARKET` | 39,3% | 51,2% | 4,1% |
| `PARK` | 25,9% | 48,9% | 7,3% |
| `PARKING_OFF` | 5,7% | 35,0% | 10,7% |
| `MALL` | 50,8% | **8,4%** | 5,9% |

("% tên mâu thuẫn" = tên chứa cụm **không thể** thuộc lớp đó: `PARK` chứa "khu công nghiệp"/"nghĩa trang"/
"công ty"; `PARKING_OFF` chứa "gara"/"sửa chữa"/"rửa xe".)

⇒ **`FUEL` là lớp duy nhất sạch nhãn ở phía Overture** (93,6%). `MALL` ở mức 8,4% — con số 22,85× là **nhiễu
taxonomy**, không phải độ phủ; đưa nó vào covariate cầu là đưa vào toàn tiệm tạp hoá. `PARKING_OFF` của
Overture lẫn 10,7% garage sửa xe.

---

## 5. Phép đo có ground truth: recall trên nền độc lập

Dùng lại bằng chứng thực địa của `poi_recall.py` (trạm sạc mà `name`/`address` nêu đích danh một cây
xăng/bãi đỗ) cho **cả hai** nguồn — đây là phép đo duy nhất ở đây có mốc nằm ngoài cả hai:

| Lớp | n mốc | OSM @100 m | Overture @100 m | **hợp nhất** @100 m |
| --- | ---: | ---: | ---: | ---: |
| `FUEL` | 1.407 | 35,9% | 15,3% | **43,7%** |
| `PARKING_OFF` | 852 | 8,8% | 1,3% | **10,1%** |

**Kết luận vận hành.** Overture **không** thay được OSM (recall thấp hơn ở cả hai lớp), nhưng nó **bù thật**:
hợp nhất kéo recall fuel **35,9% → 43,7%** (+7,8 điểm) bằng nguồn hoàn toàn độc lập. Với `PARKING_OFF` thì
+1,3 điểm — **không cứu được**, và §4 giải thích vì sao: 10,7% "bãi đỗ" của Overture là garage.

---

## 6. Độ tươi — chỉ so được một chiều

| | OSM | Overture |
| --- | --- | --- |
| Ngày sửa **mức đối tượng** | ✅ có, 99,1–100% đối tượng | ❌ **không có** |
| Nguồn của ngày | `timestamp` trong `.pbf` đã freeze | `sources[].update_time` |
| Giá trị phân biệt | hàng nghìn | **1** (`meta`, 99% số điểm) |

`update_time` của Overture ở VN là **ngày giao lô** của nhà cung cấp (`2026-07-02` cho toàn bộ `meta`), không
phải ngày từng địa điểm được sửa; mục `sources` còn có một nguồn giả tên `Overture` = ngày build release
(`2026-07-14`). Lấy bừa cái nào cũng cho ra "mọi POI đều mới tinh". `build_poi` loại nguồn giả và ghi
`n_unique_update_time_by_dataset` vào báo cáo; `compare_osm` có cổng theo **tỉ lệ** (`n_distinct/n > 10%`) để
tự tắt phần so độ tươi thay vì in ra một bảng vô nghĩa.

Phía OSM thì đo được thật, và số không đẹp: **p50 `FUEL` = 2023-02-16**, **42,9%** cây xăng chưa ai sửa
trong 5 năm; `DEPT_STORE` tệ nhất (p50 2017-09, **81%** quá 5 năm).

*Giới hạn:* raw Overpass gọi `out center tags` nên **không có** timestamp; ngày sửa lấy từ `.pbf` đã freeze
(ảnh 2026-07-20), nên POI tạo sau ngày đó không có ngày (0,1–0,9%, để NaT, **không** lấp bằng ngày crawl).

---

## 7. Chốt lại

1. **`PARK` là bug thật, đã sửa** — lớp không tồn tại chứ không phải thiếu dữ liệu (§0).
2. **Overture bổ sung, không thay thế.** Chỉ nhập cho `FUEL` (nhãn sạch 93,6%, +7,8 điểm recall).
   Các lớp khác: nhiễu nhãn quá cao để dùng làm covariate.
3. **Chưa nhập vào `demand_h3`.** `overture_poi_h3.parquet` đứng riêng; hợp nhất hai nguồn thành một cột
   feature là quyết định của **E-DQ7d** — cùng ranh giới với `n_park`.
4. **Overture đã vào `MANIFEST.json`** (`make freeze` cần chạy lại: raw có thêm `park.json` + thư mục
   `data/raw/overture/`).

**Tái lập:**

```bash
make overture-fetch       # quét S3 -> data/raw/overture/  (~6 phút, 153 MB)
make overture             # -> overture_poi_points / overture_poi_h3
make poi-timestamps       # ngày sửa OSM từ .pbf đã freeze (~7 phút)
make overture-compare     # -> data/interim/overture/osm_vs_overture.{json,md}
```

**Test:** `tests/test_overture_taxonomy.py` — khoá bảng chữ chung hai nguồn, khoá ánh xạ không nuốt
`amusement_park`/`rv_park`/`playground`, khoá `grocery_store ≠ SUPERMARKET`, và khẳng định ghép cặp không gian
**bằng đúng brute-force** ở 50/100/200/300 m (`poi_semantics.neighbour_pairs` bucket ở res 9 nên chỉ bảo đảm
tới ~185 m — dùng nó ở 200/300 m sẽ **bỏ sót cặp thật** và thổi phồng phần "chỉ có ở một nguồn").
