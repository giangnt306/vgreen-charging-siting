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
| `n_poi`, `n_parking`, `n_fuel` | int | OSM POI |

**Còn thiếu (enrich sau, ngoài phạm vi bộ crawl này):**
- `admin_l1_code`, `province_name`, `commune_name`, `commune_kind` — cần join ranh giới hành chính.
- `demand_weight = f(pop, road, poi, …)` — công thức trọng số chốt ở **Sprint 2**.

## Kết quả & kiểm chứng (chạy 2026-07-22)

- **pop:** 99,63 triệu người / **104.171 ô** — khớp dân số VN 2020 (~97–98 triệu; WorldPop
  UN-unadjusted thường nhỉnh hơn thống kê). ✅ sanity pass.
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
