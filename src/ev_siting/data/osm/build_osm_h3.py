#!/usr/bin/env python3
"""build_osm_h3.py — Gộp POI + road network về lưới H3 res 8 (thành phần demand_h3).

Đọc:
  - data/raw/osm/poi/<category>.json   (overpass_poi.py)
  - data/interim/osm/osm_roads_h3.parquet  (roads_pbf.py)

Sinh:
  - osm_poi_points.parquet          : 1 dòng/POI đã gán h3_r8/h3_r9 (để map/QA)
  - osm_demand_components_h3.parquet : theo ô H3 res 8, các cột khớp SCHEMA_CONTRACT
        h3_r8, n_poi, n_parking, n_fuel, road_len_m, road_len_mt_m
        (pop lấy từ WorldPop ở bước sau -> khi đó ghép để có demand_h3 đầy đủ)

Quy ước n_poi = POI *sinh cầu* (mall + apartments + retail); fuel/parking tách riêng
để khớp đúng 3 cột đếm của contract.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.build_osm_h3
"""
import json

import pandas as pd

from .paths import (DEMAND_COMPONENTS, H3_RES_R8, H3_RES_R9, POI_POINTS,
                    POI_RAW_DIR, ROADS_H3, ensure_dirs)
import h3

# category -> cột đếm trong demand_h3. mall/apartments/retail dồn vào n_poi.
_COUNT_COL = {
    "fuel": "n_fuel",
    "parking": "n_parking",
    "mall": "n_poi",
    "apartments": "n_poi",
    "retail": "n_poi",
}


def load_poi_points():
    """Đọc mọi <category>.json -> DataFrame điểm đã gán H3."""
    rows = []
    for cat_file in sorted(POI_RAW_DIR.glob("*.json")):
        with open(cat_file, encoding="utf-8") as f:
            data = json.load(f)
        for el in data:
            lat, lng = el["lat"], el["lng"]
            rows.append({
                "osm_type": el["osm_type"], "osm_id": el["osm_id"],
                "category": el["category"], "name": el.get("name", ""),
                "lat": lat, "lng": lng,
                "h3_r8": h3.latlng_to_cell(lat, lng, H3_RES_R8),
                "h3_r9": h3.latlng_to_cell(lat, lng, H3_RES_R9),
            })
    df = pd.DataFrame(rows)
    # khử trùng phòng khi 1 POI lọt vào >1 nhóm (không xảy ra với tag hiện tại,
    # nhưng an toàn): 1 (osm_type, osm_id) đếm 1 lần cho mỗi category.
    if not df.empty:
        df = df.drop_duplicates(["osm_type", "osm_id", "category"]).reset_index(drop=True)
    return df


def aggregate(poi_df, roads_df):
    """Gộp đếm POI theo ô + ghép chiều dài đường -> bảng thành phần demand."""
    # đếm POI theo (h3_r8, cột đếm)
    if poi_df.empty:
        counts = pd.DataFrame(columns=["h3_r8", "n_poi", "n_parking", "n_fuel"])
    else:
        tmp = poi_df.copy()
        tmp["count_col"] = tmp["category"].map(_COUNT_COL)
        counts = (tmp.groupby(["h3_r8", "count_col"]).size()
                  .unstack("count_col", fill_value=0).reset_index())
    for col in ("n_poi", "n_parking", "n_fuel"):
        if col not in counts.columns:
            counts[col] = 0

    merged = counts.merge(roads_df, on="h3_r8", how="outer")
    for col in ("n_poi", "n_parking", "n_fuel"):
        merged[col] = merged[col].fillna(0).astype(int)
    for col in ("road_len_m", "road_len_mt_m"):
        merged[col] = merged[col].fillna(0.0)
    return merged[["h3_r8", "n_poi", "n_parking", "n_fuel",
                   "road_len_m", "road_len_mt_m"]].sort_values(
        "h3_r8").reset_index(drop=True)


def run():
    ensure_dirs()
    print("[h3] đọc POI raw + gán H3...")
    poi_df = load_poi_points()
    poi_df.to_parquet(POI_POINTS, index=False)
    print(f"[h3] {len(poi_df)} POI -> {POI_POINTS}")

    roads_df = (pd.read_parquet(ROADS_H3) if ROADS_H3.exists()
                else pd.DataFrame(columns=["h3_r8", "road_len_m", "road_len_mt_m"]))
    if not ROADS_H3.exists():
        print(f"[h3] ! chưa có {ROADS_H3.name} — chạy roads_pbf.py trước để có road_len")

    comp = aggregate(poi_df, roads_df)
    comp.to_parquet(DEMAND_COMPONENTS, index=False)
    print(f"[h3] {len(comp)} ô H3 -> {DEMAND_COMPONENTS}")
    print("      tổng:", {
        "n_poi": int(comp.n_poi.sum()),
        "n_parking": int(comp.n_parking.sum()),
        "n_fuel": int(comp.n_fuel.sum()),
        "road_km": round(comp.road_len_m.sum() / 1e3),
        "road_mt_km": round(comp.road_len_mt_m.sum() / 1e3),
    })
    return comp


if __name__ == "__main__":
    run()
