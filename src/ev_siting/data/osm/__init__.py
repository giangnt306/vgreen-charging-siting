"""OSM extraction: POI (điểm quan tâm) + road network (trắc địa) cho Việt Nam.

Nguồn công khai (SCHEMA_CONTRACT mục 3 `demand_h3`):
  - POI  → 10 cột theo LỚP tag (Overpass API): n_fuel / n_parking_off / n_parking_street
           / n_mall / n_dept_store / n_supermarket / n_market / n_apartment
           / n_apartment_complex / apartment_levels_sum  (E-DQ7c — `n_poi`+`n_parking` khai tử)
  - Roads → km/lane-mét theo LỚP highway (Geofabrik `vietnam-latest.osm.pbf`, osmium streaming)
           → road_access_m / road_len_m / road_lane_mw_m / road_lane_ar_m / road_bridge_m  (E-DQ7b)

Kết quả gộp về lưới H3 res 8 → thành phần OSM của `demand_h3` (pop lấy từ WorldPop sau).
"""
