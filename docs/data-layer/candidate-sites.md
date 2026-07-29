# CANDIDATE SITES & LAND-USE FILTER (P5)

> Cập nhật: **2026-07-28** · Nhánh `data/giang` · Xử lý **[P5](../known-issues.md)** (candidate set + lọc land-use).
>
> Điểm chạm interop thứ 3 giữa **Giang → Kỳ** (ngoài demand proxy & GeoJSON kết quả).

---

## 0. TL;DR

- **Vấn đề P5** gộp 3 câu hỏi độc lập: **(a)** candidate sinh từ đâu · **(b)** điểm nào phải loại (land-use) · **(c)** candidate là điểm hay ô H3.
- **Output:** `data/processed/candidate_sites.{parquet,geojson}` — bàn giao trực tiếp cho MCLP.
- **Bộ lọc khả thi:** `data/interim/landuse/buildable_h3.parquet` (ESA WorldCover 10m + OSM cấm + road access).
- **MVP Hà Nội:** 1.672 candidate, 79% ô AOI buildable, **5/5 QA gate PASS**.
- Chạy: `make landuse CITY=hanoi && make candidates CITY=hanoi`.

---

## 1. Ba câu hỏi của P5

| | Câu hỏi | Bản chất | Quyết định |
| --- | --- | --- | --- |
| **(a)** | Candidate **sinh ra từ đâu**? | bộ lọc **dương** (nơi *có thể* đặt) | phân tầng anchor T0–T4 (§3) |
| **(b)** | Điểm nào phải **loại bỏ**? | bộ lọc **âm** (hồ/núi/đất cấm/không đường) | `buildable_h3` 2 mức (§4) |
| **(c)** | Candidate là **điểm** hay **ô H3**? | granularity — dính trực tiếp **P4** | mô hình lai: điểm thực, ≤1/ô (§2) |

---

## 2. (c) Granularity — mô hình lai *(quyết định nền)*

Với `R = 3 km` và `d = 0,98 km` (tâm–tâm 2 ô H3 res 8) → tỷ lệ **R/d = 3,07**.
Hệ quả: **hai điểm bất kỳ trong cùng một ô H3 phủ gần như y hệt tập ô demand**.

- Về toán học MCLP: vị trí chính xác trong ô là **vô nghĩa** — chỉ ô có nghĩa.
- Về explainability/deliverability (problem-analysis §5 "tại sao đặt ở đây"): điểm thực lại **rất có nghĩa**.

> **Chốt:** candidate = **một điểm thực** (POI anchor / trạm hiện có), nhưng **tối đa 1 candidate / ô H3 res 8**.
> Coverage của candidate tính theo `h3_r8` của nó.

Vì sao ≤1/ô là bắt buộc: nếu giữ hàng chục điểm gần nhau phủ cùng tập ô → MCLP có nhiều **nghiệm bằng nhau**
→ chọn ngẫu nhiên trong các nghiệm đó. Đây là **biến thể im lặng của P4** (degeneracy), khác với P4 gốc ở chỗ
nó không lộ ra qua tỷ lệ R/d mà qua **cấu trúc candidate**. Gate ④ (§5) bắt đúng lỗi này.

---

## 3. (a) Sinh candidate — phân tầng anchor

| Tier | Nguồn | Lý do | `capex_class` |
| --- | --- | --- | --- |
| **T0** | trạm hiện có (`canonical/stations`) | brownfield: đã có điện, mặt bằng, giấy phép | `low` |
| **T1** | `amenity=parking`, `amenity=fuel` | có sân đỗ, quen mô hình dừng-đỗ | `mid` |
| **T2** | `shop=mall`, `retail`, `building=apartments` | dwell time dài, có bãi đỗ đi kèm | `mid` |
| **T4** | **gap-fill tổng hợp** — centroid ô demand cao **không** có anchor T0–T2 | chống thiên vị đô thị của OSM | `high` |

- **T0 là incumbent bắt buộc mở** (ràng buộc thiết kế MCLP) và `is_existing=True` → Sprint 3 tính CapEx=0 / loại khỏi ngân sách;
  cũng để DoD Sprint 2 so sánh "mạng hiện tại vs. model đề xuất".
- **T4 bắt buộc, không phải nice-to-have.** POI OSM thưa ở vùng ven → nếu chỉ POI-anchored thì MCLP *không thể*
  chọn ở đó → kết quả tự động thiên vị đô thị, mâu thuẫn mục tiêu "phủ công bằng" của Nhà nước
  (problem-analysis §1). T4 gắn cờ `anchor_type=gapfill_synthetic`, chỉ lấy ô trong **top-decile demand**
  (`GAPFILL_TOP_Q = 0.90`), và **không** được trình bày như khuyến nghị chốt trong report cuối.
- **T3** (rest_area / nút giao QL·CT, chung cư mật độ cao) cần road-class trích từ `.pbf` → **để roadmap**.

**Gộp về ≤1/ô:** khi nhiều anchor rơi cùng ô, giữ anchor **tier tốt nhất** (rank T0<T1<T2<T4).

---

## 4. (b) Bộ lọc land-use — `buildable_h3`

**Nền chính: ESA WorldCover 10m v200 (2021), CC-BY 4.0.** Vì OSM land-use ở VN rất thưa —
*"không có polygon nước" ≠ "đất khô"*. OSM chỉ bổ sung ranh giới **pháp lý** mà raster không có
(military / protected_area / aerodrome). Pipeline đã có `rasterio` từ WorldPop → chi phí tích hợp ~0.

### Loại cứng (bỏ khỏi candidate set)

| Loại | Nguồn | Ngưỡng / tag |
| --- | --- | --- |
| Mặt nước | WorldCover | `frac_water ≥ 0,50` (`WATER`) |
| Nước + ngập nước | WorldCover | `frac_water + frac_wetland ≥ 0,70` (`WETLAND`) |
| Đất cấm | OSM | `landuse=military` · `boundary=protected_area` · `leisure=nature_reserve` · `aeroway=aerodrome` · `natural=water`/`reservoir` |
| Ngoài AOI | `aoi.py` | ngoài lõi + buffer 5 km |
| Toạ độ bẩn (T0) | `stations` | cờ `COORD_INVALID` / `COORD_PLACEHOLDER` / `DUP_COORD_SUSPECT` (F4, tập dùng chung `features/paths.py:DIRTY_COORD_FLAGS`) |

> **`built_up_frac`** (tỷ lệ pixel WorldCover class 50) là chỉ số chủ lực: bắt cả nước, núi, rừng,
> và "đã có hạ tầng xây dựng" trong một lần quét.

### Phạt mềm (giữ, hạ điểm — cột `penalty` ∈ [0,1] + `penalty_flags`)

| Loại | Điều kiện | Đóng góp `penalty` |
| --- | --- | --- |
| Đất nông nghiệp | `frac_crop ≥ 0,60` (`CROP`) | +0,3 |
| Hạ tầng mỏng | `built_up_frac < 0,15` (`LOW_BUILTUP`) | +0,2 |
| Chưa xây dựng | `built_up_frac < 0,05` (`NOT_BUILT_UP`) | +0,35 |
| Không thấy đường | `road_len_m ≤ 0` (`NO_ROAD_ACCESS`) | +0,25; `pop>0` cũng gắn `POP_NO_ROAD` |
| Xa trạm biến áp | dist tới `power=substation` | +0,5·min(d/50 km, 1) — mẫu số vật lý cố định |

Trạm hiện có (T0) đã có điện/mặt bằng → `penalty = 0` (không phạt land-use thêm).

---

## 5. QA gate — 5 cổng chặn

Đây là phần khiến P5 **thực sự được đóng**, thay vì chỉ "có file candidate". Ghi ra `candidate_sites_qa.json`.

| # | Gate | Ngưỡng | Vì sao |
| --- | --- | --- | --- |
| ① | **upper_bound_coverage** | union coverage toàn bộ candidate ≥ **90%** demand lõi AOI | fail = chính candidate set chặn model → mọi kết quả MCLP là trần giả |
| ② | **freedom_ratio** | `\|candidates\| ≥ 5×p` | nếu `≈ p` thì MCLP không có gì để chọn |
| ③ | **size_ceiling** | `\|candidates\| ≤ 3.000` | giữ MCLP giải được trong thời gian hợp lý |
| ④ | **anti_degenerate** | `unique(coverage_set)/\|candidates\| ≥ 0,90` | biến thể ẩn của **P4**: nhiều candidate phủ y hệt → nghiệm không xác định |
| ⑤ | **grid_radius** | `R > d = 0,98 km` | nhắc lại gate **P4** cho khép kín |

FAIL bất kỳ gate nào (mặc định) → exit ≠ 0, **không bàn giao Kỳ**. Dùng `--no-strict` để chỉ cảnh báo.

---

## 6. Schema bàn giao — `candidate_sites`

| Cột | Kiểu | Vai trò |
| --- | --- | --- |
| `candidate_id` | string | **PK** (`cand-<city>-<idx>`) |
| `lat`, `lng` | double | toạ độ thật (explainability) |
| `h3_r8` | string | ô coverage (**unique** — ≤1/ô) |
| `tier` | string | T0–T4 |
| `anchor_type` | string | `existing_station`/`parking`/`fuel`/`mall`/`retail`/`apartments`/`gapfill_synthetic` |
| `source_ref` | string | `station_id` \| `osm_type/osm_id` \| `synthetic:<h3>` |
| `is_existing` | bool | T0 → CapEx=0 ở Sprint 3 (incumbent bắt buộc mở) |
| `n_existing_in_cell` | int32 | số trạm đang vận hành **trong chính ô này** — thứ duy nhất ràng buộc ≤1/ô xoá mất (18.902 trạm → 12.834 ô; ô đông nhất 12). Ràng buộc **không** mất phủ (đo 29/07: union trước/sau dedup trùng bit), nên nó được giữ; muốn tiêu thụ cột này phải đổi sang MCLP **có sức chứa** |
| `built_up_frac` | double | tỷ lệ đô thị hoá của ô |
| `dist_substation_m` | double | proxy đấu nối lưới |
| `penalty`, `penalty_flags` | double/list | phạt mềm land-use ∈ [0,1] + lý do audit |
| `capex_class` | string | `low`/`mid`/`high` — ràng buộc ngân sách Sprint 3 |

Format: **parquet** (canonical) + **GeoJSON điểm** (cho Kỳ, cùng chuẩn demand proxy).

---

## 7. Pipeline & lệnh

```
make landuse    CITY=hanoi     # WorldCover -> OSM cấm -> buildable_h3 -> validate
make candidates CITY=hanoi     # sinh candidate + QA gate
```

| # | Bước | Module | Output |
| --- | --- | --- | --- |
| 1 | WorldCover → lớp phủ H3 | `data/landuse/worldcover.py` | `landuse_h3.parquet` |
| 2 | OSM vùng cấm + substation | `data/landuse/osm_exclusion.py` | `exclusion_zones.parquet` · `osm_substations.parquet` |
| 3 | Gộp → khả thi | `data/landuse/build_buildable_h3.py` | **`buildable_h3.parquet`** |
| 4 | QA land-use | `data/landuse/validate.py` | `landuse_quality_report.json` |
| 5 | Sinh candidate + QA | `features/build_candidates.py` | **`candidate_sites.{parquet,geojson}`** + `_qa.json` |

**AOI** (`src/ev_siting/aoi.py`): MVP = 1 thành phố + buffer 5 km, định nghĩa bằng **tâm + bán kính**
(vì cột admin chưa có — `E-DQ3`). Preset: `hanoi`/`hcm`/`danang`/`haiphong`/`cantho`; override bằng
`--aoi-lat/--aoi-lng/--radius-km/--buffer-km`. Khi enrich admin xong, chỉ cần thay `AOI.cells()` bằng
spatial-join ranh giới — module tiêu thụ không đổi.

---

## 8. Kết quả MVP Hà Nội (snapshot lịch sử 2026-07-24)

- **AOI:** tâm (21,028 · 105,834), lõi 25 km + buffer 5 km → **3.141 ô H3**.
- Các số mục này dùng policy trước F14; chỉ là mốc lịch sử, không so với build hiện tại.
- **candidate_sites:** **1.672** candidate — T0 1.411 · T1 96 · T2 54 · **T4 111**. CapEx: low 1.411 · mid 148 · high 113.
- **QA gate:** upper-bound coverage 1,00 · freedom 1.672 (≥100) · size 1.672 (≤3.000) · anti-degenerate 1,00 ·
  grid_radius 3,0 → **5/5 PASS**.

---

## 9. Ngưỡng & hiệu chỉnh

Ngưỡng đặt trong `data/landuse/paths.py` + `features/paths.py`. `BUILT_UP_MIN = 0,05` nay chỉ kích hoạt
penalty, không loại dân cư nông thôn bằng một raster nhiễu. Gate F14 **FAIL** nếu tỷ lệ ô `pop>0 & road=0`
vượt 20%, để phát hiện thiếu coverage road. `GAPFILL_TOP_Q`, `CROP_DOMINANT` và penalty substation (mẫu số
vật lý 50 km) đều là hằng số, không phụ thuộc AOI.

---

## 10. Hợp đồng dùng `penalty` phía MCLP *(chốt sau F14 — 2026-07-28)*

**Vì sao đây là hợp đồng, không phải gợi ý.** Trước F14, `NOT_BUILT_UP` và `NO_ROAD_ACCESS`
**loại cứng** candidate; MCLP có bỏ qua `penalty` cũng không chọn được đất chưa xây / không đường.
Sau F14 hai tín hiệu đó chỉ còn là phạt mềm, nên **candidate set đã rộng ra một cách có chủ đích**:

| | national (freeze 28/07) |
| --- | --- |
| candidate | **28.075** (`low` 12.834 · `mid` 6.361 · `high` 8.880) |
| `penalty` phân vị | p50 **0,24** · p75 **0,51** · p90 **0,74** · p95 **0,92** |
| cờ | `LOW_BUILTUP` 11.302 · `NO_ROAD_ACCESS` 6.819 · `NOT_BUILT_UP` 4.138 · `CROP` 2.794 · `POP_NO_ROAD` 30 |
| **cả `NO_ROAD_ACCESS` ∧ `NOT_BUILT_UP`** | **1.337** |

> **MCLP bỏ qua `penalty` = model được phép chọn đúng những chỗ code cũ từ chối.** Đây là điểm bàn giao
> trách nhiệm rõ ràng giữa tầng dữ liệu (Giang) và tầng tối ưu (Kỳ).

### Chốt: `penalty` vào **hàm chi phí**, không vào ràng buộc khả thi

$$
\text{CapEx}_i = \text{base}(\texttt{capex\_class}_i)\times(1+\lambda\cdot \texttt{penalty}_i),
\qquad \lambda = 1{,}0 \ \text{(mặc định)}
$$

- `is_existing=True` (T0) → **CapEx = 0**, không áp công thức trên (incumbent bắt buộc mở).
- `λ = 1` ⇒ điểm `penalty=1` đắt **gấp đôi** điểm `penalty=0` cùng `capex_class`. MCLP vẫn là bài toán
  phủ; phần "khó xây" đi vào **ràng buộc ngân sách** — nơi `capex_class` vốn đã sống.

**Vì sao KHÔNG hard-filter ở tầng model** (vd loại `penalty ≥ 0,6`): làm thế là tái lập đúng lỗi F14 —
để một raster nhiễu (stride-8) và độ phủ OSM quyết định xoá cầu nông thôn. Bằng chứng trực tiếp trong
chính bản freeze: **17 trạm T0 đang vận hành thật** nằm trong ô bị gắn *đồng thời* `NO_ROAD_ACCESS` và
`NOT_BUILT_UP`. Trạm đang chạy thì hiển nhiên có đường vào ⇒ **cờ sai ở đó**, và hard-filter sẽ xoá
hạ tầng có thật. Phạt mềm giữ được chúng nhưng vẫn hạ ưu tiên.

### Hai nghĩa vụ bắt buộc phía báo cáo

1. **Cảnh báo khảo sát thực địa** cho mọi điểm được chọn có `tier=T4` **hoặc** cờ
   `NO_ROAD_ACCESS ∧ NOT_BUILT_UP`. Cùng mức với quy tắc `SYNTHETIC` đã có ở §3 — không được trình bày
   như khuyến nghị chốt.
2. **Bảng phân rã** số điểm được chọn theo `penalty_flags` và `capex_class`, để người đọc thấy bao nhiêu
   khuyến nghị dựa trên đất chưa kiểm chứng.

### Sensitivity bắt buộc trước khi chốt số

Chạy MCLP với `λ ∈ {0 · 1 · 3}` trên cùng candidate set. Nếu tập điểm chọn giữa `λ=0` và `λ=1` lệch
**> 20%**, `penalty` đang chi phối nghiệm hơn cả demand → phải soát lại trọng số ở §4 trước khi công bố.
Ghi kết quả vào report Sprint 2.

---

## 11. Chạy toàn quốc (national)

Ngoài MVP 1 thành phố, pipeline chạy được **toàn Việt Nam** trên **lưới `demand_h3` quốc gia
(268.404 ô res 8)** — dùng `--national` ở mọi bước, hoặc `make landuse-national && make candidates-national`.

> **Một tập candidate duy nhất toàn quốc (không per-tỉnh).** Per-tỉnh cần gán ô → tỉnh, nhưng cột admin
> hiện **null 100%** (`E-DQ3` chưa xong) → chưa cắt theo tỉnh được. Hệ quả: MCLP quốc gia là **một bài
> toán lớn** — phía model (Kỳ) có thể cần phân rã theo vùng; đó là quyết định của tầng model.

**National khác city ở đâu (đều tự động theo `--national`):**

| Thành phần | City | National | Lý do |
| --- | --- | --- | --- |
| AOI | disk (tâm+bán kính+buffer) | `NationalAOI` = toàn lưới `demand_h3` | VN không phải hình tròn |
| WorldCover | 1 window/ tile, đọc **từng pixel** | **18 tile** VN, **stride 8** (~80 m) + skip tile biển (404) | full VN ~3,3 tỉ pixel đất — gán H3 từng pixel là bất khả thi; stride 8 vẫn ~130 mẫu/ô |
| OSM exclusion | 1 query bbox | **quadtree** + **STRtree** bulk; **bỏ `natural=water`** (WorldCover phủ nước) | bbox VN quá lớn cho 1 query; kéo mọi polygon nước toàn VN quá nặng |
| Substation dist | vòng lặp Python | **BallTree(haversine)** | 268k ô × N trạm → phải index không gian |
| buildable mask | `iterrows` | **numpy vector hoá** | 268k dòng |
| Gate size / p_hint / gap-fill_q | 3.000 / 20 / 0,90 | **80.000 / 800 / 0,98** | national nhiều anchor hơn; gap-fill chọn lọc hơn để không phình MCLP |

Mọi ngưỡng scope-aware **override được** qua CLI (`--max-candidates`, `--p-hint`, `--gapfill-q`, `--serve-radius-km`).

**Kết quả toàn quốc (rebuild 2026-07-28, F14):**

- **WorldCover:** 16 tile đất (2 tile biển 404 bỏ qua) → `landuse_h3` **1.419.043 ô đất** (stride 8).
- **OSM exclusion:** **694 ô** bị cấm (MILITARY 327 · PROTECTED 210 · AIRPORT 158) + **2.432 trạm biến áp**.
- **buildable_h3:** 268.404 ô → **259.324 buildable (97%)**. Loại cứng: WATER 7.296 · WETLAND 4.741 ·
  PROTECTED 210 · MILITARY 327 · AIRPORT 158. `pop>0 & road=0` = **6.352/104.171 = 6%**, PASS gate ≤20%.
- **candidate_sites:** **28.075** — T0 12.834 · T1 8.688 · T2 1.828 · T4 4.725. CapEx: low 12.834 · mid 6.361 · high 8.880.
- **QA gate: 5/5 PASS** — upper-bound coverage **0,9438** · freedom 28.075 (≥4.000) · size 28.075 (≤80.000) ·
  anti-degenerate 1,00 · grid_radius 3,0.

---

## 10. Limitation (không sửa được trong scope — `DOC`)

- **Quy hoạch sử dụng đất chính thức VN không public** → WorldCover/OSM chỉ là **proxy**; điểm "buildable"
  vẫn có thể bị cấm theo quy hoạch địa phương.
- **WorldCover 2021 vs hiện tại 2026** — lệch vintage như **P10**.
- **Bias đô thị của OSM POI** — giảm nhẹ bằng T4, không khử được.
- Candidate **`SYNTHETIC` (T4)** phải kèm cảnh báo khảo sát thực địa, không dùng như khuyến nghị chốt.
- T3 (rest_area/nút giao QL) chưa có → hành lang liên tỉnh phủ chưa tối ưu (roadmap).
- **Phủ nông thôn (national):** `NOT_BUILT_UP`/`NO_ROAD_ACCESS` là penalty, không phải quyết định loại cứng.
  Candidate có cờ này vẫn cần khảo sát hạ tầng thực địa trước khi đề xuất.
