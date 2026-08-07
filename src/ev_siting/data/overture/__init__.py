"""Overture Maps Places — nguồn POI ĐỘC LẬP để đối chiếu tầng POI của OSM (E-DQ7c).

`osm/poi_recall.py` đo được recall FUEL **35,9%** / PARKING_OFF **9,6%** bằng chính tập
cung 19.015 trạm sạc. Đó là bằng chứng *thiếu POI thật*, nhưng nó chỉ trả lời được
"OSM thiếu bao nhiêu **ở nơi có trạm sạc**" — không nói được thiếu ở đâu trên cả nước,
và không có nguồn nào để bù. Overture Places (Meta + Microsoft + OSM, CDLA-Permissive)
là nguồn duy nhất vừa **phủ toàn quốc**, vừa **có toạ độ**, vừa **dùng lại được về
pháp lý** — xem F1 trong `docs/known-issues.md`.

Ba module, cùng khuôn với `data/osm/`:
  - `fetch_places.py`  : quét S3 Overture (DuckDB + httpfs) theo `VN_BBOX` → raw parquet
                         **giữ nguyên `category` gốc** (đổi định nghĩa lớp = chạy lại
                         `build_poi`, KHÔNG crawl lại — nguyên tắc C1 của E-DQ7c)
  - `build_poi.py`     : raw → `overture_poi_points` (clip lãnh thổ fail-closed, H3,
                         `poi_class` cùng bảng chữ với `poi_semantics.CLASSES`)
  - `compare_osm.py`   : đối chiếu 2 nguồn — số lượng, ghép cặp không gian, độ tươi
"""
