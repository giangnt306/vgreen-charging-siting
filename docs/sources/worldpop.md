# WorldPop — Dân số Việt Nam 2020 → `pop` theo H3, và bảng `demand_h3`

> Nguồn `pop` cho `demand_h3` ([SCHEMA_CONTRACT.md](../schema/schema-contract.md) mục 3;
> [problem-analysis.md](../problem-analysis.md) mục 2 #6). Đây là mảnh cuối ghép với tầng
> **OSM POI + road** ([crawler-osm.md](osm.md)) để có `demand_h3` đầy đủ.
> Code: `src/ev_siting/data/worldpop/`.

## Nguồn

- **WorldPop Global 2000–2020 Constrained**, Vietnam 2020, ~100m, UN-unadjusted, **CC-BY 4.0**.
- File: `vnm_ppp_2020_constrained.tif` (~27 MB) — mỗi pixel = **số người/pixel**.
- "Constrained" = chỉ phân bổ dân vào ô có dấu hiệu định cư (built-settlement) → sát thực địa,
  ít pixel rỗng hơn bản unconstrained.
- ⚠️ **Hai hệ quả của lựa chọn này đã được đo (29/07) và đang mở dưới dạng `E-DQ7e` + `E-DQ7f`** —
  xem [§ Hạn chế đã đo](#hạn-chế-đã-đo-e-dq7e--e-dq7f). Tóm tắt: bản **UN-unadjusted** làm mọi
  con số **tuyệt đối** lệch **+2,11%**, và cơ chế **constrained** dồn dân của cả xã vào vài pixel ở
  **146 ô**.
- URL neo trong [`paths.py`](../src/ev_siting/data/worldpop/paths.py) (`WORLDPOP_URL`).

## Cấu trúc & pipeline

```
src/ev_siting/data/worldpop/
├── paths.py            #  ★ đường dẫn canonical + WORLDPOP_URL
├── worldpop_pop.py     #  tải .tif + đọc theo strip (rasterio) -> pop theo H3
└── build_demand_h3.py  #  ghép pop + thành phần OSM -> demand_h3

data/raw/worldpop/vnm_ppp_2020_constrained.tif        # BẤT BIẾN (nguồn)
data/interim/worldpop/worldpop_pop_h3.parquet         # h3_r8 -> pop
data/interim/demand/demand_h3.parquet                 # ★ demand_h3 (pop + OSM)
```

```
  worldpop_pop  ── tải .tif ─▶ rasterio strip 512 hàng ─▶ pop theo ô H3 res 8
        │                        (gộp số người/pixel vào ô của tâm pixel)
        ▼
  worldpop_pop_h3.parquet ─┐
  osm_demand_components_h3 ─┴─ build_demand_h3 (outer join h3_r8) ─▶ demand/demand_h3.parquet
```

## Cách chạy

```bash
PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop        # tải + gộp pop
PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3     # ghép -> demand_h3
# ép tải lại raster:
PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop --force-download
```

## Bảng `demand_h3` (thô)

`data/interim/demand/demand_h3.parquet` — key `h3_r8`, các cột thô của contract:

| Cột | Kiểu | Nguồn |
| --- | --- | --- |
| `h3_r8` | string | lưới H3 res 8 |
| `pop` | double | WorldPop (số người trong ô) |
| `road_access_m`, `road_len_m`, `road_lane_mw_m`, `road_lane_ar_m`, `road_bridge_m` | double | OSM roads theo lớp ([crawler-osm.md](osm.md)) — **E-DQ7b** |
| `n_fuel`, `n_parking_off`, `n_parking_street`, `n_mall`, `n_dept_store`, `n_supermarket`, `n_market`, `n_apartment`, `n_apartment_complex` | int | OSM POI theo **lớp tag** ([crawler-osm.md](osm.md)) — **E-DQ7c** (`n_poi`/`n_parking` khai tử) |
| `apartment_levels_sum` | double | Σ `building:levels` quan sát được (36,1% toà có tag) — **E-DQ7c** |

**Còn thiếu (enrich sau, ngoài phạm vi bộ crawl này):**
- `admin_l1_code`, `province_name`, `commune_name`, `commune_kind` — cần join ranh giới hành chính.
- `demand_weight = f(pop, road, poi, …)` — công thức trọng số chốt ở **Sprint 2**.

## Kết quả & kiểm chứng (chạy 2026-07-22)

- **pop:** 99,63 triệu người / **104.171 ô** — khớp dân số VN 2020 (~97–98 triệu; WorldPop
  UN-unadjusted thường nhỉnh hơn thống kê). ⚠️ *"✅ sanity pass" ban đầu là một **cổng không thể FAIL***:
  nó chỉ so tổng quốc gia với một dải rộng 97–98 triệu, nên không bắt được **cả hai** khuyết tật mà
  `E-DQ7e`/`E-DQ7f` sau đó tìm ra — một cái lệch mức (+2,11%), một cái sai **vị trí trong ô** mà tổng
  quốc gia **vẫn đúng nguyên**. Cùng bài học với `poi_coords_in_vn` ở E-DQ7a.
- **demand_h3:** **268.404 ô** (union pop ∪ đường ∪ POI); 97.819 ô có **cả** dân & đường.
- Spot-check lõi đô thị (0,83 km²/ô ở VN): HCMC Q1 ≈ 27.600 người, Hà Nội Hoàn Kiếm ≈ 31.200,
  Đà Nẵng ≈ 15.800 — đúng bậc độ dày dân.
- Không có giá trị âm ở mọi cột.

## Ghi chú kỹ thuật

- **RAM-safe:** raster 8.789 × 17.796 px đọc theo **strip 512 hàng** (`rasterio.windows`),
  chỉ giữ pixel `> 0` và `!= nodata (-99999)`; tâm pixel → H3 → gộp dồn (dict) → không giữ
  toàn bộ ảnh trong RAM.
- **Tâm pixel:** raster north-up (EPSG:4326) nên `lon = c + a·(col+0.5)`, `lat = f + e·(row+0.5)`
  (`e < 0`). Sai số ≪ kích thước ô res 8 (cạnh 0,56 km, bán kính nội tiếp 0,49 km) → an toàn cho
  demand proxy. *(Bản trước ghi "cạnh ~0,46 km" — đó là bán kính nội tiếp, không phải cạnh; xem **P4**.)*
- **CRS:** WGS84 (EPSG:4326) xuyên suốt, khớp contract.
- **Diện tích ô KHÔNG phải hằng số.** Ô H3 res 8 trên lãnh thổ VN chạy **0,785–0,869 km²**
  (trung vị 0,825). Mọi ngưỡng **mật độ** phải chia bằng `h3.cell_area(cell, 'km^2')` từng ô —
  dùng một con số phẳng "0,83" lệch tới ±5% và đã từng cho ra số ô outlier sai (**E-DQ7f**).

## Hạn chế đã đo (`E-DQ7e` / `E-DQ7f`)

Hai khuyết tật **độc lập**, cùng nằm ở cột `pop`, phát hiện 29/07. Chi tiết + bằng chứng đầy đủ:
[known-issues.md — E-DQ7e](../known-issues.md#e-dq7e--pop-chưa-hiệu-chuẩn-tuyệt-đối-bước-8) ·
[E-DQ7f](../known-issues.md#e-dq7f--pop-phân-bổ-sai-chỗ-trong-ô-dasymetric-spike-bước-9).

| | **E-DQ7e** — mức tuyệt đối | **E-DQ7f** — phân bổ trong ô |
| --- | --- | --- |
| Nguyên nhân | dùng raster **UN-unadjusted** thay vì **UNadj** | mặt nạ built-settlement của BSGM bỏ sót ⇒ dồn dân cả xã vào vài pixel |
| Quy mô | 99,627 M vs **97,569 M** (**+2,11%**) | **146 ô / 792.118 dân** (0,795% dân số) |
| Bằng chứng | tỉ số UNadj/unadj = **hằng số 0,979344**, std **2,5e-08** trên 2,64M pixel | đỉnh **29.337 người trên 1 pixel 100 m** (= 2,9M/km²); 3 ô nặng nhất chỉ có **1–2 pixel ≠ 0** |
| Thứ hạng ô | **bất biến từng bit** (đơn điệu) | **có xê dịch** — 17/146 ô nằm trong top-500 `pop` toàn quốc |
| Chặn gì | chỉ phát biểu tuyệt đối (`coverage_pop`, đối chiếu GSO) | T4 gap-fill khi chạy **national** (46/146 ô `buildable`); `POP_NO_ROAD` giả (6 ô) |
| **KHÔNG** chặn | `E-DQ7d` (đơn điệu) | `E-DQ7d` — chỉ chạm **14/12.811** ô cung |
| Hướng sửa | đổi `WORLDPOP_URL` sang file **UNadj** + cập nhật MANIFEST (**E-DQ10**) — **không** hardcode hệ số | xuất `n_px`/`max_px`/`top3_px_share`/`pop_lat`/`pop_lon` ngay trong lượt gộp → cờ `POP_PIXEL_IMPLAUSIBLE`, **flag không xoá** |

⚠️ **Đừng winsorize theo mật độ.** Ngưỡng ">48.000 người/km²" bắt **67 ô lõi TP.HCM CÓ THẬT** (liền
khối, ~100 pixel/ô, 500–800 người/pixel) và **0/146** ô hỏng — **giao hai tập = 0**. Cắt ngọn sẽ san
phẳng đúng đỉnh cầu của cả nước mà không chạm được lỗi nào.
