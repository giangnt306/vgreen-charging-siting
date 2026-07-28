"""OSM extraction: POI (điểm quan tâm) + road network (trắc địa) cho Việt Nam.

Nguồn công khai (SCHEMA_CONTRACT mục 3 `demand_h3`):
  - POI  → n_poi, n_parking, n_fuel   (Overpass API, trạm xăng/TTTM/chung cư/bãi đỗ)
  - Roads → km/lane-mét theo LỚP highway (Geofabrik `vietnam-latest.osm.pbf`, osmium streaming)
           → road_access_m / road_len_m / road_lane_mw_m / road_lane_ar_m / road_bridge_m  (E-DQ7b)

Kết quả gộp về lưới H3 res 8 → thành phần OSM của `demand_h3` (pop lấy từ WorldPop sau).
"""
