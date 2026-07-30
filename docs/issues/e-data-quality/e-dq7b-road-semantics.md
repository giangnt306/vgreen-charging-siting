# E-DQ7b — `road_len` sai ngữ nghĩa (bước 5)

`🟠 FIX · ☑ chốt 2026-07-28 · Owner: Giang`

**Chẩn đoán — ba triệu chứng, một lỗi thiết kế.** Register tách 3 triệu chứng (`track`+`service` tính là đường
sinh cầu · double-count 2 chiều · `_MAJOR` gộp 3 cấp), nhưng gốc chung là: **`road_len_m` phải phục vụ hai định
nghĩa mâu thuẫn cùng lúc**.

- [`build_buildable_h3.py`](../../../src/ev_siting/data/landuse/build_buildable_h3.py) dùng `road_len_m <= 0` làm bộ
  lọc **cứng** `NO_ROAD_ACCESS` → cần định nghĩa **rộng**: đường đất vẫn là lối vào.
- Proxy cầu cần định nghĩa **hẹp**: đường mòn không sinh nhu cầu sạc.

Vì vậy "bỏ `track`+`service`" chỉ đúng một nửa, và nửa sai thì đắt. Đo trên lưới hiện tại: bỏ chúng khỏi **một
cột duy nhất** đẩy số ô `road=0` từ **6.350 → 34.178** (+27.828); trong đó **2.474 ô chứa 850.207 dân** và **36 ô
chứa 145 trạm sạc đang vận hành** — tức bộ lọc khả thi sẽ loại đúng những chỗ đã **chứng minh** là xây được.

**Thành phần `road_len_m` đo trên `.pbf` đã freeze** (tổng 730.718,5 km — khớp bit-level bảng cũ):

| Lớp                                |      km |     % |      `oneway` | `lanes` có tag |     Ô | `pop` trung vị/ô |
| ----------------------------------- | ------: | ----: | --------------: | ----------------: | -----: | -------------------: |
| LOCAL (residential/unclassified/…) | 449.236 | 61,5% |            0,7% |              0,6% |     — |                   — |
| **TRACK**                     |  74.487 | 10,2% |            0,0% |             0,03% |     — |                   — |
| **SERVICE**                   |  70.667 |  9,7% |            1,2% |              0,3% |     — |                   — |
| TERTIARY                            |  57.252 |  7,8% |            6,2% |              5,6% |     — |                   — |
| SECONDARY                           |  30.842 |  4,2% |           16,4% |             17,4% | 33.339 |                  216 |
| TRUNK                               |  23.511 |  3,2% |           31,2% |             50,4% | 22.554 |                  312 |
| PRIMARY                             |  17.660 |  2,4% |           31,7% |             40,6% | 17.673 |                  374 |
| MOTORWAY                            |   7.004 |  1,0% | **96,9%** |             97,4% |  4.165 |         **73** |

**Bốn quyết định thiết kế (đều đo được):**

1. **R1 — tách TRÍCH XUẤT khỏi CHÍNH SÁCH.** `_EXCLUDE`/`_MAJOR` nằm ngay trong vòng lặp stream: đổi định nghĩa
   "đường" = stream lại 325 MB (~7 phút) và **không hoàn tác được** vì bảng ra chỉ còn 2 số. Nay
   [`roads_pbf.py`](../../../src/ev_siting/data/osm/roads_pbf.py) ghi **km + lane-mét + lane-mét-có-tag của TỪNG LỚP**
   cho mỗi ô; mọi cột vô hướng do `road_semantics.derive()` suy ra ⇒ đổi chính sách = tính lại **vài giây**.
2. **R2 — hai cột, hai nhiệm vụ.** `road_access_m` (mọi đường lái xe được, **gồm** `service`+`track`) cho **lối
   vào**; `road_len_m` (**trừ** chúng) cho **cầu**. `road_access_m` **bằng đúng** `road_len_m` cũ ⇒ chuyển
   `buildable_h3` sang cột mới là đổi 1 dòng, **không lệch hành vi** (xác nhận: 59.768 buildable · 6.350
   `NO_ROAD_ACCESS`, y hệt trước). 27.828 ô chỉ-có-`service`/`track` thành **cờ phạt mềm**
   `ROAD_ACCESS_INFORMAL`, không phải xoá ngầm.
3. **R3 — sửa double-count bằng lane-mét, KHÔNG nhân 0,5.** Đường đôi có dải phân cách vẽ thành 2 way một chiều
   ⇒ 1 hành lang tính 2 lần, còn đường 4 làn không phân cách chỉ tính 1 lần: `road_len` **không** tỉ lệ với năng
   lực thông hành. Nhân 0,5 cho mọi way `oneway` là **sai** — 3.028 km `oneway` thuộc LOCAL là cặp phố một chiều
   thật (và cách này cắt `_MAJOR` tới **20,5%**: 48.176 → 38.312 km). Lane-mét xử lý tận gốc và là số **đo
   được** đúng ở nơi cần: `lanes` có tag ở **97,4% motorway · 50,4% trunk · 40,6% primary** nhưng chỉ **0,6%
   residential** ⇒ chỉ dùng lane-mét cho trục lớn, giữ km tim đường cho lớp địa phương.
4. **R4 — tách `_MAJOR`, khai tử `road_len_mt_m`.** Trên ô có `_MAJOR>0`: ρ_Spearman(`road_len_mt_m`, motorway)
   = **0,31** còn với trunk+primary = **0,70** — cột cũ thực chất là "trục đô thị", tín hiệu cao tốc bị chìm
   (motorway chỉ 14,8% km `_MAJOR`). Hai lớp gần như không chồng lấn (3.311 ô chỉ-motorway vs 37.574 ô
   chỉ-trunk/primary) và ngữ nghĩa ngược nhau: ô motorway `pop` trung vị **73** (liên tỉnh, dừng lâu, DC công
   suất cao) vs trunk/primary **312–374** (trục đô thị). **Đổi tên thay vì đổi nghĩa ngầm** để consumer cũ gãy
   to — cùng nguyên tắc với cổng `poi_has_in_vn_flag` của E-DQ7a.

**Schema sau E-DQ7b** (`osm_roads_h3.parquet` giữ 28 cột lớp; `demand_h3` giữ 5 cột suy ra):

| Cột                   | Định nghĩa                                             | Consumer                                     |
| ---------------------- | --------------------------------------------------------- | -------------------------------------------- |
| `road_access_m`      | mọi đường lái xe được (gồm`service`+`track`) | `access_tier` (E-DQ8a) → `buildable_h3` |
| `road_len_m`         | mạng lái xe**trừ** `service`+`track`         | proxy cầu                                   |
| `road_lane_mw_m`     | lane-mét cao tốc                                        | hành lang liên tỉnh                       |
| `road_lane_ar_m`     | lane-mét`trunk`+`primary`                            | trục đô thị                              |
| `road_bridge_m`      | km cầu/hầm (**tập con** của `road_access_m`)  | P5 — không đặt trụ trên mặt cầu      |
| ~~`road_len_mt_m`~~ | **khai tử**                                        | —                                           |

**Kết quả** (chạy 28/07 — `roads_pbf && make osm && make demand && landuse-national && candidates`):

| Đại lượng          | Trước          | Sau                        | Ghi chú                                                            |
| ---------------------- | ---------------- | -------------------------- | ------------------------------------------------------------------- |
| `road_access_m`      | —               | **721.785 km**       | =`road_len_m` cũ **chính xác** ⇒ lối vào không đổi |
| `road_len_m`         | 721.785 km       | **578.473 km**       | −143.311 km (`service`+`track`)                                |
| `road_len_mt_m`      | 46.824 km        | **khai tử**         | →`road_lane_mw_m` 13.849 km + `road_lane_ar_m` 82.484 km       |
| `road_bridge_m`      | —               | **4.345 km**         | mới; 50 ô có đường duy nhất là mặt cầu                    |
| Ô`NO_ROAD_ACCESS`   | 6.350            | **6.350**            | không đổi (đúng thiết kế R2)                                 |
| `buildable` national | 59.768           | **59.768**           | không đổi                                                        |
| Candidate Hà Nội     | 1.711 (5/5 gate) | **1.711 (5/5 gate)** | T0 1.409 · T4 130 · T1 112 · T2 60                               |

**QA gate — 6 cổng mới ở [`osm/validate.py`](../../../src/ev_siting/data/osm/validate.py) + 2 ở `build_demand_h3.py`.**
Cổng cũ `road_mt_le_total` bị gỡ vì **vô dụng**: `_MAJOR ⊂` mọi đường là đúng theo *xây dựng* nên nó không bao
giờ FAIL được — cùng lỗi thiết kế với `poi_coords_in_vn` của E-DQ7a. Thay bằng cổng **có thể FAIL**:
① `roads_h3_has_tier_columns` (chặn artefact cũ) · ② **`road_tiers_sum_eq_access`** — đối soát Σ lớp, bắt lệch
nhãn cột · ③ `road_len_le_access` + `road_bridge_le_access` · ④ `road_lane_invariants` (`lane_m ≥ m` vì mọi way
≥1 làn; `lane_obs_m ≤ lane_m`) · ⑤ **`major_lane_observed_share ≥ 0,40`** — nếu lane-mét trục lớn chủ yếu là số
**suy đoán** thì feature hết là số đo (thực đo: **59,4%**) · ⑥ **`supply_cells_have_road_access`** — cổng
**ngoại vi** duy nhất của tầng đường: ô chứa trạm sạc đang vận hành phải có đường (WARN >1%, FAIL >2%).

> ⚠️ **Cổng ② và ④ đã bắt lỗi thật ngay trong lúc dựng.** Bản đầu ghi accumulator theo thứ tự xen kẽ nhưng đặt
> tên cột theo thứ tự gộp ⇒ **lệch nhãn toàn bộ bảng lớp**: số vẫn không âm và vẫn cộng ra tổng "đẹp", nhưng
> `road_access_m` ra **205.936 km** thay vì 730.718 km và `lanes có tag` ra **229%**. Nay chỉ số slot tra thẳng
> từ `TIER_COLUMNS.index(...)` nên hai bên không thể lệch, kèm test khoá layout
> ([`tests/test_road_semantics.py`](../../../tests/test_road_semantics.py)).

**Phát hiện phụ (không có trong register):**

- **`service` không tách được theo subtype ở VN:** **86%** (61.032/70.667 km) **không** có tag `service=*`;
  `parking_aisle` chỉ **214 km**. ⇒ phương án "giữ lối đi bãi đỗ, bỏ lối vào nhà" **không khả thi** — phải xử lý
  `service` như một khối. Ghi lại để không ai đề xuất lại.
- **`track` 74,6% `unpaved` rõ ràng** (55.576 km) — vừa xác nhận loại khỏi cầu, vừa xác nhận **vẫn là** lối vào.
- **4.178 km cầu + 203 km hầm.** Ô mà đường duy nhất là mặt cầu vẫn đang lọt bộ lọc lối vào → thêm
  `road_bridge_m` + cờ mềm `ROAD_BRIDGE_ONLY` (**50 ô**).
- **`highway=services`/`rest_area`: 91 đối tượng, 49 km.** Trạm dừng nghỉ cao tốc là vị trí sạc hạng nhất nhưng
  đang bị đếm như đường thường → **ứng viên T3** cho P5 (hiện `build_candidates.py` ghi "để roadmap").
- **108 trạm đang vận hành nằm ở ô OSM không có bất kỳ đường nào** (100 ô, 0,78% ô có trạm) — hoặc OSM thiếu
  đường, hoặc toạ độ còn sai sau E-DQ1. Đây chính là cổng ⑥ ở trên, và là đầu vào cho **E-DQ7d**.

**Hệ quả thứ tự — ràng buộc "7b trước 8" đã tan.** [§ thứ tự](../../known-issues.md#3-thứ-tự-xử-lý--ràng-buộc-phụ-thuộc) lập luận E-DQ8 phải đo sau 7b vì bỏ
`track`+`service` làm **tăng** số ô `road=0`. Điều đó chỉ đúng với phương án **một cột**. Với R2, E-DQ8 đo trên
`road_access_m` (một xóm chỉ có đường mòn **vẫn có** đường) nên con số **đứng yên: 6.350 ô / 1.268.026 dân** —
đúng bằng giá trị sau E-DQ7a. Nói cách khác, lý do "phải làm 7b trước" chính là bằng chứng phương án một cột
sai. E-DQ8 nay **đo được ngay**, và có thêm hai tập con để phân loại: 27.828 ô lối vào phi chính thức (850.207
dân) và 100 ô có trạm thật nhưng không có đường.

> ✅ **Chốt 30/07.** Hai tập con ấy đã thành hai dòng register riêng: `road_access_m` được **giữ nguyên** làm nguồn, nhưng câu hỏi "có lối vào không?" nay đo ở thang **lân cận** (`access_tier`, [E-DQ8a](e-dq8a-access-tier.md)) và khối lượng dân ở ô không lối vào đã được **dời** ([E-DQ8b](e-dq8b-roadless-reallocation.md)). 27.828 ô `ROAD_ACCESS_INFORMAL` vẫn đúng như R2 định — và cờ đó **nay mới thật sự có trọng số** trong `penalty` (trước 30/07 nó được phát ra nhưng công thức bỏ qua).

**Limitation (`DOC`):**

- **Lane-mét ở lớp địa phương là số suy đoán** (mặc định 1 làn nếu một chiều, 2 nếu hai chiều) vì `lanes` chỉ
  có ở 0,6% `residential` → **không** dùng `lane_m_LOCAL` làm feature; cổng ⑤ chỉ canh lớp trục lớn.
- **`oneway` không đồng nghĩa đường đôi.** Lane-mét né được vấn đề này (đếm làn, không đếm hành lang) nhưng nếu
  sau này cần **số hành lang**, phải ghép cặp way song song bằng hình học — chưa làm.
- **`motorway` của OSM ở VN rộng hơn "cao tốc" chính thức**: 7.004 km tim đường (3.612 km nếu nhân đôi-halve) so
  với ~2.000+ km cao tốc đang khai thác, vì OSM gắn `motorway` cho cả đường trên cao đô thị/vành đai. Vì vậy
  **không** đặt cổng cứng theo số liệu chính thức — muốn dùng phải chốt nguồn chính thức và freeze vào
  `data/external/` trước.
- **Trọng số gap-fill T4 vẫn đặt tay** (`0,025·road_lane_ar_m + 0,05·road_lane_mw_m`, cao tốc nặng gấp đôi vì ô
  cao tốc `pop` trung vị chỉ 73 nên vô hình trong hạng `pop`) — **E-DQ7d/P1** sẽ hiệu chuẩn bằng 18,6M bản ghi
  occupancy.

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
