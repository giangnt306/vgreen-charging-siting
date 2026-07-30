# E-DQ8a — Lối vào đo ở thang SAI (bước 10)

`🟡 FIX · ☑ Xử lý 2026-07-30 · Owner: Giang`

**Chẩn đoán.** `buildable_h3` và E-DQ8 hỏi *"ô này có đường không?"* bằng cách xét **đúng ô đó**
(`road_access_m <= 0`). Ô res 8 rộng 0,75 km² và tâm hai ô kề cách **0,98 km**: một xóm mà đường vào nằm ở
**ô bên cạnh** bị kết luận "không có đường". Tách 6.350 ô của E-DQ8 theo vành:

| Bậc         | Điều kiện                               |              Ô | `pop` | % khối lượng |
| ------------ | ------------------------------------------ | --------------: | ------: | --------------: |
| `ADJACENT` | có đường ở**vành 1** (~1,0 km) | **4.862** | 894.956 | **72,1%** |
| `NEAR`     | chỉ có ở vành 2 (~2,0 km)              |             923 | 159.831 |           12,9% |
| `ISOLATED` | không có đường trong cả hai vành    |             565 | 187.047 |           15,1% |

⇒ **72,1% khối lượng E-DQ8 không phải lỗi dữ liệu, mà lỗi THANG ĐO.** Đây đúng là cái bẫy mà **E-DQ7a đã gỡ ở
tầng biên giới** ("test là **giao lục giác** ∩ polygon, KHÔNG phải tâm-ô-trong-polygon" — vì ô vắt biên rơi tâm
về bên nào cũng được); tầng đường chưa từng được xử lý cùng cách. Cùng họ với `poi_coords_in_vn` (7a) và
`POP_DENSITY_OUTLIER` (7f): **một đại lượng không chứa thông tin về câu hỏi được hỏi**.

**Neo ngoại vi — 19.015 trạm đang vận hành.** Bậc mới phải được kiểm bằng thực địa, không tự tuyên bố:

| Bậc của ô chứa trạm          |        Trạm |           % trạm |                                                     % dân số ở bậc đó |
| --------------------------------- | -----------: | ----------------: | --------------------------------------------------------------------------: |
| `DIRECT`                        |       18.907 | **99,432%** |                                                                     98,727% |
| `ADJACENT`                      | **15** |            0,079% |                                                            **0,917%** |
| `NEAR`                          |            5 |            0,026% |                                                                      0,164% |
| `ISOLATED`                      |            1 |            0,005% |                                                                      0,192% |
| *không có dòng trong lưới* | **87** |            0,458% | — (xem[E-DQ8c](e-dq8c-servable-denominator.md)) |

Đọc đúng bằng chứng này quan trọng hơn cả con số: **15 trạm thật ở ô `ADJACENT` ⇒ ô như thế xây được**, nên loại
cứng chúng là sai. Nhưng `ADJACENT` giữ 0,917% dân mà chỉ nhận 0,079% trạm — **dưới mức dân số ~11×** — nên bằng
chứng **không** đủ để nói `ADJACENT` tương đương `DIRECT`. Vì vậy đáp án là **bậc có thứ tự + phạt mềm**, không
phải nới bộ lọc thành nhị phân.

**Cách xử lý (ĐÃ CÀI ĐẶT) — [`osm/access_tiers.py`](../../../src/ev_siting/data/osm/access_tiers.py).**

1. **A1 — hai cột vành + một cột bậc.** `road_access_nb1_m`, `road_access_nb2_m` (Σ `road_access_m` của vành 1/2,
   **trừ** chính ô) → `access_tier` ∈ `DIRECT|ADJACENT|NEAR|ISOLATED`. Vào `demand_h3`.
2. **A2 — tính TRƯỚC khi clip lãnh thổ.** Ô bên kia biên vẫn là láng giềng **có đường thật** (8.934 km đường rò
   của Geofabrik, E-DQ7a); clip trước khi tính vành sẽ báo `ISOLATED` giả cho đúng những ô biên.
3. **A3 — loại cứng CHỈ `ISOLATED`** (`buildable_h3`: **6.350 → 723 ô**). `ADJACENT`/`NEAR` nhận phạt mềm
   `NEEDS_ACCESS_ROAD` (**7.072 ô**) — phải **làm** đường vào là chi phí thật, không phải lý do loại bỏ.
4. **A4 — bậc phải được TÍNH, không mặc định.** Ô AOI không có dòng trong `demand_h3` (AOI thành phố sinh đĩa
   hình học; ô `OUTSIDE` đã tách sang `demand_h3_clipped_out`) trước đây rơi về `road_access_m = 0` ⇒ loại cứng.
   Nay tra bậc từ `osm_demand_components_h3` qua `tiers_from_lookup()`. Lý do là **đo được**: 76 ô không-dòng
   chứa **83 trạm đang vận hành**, và tính từ bảng đường ra **50 `ADJACENT` · 8 `NEAR` · 18 `ISOLATED`** — mặc
   định `ISOLATED` loại cứng đúng những ô đã có bằng chứng thực địa là xây được. `classify()` là **nơi duy nhất**
   định nghĩa bậc để hai đường tính không thể lệch (bài học cổng ② của E-DQ7b).

**Phát hiện phụ — bộ lọc cũ gần như vô ích.** `NO_ROAD_ACCESS` loại 6.350 ô, nhưng chỉ **134 ô** bị loại **RIÊNG**
bởi nó; phần còn lại đã vướng `NOT_BUILT_UP`/`WATER`/`WETLAND`:

```
('NOT_BUILT_UP','NO_ROAD_ACCESS')                      4.408
('NOT_BUILT_UP','NO_ROAD_ACCESS','WATER','WETLAND')      749
('NOT_BUILT_UP','NO_ROAD_ACCESS','WATER')                520
('NOT_BUILT_UP','NO_ROAD_ACCESS','WETLAND')              481
('NO_ROAD_ACCESS',) một mình                             134
```

⇒ Hệ quả **cung** của E-DQ8 gần bằng 0; hệ quả thật nằm ở **mẫu số cầu**, và đó là 8b/8c.

**Phát hiện phụ — bốn cờ mềm có trọng số 0.** `POP_NO_ROAD`, `ROAD_ACCESS_INFORMAL` (27.828 ô),
`ROAD_BRIDGE_ONLY` (50 ô), `NO_SUBSTATION` được **phát** vào `penalty_flags` nhưng công thức `penalty` chỉ gồm
`crop`/`low_built`/`dist` ⇒ chúng **không hề** ảnh hưởng điểm. Nay vào công thức
(`+0,2·needs_access +0,1·informal +0,1·bridge_only`). `access_tier` cũng được **xuất ra** `buildable_h3`: không
audit được một quyết định loại bỏ bằng cột không có trong artefact.

**Cổng QA — 1 cổng mới ở `build_demand_h3` (FAIL được):** `access_tier_consistent` — mọi ô `road_access_m > 0`
phải là `DIRECT`, và mọi ô `ISOLATED` phải thật sự trống đường ở **cả hai** vành (đo: **0 · 0**). Kèm
[`tests/test_access_tiers.py`](../../../tests/test_access_tiers.py) — 11 test khoá ngữ nghĩa, trong đó ca `ADJACENT`
(ô mà bản cũ đánh sai) và ca ô mồ côi ở A4.

**Kết quả** (`make demand` → `landuse-national` → `candidates`):

| Đại lượng                        | Trước    | Sau                                           |
| ------------------------------------ | ---------- | --------------------------------------------- |
| ô loại cứng vì "không đường" | 6.350      | **723** (`ISOLATED`)                  |
| `buildable` national               | 59.768     | **59.927**                              |
| cờ`NEEDS_ACCESS_ROAD`             | —         | **7.072 ô**                            |
| `candidate_sites` (Hà Nội MVP)   | 1.707      | **1.707** (không đổi)                |
| `demand_h3`                        | 254.159 ô | **255.480 ô** (thêm ô nhận của 8b) |

**Limitation (`DOC`):**

- **`ADJACENT` ≠ `DIRECT`, và phạt 0,2 là số ĐẶT TAY.** Bằng chứng 15 trạm chỉ chứng minh *tới được*; độ lớn chi
  phí làm đường vào chưa có nguồn. Nếu muốn số đo, phải có capex đường theo lớp — chưa freeze nguồn nào.
- **Vành ≠ khoảng cách.** `grid_disk(1)` là ~0,98 km theo tâm ô, không phải khoảng cách tới **mép** đường. Muốn
  chính xác phải tính `dist_to_road_m` từ hình học way — chưa làm; vành là bản rẻ và đủ để phân bậc.
- **Lưới vẫn KHÔNG phải tessellation.** A4 chữa *mặc định sai*, không chữa *ô thiếu*: 76 ô / 83 trạm vẫn không có
  dòng ở bất kỳ bảng lưới nào. Xem [E-DQ8c](e-dq8c-servable-denominator.md).

---

← [Register vấn đề](../../known-issues.md) · [Mục lục issue](../README.md)
