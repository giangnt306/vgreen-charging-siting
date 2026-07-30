#!/usr/bin/env python3
"""validate.py — Cổng QA cho tầng OSM (POI + road network).

Kiểm tra tối thiểu trên các artefact interim rồi ghi `osm_quality_report.json`:
  - POI points: tọa độ nằm trong VN_BBOX, không trùng (type,id,category), có h3.
  - road H3   : road_len_m/mt_m không âm, mt_m <= m, h3_r8 hợp lệ.
  - components: 3 cột đếm không âm, không trùng h3_r8.

Thoát code != 0 nếu có kiểm tra FAIL (để chặn pipeline). WARN không chặn.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.validate
"""
import json
import sys

import pandas as pd

from ev_siting.vn_boundary import mask_points_in_vn

from .paths import DEMAND_COMPONENTS, POI_OUTSIDE_VN, POI_POINTS, QUALITY_REPORT, ROADS_H3, ensure_dirs


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def run():
    ensure_dirs()
    report = {"checks": [], "stats": {}}
    all_ok = True

    if POI_POINTS.exists():
        poi = pd.read_parquet(POI_POINTS)
        report["stats"]["n_poi_points"] = int(len(poi))
        report["stats"]["poi_by_category"] = poi["category"].value_counts().to_dict()
        # E-DQ11: kiểm tra ĐA GIÁC lãnh thổ, không phải bbox. Bản cũ hỏi `lat.between(bbox)`
        # nên luôn PASS trong khi 54,2% POI nằm ở Thái Lan/Campuchia/Quảng Tây — cổng hỏi
        # sai câu hỏi thì không bao giờ đỏ (cùng họ lỗi với F4).
        in_vn = mask_points_in_vn(poi["lat"], poi["lng"])
        n_out = int((~in_vn).sum())
        all_ok &= _check(report, "poi_coords_in_vn", n_out == 0,
                         f"{n_out} POI ngoài đa giác lãnh thổ VN")
        report["stats"]["n_poi_clipped_outside_vn"] = (
            int(len(pd.read_parquet(POI_OUTSIDE_VN))) if POI_OUTSIDE_VN.exists() else None
        )
        dup = poi.duplicated(["osm_type", "osm_id", "category"]).sum()
        all_ok &= _check(report, "poi_no_dup", dup == 0, f"{dup} trùng")
        all_ok &= _check(report, "poi_has_h3", bool(poi["h3_r8"].notna().all()), fatal=False)
    else:
        all_ok &= _check(report, "poi_points_exists", False, str(POI_POINTS))

    if ROADS_H3.exists():
        rd = pd.read_parquet(ROADS_H3)
        report["stats"]["n_road_cells"] = int(len(rd))
        report["stats"]["road_km"] = round(rd["road_len_m"].sum() / 1e3, 1)
        report["stats"]["road_mt_km"] = round(rd["road_len_mt_m"].sum() / 1e3, 1)
        all_ok &= _check(report, "road_non_negative",
                         bool((rd[["road_len_m", "road_len_mt_m"]] >= 0).all().all()))
        all_ok &= _check(report, "road_mt_le_total",
                         bool((rd["road_len_mt_m"] <= rd["road_len_m"] + 1e-6).all()))
    else:
        all_ok &= _check(report, "roads_h3_exists", False, str(ROADS_H3), fatal=False)

    if DEMAND_COMPONENTS.exists():
        comp = pd.read_parquet(DEMAND_COMPONENTS)
        report["stats"]["n_cells"] = int(len(comp))
        cnts = comp[["n_poi", "n_parking", "n_fuel"]]
        all_ok &= _check(report, "counts_non_negative", bool((cnts >= 0).all().all()))
        dup = comp.duplicated(["h3_r8"]).sum()
        all_ok &= _check(report, "components_unique_h3", dup == 0, f"{dup} trùng")
    else:
        all_ok &= _check(report, "components_exists", False, str(DEMAND_COMPONENTS))

    report["overall"] = "PASS" if all_ok else "FAIL"
    with open(QUALITY_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[{report['overall']}] -> {QUALITY_REPORT}")
    print("stats:", json.dumps(report["stats"], ensure_ascii=False))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    run()
