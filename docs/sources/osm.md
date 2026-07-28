# OSM — POI (điểm quan tâm) & Road network (trắc địa) cho Việt Nam

> Nguồn công khai cho **tầng cầu** (`demand_h3`) theo [SCHEMA_CONTRACT.md](../schema/schema-contract.md)
> mục 3. Đây là bộ #5 "POI & Trắc địa" trong [problem-analysis.md](../problem-analysis.md) mục 2.
> Code ở `src/ev_siting/data/osm/`, dữ liệu thô ở `data/raw/osm/`, đã xử lý ở `data/interim/osm/`.

Hai nguồn OSM độc lập, gộp về **lưới H3 res 8**:

| Nguồn | Lấy gì | Cột `demand_h3` sinh ra | Công cụ |
| --- | --- | --- | --- |
| **Overpass API** | POI: trạm xăng, bãi đỗ, TTTM, chung cư, siêu thị/chợ | `n_fuel`, `n_parking`, `n_poi` | `requests` |
| **Geofabrik `.pbf`** | Mạng lưới đường theo **lớp** `highway` (km + lane-mét) | `road_access_m`, `road_len_m`, `road_lane_mw_m`, `road_lane_ar_m`, `road_bridge_m` | `osmium` (stream) |

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
├── vn_boundary.py      #  ★ polygon lãnh thổ VN + tỉnh, trích từ .pbf đã freeze (E-DQ7a)
├── road_semantics.py   #  ★ phân lớp highway + suy dẫn cột road_* (E-DQ7b)
└── build_osm_h3.py     #  gộp POI + road về H3 -> bảng thành phần demand

data/raw/osm/                        # BẤT BIẾN
├── poi/<category>.json              #   phản hồi Overpass đã khử trùng (fuel/parking/mall/apartments/retail)
└── vietnam-latest.osm.pbf           #   dump Geofabrik (nguồn road network, ~325 MB)

data/interim/osm/                    # đã xử lý / dẫn xuất
├── vn_boundary.parquet              #   ★ 1 polygon adm2 (VN) + 40 polygon adm4 (tỉnh) — E-DQ7a/E-DQ3
├── vn_boundary.geojson              #   bản xem/QA trên map
├── vn_boundary_report.json          #   6 cổng QA polygon
├── osm_poi_points.parquet           #   1 dòng/POI + h3_r8/h3_r9 + in_vn (để map/QA)
├── osm_roads_h3.parquet             #   ★ km/lane-mét theo LỚP highway × ô H3 (E-DQ7b)
├── osm_demand_components_h3.parquet #   ★ h3_r8, n_poi, n_parking, n_fuel, road_access_m, road_len_m,
│                                    #     road_lane_mw_m, road_lane_ar_m, road_bridge_m
└── osm_quality_report.json          #   thống kê QA từ validate.py
```

## Luồng dữ liệu (pipeline)

```
  overpass_poi ── nwr[tag](bbox), quadtree tách khi >40k/lỗi ──▶ raw/osm/poi/<category>.json
        │
  roads_pbf ── tải Geofabrik .pbf ─▶ osmium stream way[highway] ─▶ interim/osm/osm_roads_h3.parquet
        │                              (lấy mẫu ~150m dọc đường, cộng vào ô H3 của điểm giữa;
        │                               ghi km/lane-mét theo TỪNG LỚP — chính sách suy ra sau, E-DQ7b)
        │
  vn_boundary ── .pbf đã freeze ─▶ relation adm2 id 49915 + adm4 ─▶ interim/osm/vn_boundary.parquet
        │                            (linemerge + polygonize; KHÔNG dùng with_areas — xem ghi chú)
        │
  build_osm_h3 ── clip POI mức ĐIỂM (in_vn) + đếm theo ô + road_semantics.derive()
        │                                  ──▶ interim/osm/osm_demand_components_h3.parquet
        │
  validate ── cổng QA (in_vn, đối soát số đếm/Σ lớp, lane quan sát, ô có trạm phải có lối vào)
        │                                  ──▶ interim/osm/osm_quality_report.json
```

## Cách chạy

```bash
# Toàn bộ (cần mạng cho Overpass + tải .pbf):
PYTHONPATH=src python -m ev_siting.data.osm.overpass_poi        # POI toàn VN
PYTHONPATH=src python -m ev_siting.data.osm.roads_pbf           # tải .pbf + road_len theo H3
PYTHONPATH=src python -m ev_siting.data.osm.vn_boundary         # polygon lãnh thổ (make boundary)
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
> để khớp đúng 3 cột đếm của [SCHEMA_CONTRACT.md](../schema/schema-contract.md#🟡-demand_h3--nhu-cầu-theo-ô-h3-11-cột--key-h3_r8).

## Ánh xạ loại đường → cột `road_*` (**E-DQ7b**)

`roads_pbf.py` **không** ghi cột chính sách nữa. Bảng `osm_roads_h3.parquet` giữ **km +
lane-mét + lane-mét-có-tag `lanes` theo TỪNG LỚP** (`m_<TIER>` / `lane_m_<TIER>` /
`lane_obs_m_<TIER>`, 9 lớp) + `bridge_m`; các cột vô hướng do
[`road_semantics.derive()`](../../src/ev_siting/data/osm/road_semantics.py) suy ra. Đổi
định nghĩa "đường" vì thế là **tính lại vài giây**, không phải stream lại 325 MB (~7 phút).

| Lớp (`TIER`) | `highway=*` | km (snapshot 2026-07-20) |
| --- | --- | ---: |
| `MOTORWAY` | `motorway`, `motorway_link` | 7.004 |
| `TRUNK` | `trunk`, `trunk_link` | 23.511 |
| `PRIMARY` | `primary`, `primary_link` | 17.660 |
| `SECONDARY` | `secondary`, `secondary_link` | 30.842 |
| `TERTIARY` | `tertiary`, `tertiary_link` | 57.252 |
| `LOCAL` | `residential`, `unclassified`, `living_street`, `road` | 449.236 |
| `SERVICE` | `service` | 70.667 |
| `TRACK` | `track` | 74.487 |
| `OTHER` | còn lại (`services`, `rest_area`, `busway`, …) | 58 |

Cột vô hướng dùng ở `demand_h3`:

| Cột | Định nghĩa | Dùng cho |
| --- | --- | --- |
| `road_access_m` | Σ mọi lớp (**gồm** `service`+`track`) | **lối vào** — `buildable_h3`, E-DQ8 |
| `road_len_m` | Σ trừ `service`+`track` | **cầu** — proxy demand |
| `road_lane_mw_m` | lane-mét `MOTORWAY` | hành lang liên tỉnh (sạc nhanh) |
| `road_lane_ar_m` | lane-mét `TRUNK`+`PRIMARY` | trục đô thị |
| `road_bridge_m` | km cầu/hầm (**tập con** của `road_access_m`) | P5 — không đặt trụ trên mặt cầu |
| ~~`road_len_mt_m`~~ | **khai tử** (đổi tên thay vì đổi nghĩa ngầm) | — |

> Chỉ có một chính sách còn nằm ở khâu trích xuất: `NON_DRIVABLE`
> (`footway`/`path`/`pedestrian`/`steps`/`cycleway`/`bridleway`/…) bị loại ngay, vì
> không phải đường lái xe được theo **bất kỳ** định nghĩa downstream nào.

## Ghi chú kỹ thuật

- **`VN_BBOX` là phạm vi CRAWL, không phải bộ lọc lãnh thổ** (**E-DQ7a**). Hộp
  `(8, 102, 23.7, 110)` chứa trọn Phnom Penh / Viêng Chăn / Nam Ninh / Hải Nam →
  **54,2% POI** thu về nằm ngoài VN. Clip dùng polygon `admin_level=2` (relation
  **49915**) trích từ chính `.pbf` **đã freeze** — không thêm nguồn thô, không re-crawl
  Overpass bằng `(poly:…)` (614 way ⇒ query cực nặng + phá snapshot E-DQ10).
- **Ráp ring thủ công thay vì `FileProcessor.with_areas()`:** bộ ráp area của osmium trả
  về **rỗng** cho relation 49915 vì 15/614 way outer bị Geofabrik cắt ở mép extract →
  ring không khép, assembler bỏ qua **im lặng**. `linemerge` + `polygonize` chịu được.
  Vì chế độ lỗi là im lặng nên cổng QA **neo điểm** (6 điểm VN phải trong, 5 điểm nước
  ngoài **nằm trong `VN_BBOX`** phải ngoài) là bắt buộc.
- **Clip POI ở mức ĐIỂM, phân loại lưới ở mức Ô** (`cell_state`/`frac_in_vn` trên
  `demand_h3`), và test ô là **giao lục giác ∩ polygon** chứ không phải tâm-ô-trong-polygon:
  ô res 8 có bán kính nội tiếp 0,49 km nên test theo tâm ô xoá nhầm **74.642 dân VN**
  (so với 6.472 khi test theo giao).
- **`road_len` cũng rò rỉ:** dump Geofabrik cắt bằng polygon **có đệm**, không cắt đúng
  biên → 8.934 km đường ngoài VN (96% trong 10 km quanh biên).
- **Hai cột đường, hai nhiệm vụ** (**E-DQ7b**). `road_len_m` cũ phải phục vụ hai định
  nghĩa mâu thuẫn: bộ lọc cứng `NO_ROAD_ACCESS` cần định nghĩa **rộng** (đường đất vẫn
  là lối vào), proxy cầu cần định nghĩa **hẹp** (đường mòn không sinh nhu cầu sạc). Đo
  thật: bỏ `service`+`track` khỏi **một** cột đẩy ô `road=0` từ 6.350 → 34.178, trong đó
  **2.474 ô chứa 850.207 dân** và **36 ô chứa 145 trạm sạc đang vận hành**. Vì vậy tách
  `road_access_m` (lối vào) / `road_len_m` (cầu); `road_access_m` **bằng đúng**
  `road_len_m` trước 7b nên `buildable_h3` không lệch hành vi.
- **Double-count đường đôi — sửa bằng lane-mét, không nhân 0,5** (**E-DQ7b**). Đường đôi
  có dải phân cách vẽ thành 2 way một chiều (motorway **96,9%** `oneway`) ⇒ 1 hành lang
  tính 2 lần, còn đường 4 làn không phân cách chỉ tính 1 lần. Nhân 0,5 cho mọi way
  `oneway` là sai (3.028 km `oneway` lớp LOCAL là cặp phố một chiều thật). Lane-mét là
  số **đo được** đúng ở nơi cần: `lanes` có tag ở **97,4% motorway · 50,4% trunk · 40,6%
  primary** nhưng chỉ **0,6% residential** → chỉ dùng lane-mét cho trục lớn.
- **`service` không tách được theo subtype ở VN:** **86%** (61.032/70.667 km) không có
  tag `service=*`, `parking_aisle` chỉ **214 km** → phải xử lý `service` như một khối.
- **Lệch nhãn cột là chế độ lỗi im lặng.** Accumulator của `RoadHandler` gom vào list
  phẳng rồi đặt tên bằng `TIER_COLUMNS`; nếu hai bên khác thứ tự thì số vẫn không âm và
  vẫn cộng ra tổng "đẹp" nhưng gán sai lớp (`road_access_m` ra 205.936 km thay vì
  730.718 km). Chỉ số slot nay tra thẳng từ `TIER_COLUMNS.index(...)`, kèm cổng QA
  `road_tiers_sum_eq_access` + `road_lane_invariants` và test khoá layout.
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
  (cạnh 0,56 km, bán kính nội tiếp 0,49 km) bước lấy mẫu 150 m ≪ kích thước ô → sai số
  biên nhỏ, đủ tốt cho demand proxy.
  > ⚠️ Con số "cạnh ~0,46 km" ở bản trước là **bán kính nội tiếp**, không phải cạnh — bảng
  > H3 v3 ghi nhầm hai đại lượng này (v4 đã sửa). Với lục giác đều: cạnh `a` = bán kính
  > **ngoại tiếp**; bán kính **nội tiếp** `r = a·√3/2`; tâm–tâm `d = a·√3 = 2r`. Xem **P4**.
- **CRS:** WGS84 (EPSG:4326) xuyên suốt, khớp contract.
