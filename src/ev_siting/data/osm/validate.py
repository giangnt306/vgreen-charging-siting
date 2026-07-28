#!/usr/bin/env python3
"""validate.py — Cổng QA cho tầng OSM (POI + road network + lưới demand).

Kiểm tra tối thiểu trên các artefact interim rồi ghi `osm_quality_report.json`:
  - POI points : có cờ `in_vn`, không trùng (type,id,category), có h3.
  - road H3    : road_len_m/mt_m không âm, mt_m <= m.
  - components : 3 cột đếm không âm, không trùng h3_r8, **khớp đúng số POI `in_vn`**.
  - demand_h3  : đã clip lãnh thổ, không còn ô `OUTSIDE`.

⚠️ **E-DQ7a — vì sao bỏ cổng cũ `poi_coords_in_vn`.** Cổng đó kiểm "toạ độ POI nằm
trong `VN_BBOX`", tức kiểm đúng cái hộp SINH RA lỗi: `VN_BBOX` chứa trọn Phnom Penh /
Viêng Chăn / Nam Ninh nên 54,2% POI nước ngoài vẫn PASS. Cổng thay thế đối chiếu với
**polygon lãnh thổ** (`vn_boundary.py`) và đối soát số đếm — một cổng chỉ có giá trị
khi nó có thể FAIL.

Thoát code != 0 nếu có kiểm tra FAIL (để chặn pipeline). WARN không chặn.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.validate
"""
import json
import sys

import pandas as pd

from ev_siting.data.worldpop.paths import DEMAND_H3
from .paths import (DEMAND_COMPONENTS, POI_POINTS, QUALITY_REPORT, ROADS_H3,
                    VN_BBOX, VN_BOUNDARY, ensure_dirs)

#: category -> cột đếm (phải khớp `build_osm_h3._COUNT_COL`)
_COUNT_COL = {"fuel": "n_fuel", "parking": "n_parking",
              "mall": "n_poi", "apartments": "n_poi", "retail": "n_poi"}


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def run():
    ensure_dirs()
    report = {"checks": [], "stats": {}}
    all_ok = True
    s_lat, w_lon, n_lat, e_lon = VN_BBOX

    all_ok &= _check(report, "vn_boundary_exists", VN_BOUNDARY.exists(),
                     "" if VN_BOUNDARY.exists() else f"{VN_BOUNDARY} — chạy `make boundary` (E-DQ7a)")

    poi = None
    if POI_POINTS.exists():
        poi = pd.read_parquet(POI_POINTS)
        report["stats"]["n_poi_points"] = int(len(poi))
        report["stats"]["poi_by_category"] = poi["category"].value_counts().to_dict()

        # E-DQ7a: artefact dựng trước bản vá thì không có cột này -> chặn (stale)
        has_flag = "in_vn" in poi.columns
        all_ok &= _check(report, "poi_has_in_vn_flag", has_flag,
                         "" if has_flag else "thiếu cờ in_vn — chạy lại build_osm_h3 (E-DQ7a)")
        if has_flag:
            n_out = int((~poi["in_vn"]).sum())
            report["stats"]["n_poi_outside_vn"] = n_out
            report["stats"]["poi_outside_vn_share"] = round(n_out / max(len(poi), 1), 4)
            all_ok &= _check(report, "poi_in_vn_flagged", True,
                             f"{len(poi) - n_out} trong VN · {n_out} ngoài VN "
                             f"({n_out / max(len(poi), 1):.1%}) — giữ dòng, không đếm")

        # phạm vi crawl (không phải bộ lọc lãnh thổ) — sai bbox = lỗi cấu hình crawl
        tol = 0.05
        in_bbox = (poi["lat"].between(s_lat - tol, n_lat + tol)
                   & poi["lng"].between(w_lon - tol, e_lon + tol))
        all_ok &= _check(report, "poi_within_crawl_bbox", bool(in_bbox.all()),
                         f"{(~in_bbox).sum()} ngoài VN_BBOX (±{tol}°)", fatal=False)
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

        # E-DQ7a: số đếm phải bằng đúng số POI in_vn (không thừa POI nước ngoài,
        # không thiếu POI VN nằm trong ô vắt biên)
        if poi is not None and "in_vn" in poi.columns:
            want = (poi[poi["in_vn"]]["category"].map(_COUNT_COL)
                    .value_counts().reindex(["n_poi", "n_parking", "n_fuel"])
                    .fillna(0).astype(int))
            got = cnts.sum().astype(int)
            diff = {c: int(got[c] - want[c]) for c in want.index}
            all_ok &= _check(report, "counts_match_in_vn_poi",
                             all(v == 0 for v in diff.values()), json.dumps(diff))
            report["stats"]["counts"] = {c: int(got[c]) for c in want.index}
    else:
        all_ok &= _check(report, "components_exists", False, str(DEMAND_COMPONENTS))

    if DEMAND_H3.exists():
        dem = pd.read_parquet(DEMAND_H3, columns=["h3_r8", "cell_state", "frac_in_vn"])
        report["stats"]["n_demand_cells"] = int(len(dem))
        report["stats"]["demand_by_cell_state"] = dem["cell_state"].value_counts().to_dict()
        all_ok &= _check(report, "demand_clipped_to_vn",
                         not (dem["cell_state"] == "OUTSIDE").any(),
                         f"{int((dem['cell_state'] == 'OUTSIDE').sum())} ô OUTSIDE còn sót")
        all_ok &= _check(report, "demand_frac_in_vn_range",
                         bool(dem["frac_in_vn"].between(0, 1).all()))
    else:
        all_ok &= _check(report, "demand_h3_exists", False, str(DEMAND_H3), fatal=False)

    report["overall"] = "PASS" if all_ok else "FAIL"
    with open(QUALITY_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[{report['overall']}] -> {QUALITY_REPORT}")
    print("stats:", json.dumps(report["stats"], ensure_ascii=False))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    run()
