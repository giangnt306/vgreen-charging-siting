#!/usr/bin/env python3
"""build_osm_h3.py — Gộp POI + road network về lưới H3 res 8 (thành phần demand_h3).

Đọc:
  - data/raw/osm/poi/<category>.json   (overpass_poi.py)
  - data/interim/osm/osm_roads_h3.parquet  (roads_pbf.py)

Sinh:
  - osm_poi_points.parquet          : 1 dòng/POI **trong lãnh thổ VN**, đã gán h3_r8/h3_r9
  - osm_poi_outside_vn.parquet      : POI bị cắt (bbox Overpass trùm TH/LA/KH/CN) — để audit
  - osm_demand_components_h3.parquet : theo ô H3 res 8, các cột khớp SCHEMA_CONTRACT
        h3_r8, n_poi, n_parking, n_fuel, road_len_m, road_len_mt_m
        (pop lấy từ WorldPop ở bước sau -> khi đó ghép để có demand_h3 đầy đủ)

Quy ước n_poi = POI *sinh cầu* (mall + apartments + retail); fuel/parking tách riêng
để khớp đúng 3 cột đếm của contract.

E-DQ11 — CẮT BIÊN GIỚI (2026-07-29). `VN_BBOX` là hình chữ nhật nên Overpass trả về cả
Thái Lan/Lào/Campuchia/Quảng Tây: **20.256/37.362 POI (54,2%) nằm ngoài VN** (parking
65,4% · apartments 58,9% · fuel 53,4%). Lỗi lan xuống `candidate_sites`: 24,5% điểm ngoài
lãnh thổ, riêng T1 fuel 67,5% / parking 73,2%. Cắt **fail-closed ngay tại đây**: file
`POI_POINTS` chỉ chứa POI trong VN, nên mọi consumer hạ nguồn (`build_candidates._load_poi`)
sạch theo mà không cần nhớ lọc. Raw JSON vẫn bất biến, phần bị cắt ghi ra file riêng.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.build_osm_h3
"""
import json

import h3
import pandas as pd

from ev_siting.vn_boundary import mask_points_in_vn

from .paths import (
    DEMAND_COMPONENTS,
    H3_RES_R8,
    H3_RES_R9,
    POI_OUTSIDE_VN,
    POI_POINTS,
    POI_RAW_DIR,
    ROADS_H3,
    ensure_dirs,
)

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
        df["in_vn"] = mask_points_in_vn(df["lat"], df["lng"])
    else:
        df["in_vn"] = pd.Series(dtype=bool)
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
    poi_all = load_poi_points()
    poi_df = poi_all[poi_all["in_vn"]].reset_index(drop=True)
    outside = poi_all[~poi_all["in_vn"]].reset_index(drop=True)
    outside.to_parquet(POI_OUTSIDE_VN, index=False)
    poi_df.to_parquet(POI_POINTS, index=False)
    n_out = len(outside)
    print(f"[h3] {len(poi_all)} POI thô -> giữ {len(poi_df)} trong VN, cắt {n_out} ngoài biên (E-DQ11)")
    if n_out:
        by = outside["category"].value_counts()
        tot = poi_all["category"].value_counts()
        print("      cắt theo nhóm:", {k: f"{int(v)}/{int(tot[k])}" for k, v in by.items()})
    print(f"[h3] -> {POI_POINTS} | ngoài biên -> {POI_OUTSIDE_VN}")

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
