# E-DQ3 — Cột admin trống + trọng tài toạ độ (bước 14)

`🟡 FIX · ☑ chốt 2026-07-30 · Owner: Giang`

> ℹ️ **Ghi chú nguồn (30/07).** Mục này được **dựng lại** từ artefact thật
> (`data/interim/admin/station_admin_report.json` · `grid_admin_report.json`), code
> [`src/ev_siting/data/admin/`](../../../src/ev_siting/data/admin/) và commit `afe27a3`: bản viết gốc **không bao giờ
> vào file** — commit đó dán nhầm một transcript vào giữa `known-issues.md` thay cho §3 của E-DQ3. Mọi số dưới đây
> đọc trực tiếp từ report JSON, không chép lại từ doc khác.

**Chẩn đoán:** 4 cột hành chính (`admin_l1_code`, `province_name`, `commune_name`, `commune_kind`) có trong hợp đồng
schema nhưng **null 100%** ⇒ không cắt được theo tỉnh/xã, không có mẫu số cho `coverage_pop` (**P10**), và **758**
`COORD_ADDR_MISMATCH` mà [E-DQ1](e-dq1-coord-placeholder.md) cố ý hoãn thì **không có trọng tài** — địa chỉ nói một
tỉnh, `province_code` nói tỉnh khác, và không có gì phân xử ai đúng.

Ba quyết định nguồn phải chốt trước khi enrich được:

1. **Niên đại nào.** VN sáp nhập đơn vị hành chính **2025** → **34 tỉnh**, còn `province_code` của evcs là prefix
   theo hệ **63 tỉnh CŨ**. Hai hệ **không** ánh xạ 1:1 và **không** được ghi đè lẫn nhau.
2. **Nguồn ranh giới nào.** `admin_level=4` của OSM (40 polygon, đã có sẵn từ [E-DQ7a](e-dq7a-poi-outside-vn.md))
   **trộn hai niên đại** sáp nhập 2025 ⇒ không dùng được. Chốt **ranh giới xã VNSDI** (34DVHC layer 2, niên đại
   **2025-06-16**) — xem memory [[vnsdi-commune-source]].
3. **Ô lưới thuộc xã nào.** Một lục giác 0,83 km² thường vắt qua nhiều xã: **61.648/255.480 ô** chạm ≥ 2 xã và
   chúng giữ **38,8M** `pop_adj` (**40,0%**) ⇒ `groupby(commune_name)` trên nhãn ô là **sai**; phải phân bổ theo
   **trọng số diện tích**.

**Cách xử lý — hai đường độc lập, cùng một lớp ranh giới.**

- **Trạm** ([`enrich_stations.py`](../../../src/ev_siting/data/admin/enrich_stations.py)): point-in-polygon trên ranh
  giới xã; điểm rơi ngoài mọi xã nhưng trong dung sai **500 m** thì **snap** vào xã gần nhất
  (`admin_src = nearest`), quá dung sai thì **không đoán** (`unresolved`). Bất biến cứng:
  **có nhãn ⟺ `coord_resolved`**. Thêm `commune_code` (khoá join) + provenance `admin_src`/`admin_dist_m`/
  `admin_verdict`. `province_code` (hệ 63 CŨ) **giữ nguyên cạnh** `admin_l1_code` (hệ 34), crosswalk ở
  `data/interim/admin/province_crosswalk.csv` (2 mã `NA`/`AC` **không phải tỉnh** — đã có cổng riêng).
- **Lưới** ([`enrich_grid.py`](../../../src/ev_siting/data/admin/enrich_grid.py)): giao **hình lục giác** với polygon
  xã (không test theo tâm ô — tâm ô bỏ sót **2.926** ô), sinh bảng phân bổ `cell_commune` (Σw = 1 mỗi ô) rồi rollup
  `demand_commune`. **Nhãn ô = argmax trọng số**, và nhãn đó **không phải** đơn vị phân bổ — hai việc khác nhau,
  xem memory [[edq3-admin-layer]].
- **Trọng tài toạ độ:** nhãn xã phân xử `COORD_ADDR_MISMATCH` của E-DQ1 bằng cách so tỉnh-từ-toạ-độ với
  tỉnh-từ-địa-chỉ; kết luận ghi vào `admin_verdict`, **không** sửa toạ độ (trừ 11 ca snap ≤ 500 m).

**Kết quả** (`station_admin_report.json`, `grid_admin_report.json` — **mọi cổng PASS**):

| Đại lượng                                        | Giá trị                                                                              |
| -------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Trạm có nhãn                                    | **19.453/19.507** — `inside` 19.442 · `nearest` 11 · `unresolved` 54            |
| Độ phủ hành chính                              | **34 tỉnh · 2.691 xã** (niên đại 2025-06-16)                                    |
| `admin_verdict`                                  | NOT_FLAGGED 18.707 · **COORD_CONFIRMED 549** · UNRESOLVED 197 · NO_COORD 38 · **COORD_BAD 16** |
| Phân xử `COORD_ADDR_MISMATCH`                  | **561/758** (549 toạ độ ĐÚNG — lỗi ở `province_code`; 12 toạ độ SAI); 197 còn advisory |
| Cờ mới                                           | `COORD_OUTSIDE_ADMIN` **16** (loại khỏi cung) · `ADMIN_COORD_SNAPPED` 11 · `ADMIN_PROVINCE_CONFLICT` 792 |
| **Cung công khai khả dụng**                  | 19.015 → **18.999** · `supply_cells` 12.811 → **12.801**                        |
| Lưới có nhãn                                   | **255.298/255.480** ô (182 ô ngoài mọi xã giữ **2.907** người → [E-DQ8c](e-dq8c-servable-denominator.md)) |
| Bảng phân bổ                                    | `cell_commune` **322.870** cặp ô↔xã · 61.648 ô đa xã                             |
| Rollup                                            | `demand_commune` **3.321 xã / 34 tỉnh** (+ `danso` VNSDI làm ĐỐI CHỨNG + `n_supply`) |

**QA gate — 7 (trạm) + 7 (lưới), tất cả PASS.**

| Cổng (trạm)                       | Ý nghĩa                                                            |
| ----------------------------------- | -------------------------------------------------------------------- |
| `admin_join_rate ≥ 0,995`         | tỉ lệ gán nhãn trên tập `coord_resolved` — hiện **1,000**    |
| `admin_iff_coord_resolved`        | **bất biến**: có nhãn ⟺ toạ độ dùng được (không nhãn ngầm) |
| `admin_vintage_single`            | chỉ một niên đại — đúng **34** tỉnh, không lẫn hệ 63          |
| `outside_admin_excluded`          | 16 `COORD_OUTSIDE_ADMIN` **thật sự** rơi khỏi tập cung             |
| `crosswalk_total`                 | mọi `province_code` có ảnh trong crosswalk                        |
| `ambiguous_codes_are_nonprovince` | 2 mã nhập nhằng (`NA`/`AC`) chứng minh được là **không phải tỉnh** |
| `supply_fully_labelled`           | 100% trạm trong tập cung có nhãn hành chính                     |

| Cổng (lưới)                | Ý nghĩa                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `grid_admin_conservation`  | Σ mọi cột khối lượng **bất biến** qua phân bổ (lệch 0,0)             |
| `grid_admin_join_rate`     | 182 ô không xã giữ **0,0030%** dân → chuyển **E-DQ8c**, không xoá     |
| **`hex_beats_centroid`** | giao lục giác **255.298** vs test theo tâm ô 252.372 (**+2.926 ô**)    |
| `weights_sum_to_one`       | Σw = 1 mỗi ô (lệch tối đa 2,22e-16)                                     |
| `label_is_argmax`          | 0 ô có nhãn không phải argmax (chặn "first-hit")                        |
| `communes_covered`         | 0 xã không có ô nào                                                     |
| `admin_vintage_single`     | 34 tỉnh                                                                   |

Lệnh: `make admin-stations` · `make admin-grid`. Test: [`tests/test_admin.py`](../../../tests/test_admin.py) — **14
test**, gồm 2 test tính chất trên lớp ranh giới thật (`disjoint_cover`, `provinces_are_dissolve_of_communes`) và 1
test chứng minh **lục giác > tâm ô**.

**Hệ quả sang issue khác:**

- **[E-DQ7d](e-dq7d-demand-proxy-validation.md) đổi MẪU SỐ.** Harness của Kỳ đặc tả trên "12.811 ô cung", nay là
  **12.801**. Xê dịch 0,08% ⇒ **không** lật verdict 0,33/0,865, nhưng hai lần chạy trên hai mẫu số khác nhau
  **không so được với nhau**.
- **[E-DQ7a](e-dq7a-poi-outside-vn.md) chỉ "mở khoá" được một nửa.** `in_vn` thăng cấp **4/758** mismatch như dự
  đoán, nhưng 40 polygon adm4 thì không dùng được (trộn niên đại), và ranh giới xã lại làm `in_vn` **thừa** ở vai
  detector: xã bắt **16** toạ độ sai so với **4** của adm2 — vì polygon quốc gia **bao gồm lãnh hải**. Bài học:
  "một artefact, ba issue" đúng về **thứ tự làm**, nhưng không bảo đảm artefact đó là **nguồn tốt nhất** cho issue
  thứ ba.
- **Hai CSV ảnh chụp đã lỗi thời → nay đã có producer.** `clean_supply.csv` (19.015 dòng) chênh canonical **đúng
  16 dòng** = 16 trạm `COORD_OUTSIDE_ADMIN`; `excluded.csv` 492 → đúng phải là 508. Gốc rễ: **không module nào
  trong `src/` sinh ra chúng** (`grep clean_supply src/` → 0 hit) nên chúng không chạy lại theo pipeline. Đã sửa
  30/07 — [`evcs/export_supply.py`](../../../src/ev_siting/data/evcs/export_supply.py) (`make export-supply`) sinh
  lại cả hai từ `canonical/stations`, 6 cổng QA, cổng ① là **đối soát `input = cung + loại`**; 16 dòng kia nay có
  lý do tường minh `COORD_OUTSIDE_ADMIN` thay vì biến mất im lặng. Nguồn chân lý **vẫn là** `canonical/stations`.
  Xem [dataset-inventory.md §3.5](../../data-layer/dataset-inventory.md).

**Limitation (`DOC`):**

- **Không có `danso` là nguồn dân số.** `demand_commune.danso` (VNSDI 2025) chỉ là **ĐỐI CHỨNG** — phát biểu tuyệt
  đối vẫn neo `pop` (WorldPop UNadj, [E-DQ7e](e-dq7e-pop-calibration.md)).
- **Hai hệ tỉnh cùng tồn tại vĩnh viễn** trong `stations`: `province_code` (63 CŨ, khoá partition Hive + prefix mã
  evcs) và `admin_l1_code` (34, hệ hiện hành). Bất kỳ báo cáo theo tỉnh **phải nói rõ dùng hệ nào**.
- **11 ca `nearest`** là suy đoán trong 500 m (không phải quan sát); **197** `COORD_ADDR_MISMATCH` còn advisory vì
  địa chỉ tự do chưa parse được → chỉ đóng hết sau [E-DQ6](e-dq6-freetext-cleanup.md).

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
