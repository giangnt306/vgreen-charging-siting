# OSM — POI (điểm quan tâm) & Road network (trắc địa) cho Việt Nam

> Nguồn công khai cho **tầng cầu** (`demand_h3`) theo [SCHEMA_CONTRACT.md](SCHEMA_CONTRACT.md)
> mục 3. Đây là bộ #5 "POI & Trắc địa" trong [problem-analysis.md](problem-analysis.md) mục 2.
> Code ở `src/ev_siting/data/osm/`, dữ liệu thô ở `data/raw/osm/`, đã xử lý ở `data/interim/osm/`.

Hai nguồn OSM độc lập, gộp về **lưới H3 res 8**:

| Nguồn | Lấy gì | Cột `demand_h3` sinh ra | Công cụ |
| --- | --- | --- | --- |
| **Overpass API** | POI: trạm xăng, bãi đỗ, TTTM, chung cư, siêu thị/chợ | `n_fuel`, `n_parking`, `n_poi` | `requests` |
| **Geofabrik `.pbf`** | Mạng lưới đường (mọi loại lái xe được) + trục lớn | `road_len_m`, `road_len_mt_m` | `osmium` (stream) |

> `pop` (WorldPop) **chưa** thuộc phạm vi bộ này → ghép ở bước demand sau. Bảng
> `osm_demand_components_h3.parquet` là **phần OSM** của `demand_h3`; join thêm `pop`
> để có bảng `demand_h3` đầy đủ, rồi mới tính `demand_weight = f(pop, road, poi, …)`.

## Cấu trúc thư mục

```
src/ev_siting/data/osm/
├── __init__.py
├── paths.py            #  ★ đường dẫn canonical (anchor PROJECT_ROOT) + VN_BBOX + H3 res
├── overpass_poi.py     #  POI qua Overpass (quadtree tách bbox khi quá tải)
├── roads_pbf.py        #  tải .pbf + stream osmium -> road_len theo H3
└── build_osm_h3.py     #  gộp POI + road về H3 -> bảng thành phần demand

data/raw/osm/                        # BẤT BIẾN
├── poi/<category>.json              #   phản hồi Overpass đã khử trùng (fuel/parking/mall/apartments/retail)
└── vietnam-latest.osm.pbf           #   dump Geofabrik (nguồn road network, ~325 MB)

data/interim/osm/                    # đã xử lý / dẫn xuất
├── osm_poi_points.parquet           #   1 dòng/POI + h3_r8/h3_r9 (để map/QA)
├── osm_roads_h3.parquet             #   road_len_m, road_len_mt_m theo ô H3
├── osm_demand_components_h3.parquet #   ★ h3_r8, n_poi, n_parking, n_fuel, road_len_m, road_len_mt_m
└── osm_quality_report.json          #   thống kê QA từ validate.py
```

## Luồng dữ liệu (pipeline)

```
  overpass_poi ── nwr[tag](bbox), quadtree tách khi >40k/lỗi ──▶ raw/osm/poi/<category>.json
        │
  roads_pbf ── tải Geofabrik .pbf ─▶ osmium stream way[highway] ─▶ interim/osm/osm_roads_h3.parquet
        │                              (lấy mẫu ~150m dọc đường, cộng chiều dài vào ô H3 của điểm giữa)
        │
  build_osm_h3 ── đếm POI theo ô + ghép road_len ──▶ interim/osm/osm_demand_components_h3.parquet
        │
  validate ── cổng QA (tọa độ trong VN, phủ tỉnh, non-negative) ──▶ interim/osm/osm_quality_report.json
```

## Cách chạy

```bash
# Toàn bộ (cần mạng cho Overpass + tải .pbf):
PYTHONPATH=src python -m ev_siting.data.osm.overpass_poi        # POI toàn VN
PYTHONPATH=src python -m ev_siting.data.osm.roads_pbf           # tải .pbf + road_len theo H3
PYTHONPATH=src python -m ev_siting.data.osm.build_osm_h3        # gộp -> bảng thành phần demand
PYTHONPATH=src python -m ev_siting.data.osm.validate            # cổng QA

# Chỉ vài nhóm POI:
PYTHONPATH=src python -m ev_siting.data.osm.overpass_poi --only fuel parking
# Ép tải lại .pbf:
PYTHONPATH=src python -m ev_siting.data.osm.roads_pbf --force-download
```

## Ánh xạ tag OSM → nhóm POI

| Nhóm (`category`) | Tag OSM | Cột đếm | Ý nghĩa (problem-analysis #5) |
| --- | --- | --- | --- |
| `fuel` | `amenity=fuel` | `n_fuel` | Trạm xăng (điểm sạc tương lai / lưu lượng xe) |
| `parking` | `amenity=parking` | `n_parking` | Bãi đỗ (chỗ đặt trụ + dừng đỗ lâu) |
| `mall` | `shop=mall`, `shop=department_store` | `n_poi` | TTTM |
| `apartments` | `building=apartments` | `n_poi` | Chung cư (sạc qua đêm cư dân) |
| `retail` | `shop=supermarket`, `amenity=marketplace` | `n_poi` | Siêu thị / chợ (điểm đến đông) |

> `n_poi` = POI **sinh cầu** (mall + apartments + retail). `fuel`/`parking` tách riêng
> để khớp đúng 3 cột đếm của [SCHEMA_CONTRACT.md](SCHEMA_CONTRACT.md#🟡-demand_h3--nhu-cầu-theo-ô-h3-11-cột--key-h3_r8).

## Ánh xạ loại đường → `road_len_*`

- `road_len_m` = tổng chiều dài **mọi đường lái xe được** (loại trừ hạ tầng đi bộ/xe đạp:
  `footway/path/pedestrian/steps/cycleway/bridleway/…`).
- `road_len_mt_m` = chiều dài **trục lớn**: `motorway` (cao tốc) + `trunk`/`primary`
  (quốc lộ) + nhánh nối tương ứng.

## Ghi chú kỹ thuật

- **Overpass — tách bbox đệ quy (quadtree):** cả nước là vùng lớn; nếu 1 bbox trả về
  `≥ 40k` phần tử hoặc server lỗi/timeout → tách 4 góc, thu nhỏ tới cạnh tối thiểu
  `0,05°`. `nwr` + `out center` để way/relation có tâm. Khử trùng theo `(type, id)` vì
  way giáp ranh có thể xuất hiện ở 2 ô.
- **Overpass — User-Agent bắt buộc:** endpoint chặn UA mặc định của `requests` (trả
  `406 Not Acceptable`) → khai báo UA rõ ràng + backoff khi `429/504`, nghỉ giữa call.
- **Roads — vì sao dùng `.pbf` chứ không Overpass:** mạng đường cả nước có hàng triệu
  `way` → Overpass không kham nổi. Dump Geofabrik + `osmium` (C++) stream nhanh, gom
  thẳng về H3 nên **không giữ segment trong RAM**.
- **Phân bổ chiều dài theo ô:** node đường thưa (đoạn thẳng có thể >1 km) → lấy mẫu dọc
  polyline mỗi ~150 m, cộng chiều dài đoạn con vào ô H3 của **điểm giữa**. Ở res 8
  (cạnh ~0,46 km) sai số biên nhỏ, đủ tốt cho demand proxy.
- **CRS:** WGS84 (EPSG:4326) xuyên suốt, khớp contract.
