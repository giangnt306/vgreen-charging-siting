# E-DQ7a — POI ngoài lãnh thổ VN (bước 4)

`🔴 FIX (chặn) · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán.** `overpass_poi.py` query bằng `VN_BBOX = (8, 102, 23.7, 110)` — hộp này chứa **trọn** Phnom Penh,
Viêng Chăn, Nam Ninh/Sùng Tả (Quảng Tây) và Hải Nam → **20.256/37.362 POI (54,2%) không nằm trong lãnh thổ VN**.
Nặng hơn: cổng QA `poi_coords_in_vn` của [`osm/validate.py`](../../../src/ev_siting/data/osm/validate.py) kiểm "POI
nằm trong `VN_BBOX`" — **kiểm đúng cái hộp sinh ra lỗi** ⇒ PASS suốt từ đầu. Một cổng chỉ có giá trị khi nó
**có thể FAIL**. `demand_h3` là hàm mục tiêu của MCLP nên đây là poisoning, không phải lỗi cosmetic.

**Ba nguồn rò rỉ, ba hình học khác nhau** (đo trên snapshot `2026-07-20`) — lý do không thể dùng một chính sách chung:

| Nguồn                  | Khối lượng ngoài VN         | Hình học rò rỉ                                                                | Nguyên nhân                                                             |
| ----------------------- | ------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| POI (Overpass)          | 20.256 điểm (**54,2%**) | ~99%**sâu** trong nước bạn (chỉ 195 POI trong vòng 10 km quanh biên) | bbox thô, không clip                                                    |
| `road_len` (`.pbf`) | **8.934 km** (1,2%)       | **96% trong 10 km quanh biên**                                             | Geofabrik cắt bằng polygon**có đệm**, không cắt đúng biên |
| `pop` (WorldPop)      | 6.472 người (0,0065%)         | 100% trong ~2 km quanh biên                                                      | hiệu ứng mép raster                                                    |

> ⚠️ **Sửa nhận định cũ.** [overview.md §7](../../data-layer/overview.md) từng ghi "`road` lấy từ Geofabrik (**đã clip
> theo quốc gia**)" → **sai**. E-DQ7a vì thế xử lý **cả road**, không chỉ POI.

**Hai quyết định thiết kế (đều đo được, không suy đoán):**

1. **Clip POI ở mức ĐIỂM, phân loại lưới ở mức Ô.** Clip POI theo ô sẽ vừa **giữ** POI nước ngoài (ô có tâm rơi
   vào VN) vừa **xoá** POI VN (ô có tâm rơi ra ngoài). Chỉ điểm mới có lãnh thổ xác định.
2. **Test ô = LỤC GIÁC ∩ POLYGON, không phải TÂM Ô ∈ POLYGON.** Ô res 8 có bán kính nội tiếp 0,49 km nên ô vắt
   biên rơi tâm về bên nào cũng được. Đo thật: test theo **tâm ô** xoá mất **74.642 dân VN thật**; test theo
   **giao lục giác** chỉ xoá **6.472** (0,0065%) — cùng một ranh giới, lệch **11 lần**. Ô vắt biên (`BORDER`)
   **giữ** kèm `frac_in_vn` (tỉ lệ diện tích thuộc VN) để `demand_weight` tự quyết chính sách chia tỉ lệ —
   1.391 ô biên có `frac_in_vn < 0,5` và chứa **69.527 dân**, quá lớn để xử lý ngầm bằng một cờ nhị phân.

**Cách xử lý — polygon trích từ chính `.pbf` đã freeze**, ở [`osm/vn_boundary.py`](../../../src/ev_siting/data/osm/vn_boundary.py):

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
[`build_buildable_h3`](../../../src/ev_siting/data/landuse/build_buildable_h3.py) chuẩn hoá theo `dmax = max(dist_substation_m)` **trên toàn lưới**; lưới cũ chứa ô sâu trong Campuchia/Lào (rất xa mọi trạm biến áp VN)
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

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
