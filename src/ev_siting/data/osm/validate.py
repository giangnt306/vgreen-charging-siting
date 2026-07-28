#!/usr/bin/env python3
"""validate.py — Cổng QA cho tầng OSM (POI + road network + lưới demand).

Kiểm tra tối thiểu trên các artefact interim rồi ghi `osm_quality_report.json`:
  - POI points : có cờ `in_vn`, không trùng (type,id,category), có h3.
  - road H3    : có đủ cột lớp (E-DQ7b), không âm, đối soát Σ lớp = `road_access_m`,
                 `road_len_m` ⊆ `road_access_m`, lane-mét quan sát được ở lớp trục lớn,
                 **ô chứa trạm sạc thật phải có lối vào** (cổng ngoại vi).
  - components : 3 cột đếm không âm, không trùng h3_r8, **khớp đúng số POI `in_vn`**.
  - demand_h3  : đã clip lãnh thổ, không còn ô `OUTSIDE`.

⚠️ **E-DQ7b — cổng `road_mt_le_total` cũ vô dụng.** `road_len_mt_m <= road_len_m` đúng
theo *xây dựng* (`_MAJOR ⊂` mọi đường) nên không bao giờ FAIL được. Thay bằng các cổng
**có thể FAIL**: đối soát Σ lớp (bắt lệch nhãn cột), tỉ lệ lane-mét *quan sát được*
(bắt trường hợp feature trục lớn thành số suy đoán), và đối chiếu ngoại vi với vị trí
trạm sạc đang vận hành (bắt lỗ hổng phủ đường của OSM).

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
from .road_semantics import (TIER_COLUMNS, TIERS, derive, lane_col,
                             lane_obs_col, m_col, major_lane_observed_share)

#: category -> cột đếm (phải khớp `build_osm_h3._COUNT_COL`)
_COUNT_COL = {"fuel": "n_fuel", "parking": "n_parking",
              "mall": "n_poi", "apartments": "n_poi", "retail": "n_poi"}

#: E-DQ7b — ngưỡng cổng lane-mét quan sát được ở lớp trục lớn (motorway+trunk+primary).
#: Dưới ngưỡng này `road_lane_*` chủ yếu là số SUY ĐOÁN từ mặc định theo lớp, không
#: còn là số đo -> feature trục lớn mất ý nghĩa.
MAJOR_LANE_OBS_MIN = 0.40
#: E-DQ7b — trần tỉ lệ ô có trạm sạc thật nhưng OSM không có đường nào (lỗ hổng phủ).
SUPPLY_NO_ACCESS_WARN = 0.01
SUPPLY_NO_ACCESS_FAIL = 0.02


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def _check_supply_access(report, roads):
    """E-DQ7b ⑥ — ô chứa trạm sạc đang vận hành phải có `road_access_m > 0`.

    Cổng **ngoại vi** duy nhất của tầng đường: mọi cổng khác đúng theo xây dựng, cổng
    này đối chiếu với thực địa (trạm sạc tồn tại thật ⇒ phải có đường tới). FAIL ⇒ hoặc
    OSM thiếu đường, hoặc toạ độ trạm còn sai sau E-DQ1 — cả hai đều cần biết.

    Tập cung khớp E-DQ2/E-DQ1/P8: `is_operational & PUBLIC & is_primary & coord_resolved`.
    """
    from ev_siting.data.evcs.paths import STATIONS_DIR
    import h3
    if not STATIONS_DIR.exists():
        return _check(report, "supply_cells_have_road_access", True,
                      "bỏ qua — chưa có canonical stations", fatal=False)
    st = pd.read_parquet(STATIONS_DIR)
    for col, val in (("is_operational", True), ("access", "PUBLIC"),
                     ("is_primary", True), ("coord_resolved", True)):
        if col in st.columns:
            st = st[st[col] == val]
    st = st[st["lat"].notna() & st["lng"].notna()]
    if st.empty:
        return _check(report, "supply_cells_have_road_access", True,
                      "bỏ qua — tập cung rỗng", fatal=False)

    cells = {h3.latlng_to_cell(a, b, 8) for a, b in zip(st["lat"], st["lng"])}
    with_access = set(roads.loc[roads["road_access_m"] > 0, "h3_r8"])
    missing = cells - with_access
    share = len(missing) / len(cells)
    report["stats"]["supply_cells"] = len(cells)
    report["stats"]["supply_cells_no_road_access"] = len(missing)
    report["stats"]["supply_cells_no_road_access_share"] = round(share, 4)
    detail = (f"{len(missing)}/{len(cells)} ô có trạm nhưng OSM không có đường nào "
              f"({share:.2%}; WARN >{SUPPLY_NO_ACCESS_WARN:.0%}, "
              f"FAIL >{SUPPLY_NO_ACCESS_FAIL:.0%})")
    if share > SUPPLY_NO_ACCESS_FAIL:
        return _check(report, "supply_cells_have_road_access", False, detail)
    return _check(report, "supply_cells_have_road_access",
                  share <= SUPPLY_NO_ACCESS_WARN, detail, fatal=False)


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

        # E-DQ7b ①: artefact dựng trước bản vá chỉ có 2 cột vô hướng -> chặn (stale)
        stale = [c for c in TIER_COLUMNS if c not in rd.columns]
        has_tiers = not stale
        all_ok &= _check(report, "roads_h3_has_tier_columns", has_tiers,
                         "" if has_tiers else f"thiếu {stale[:3]}… — chạy lại roads_pbf (E-DQ7b)")

        if has_tiers:
            rd = derive(rd)
            report["stats"]["road_km_by_tier"] = {
                t: round(rd[m_col(t)].sum() / 1e3, 1) for t in TIERS}
            report["stats"]["road_access_km"] = round(rd["road_access_m"].sum() / 1e3, 1)
            report["stats"]["road_km"] = round(rd["road_len_m"].sum() / 1e3, 1)
            report["stats"]["lane_mw_km"] = round(rd["road_lane_mw_m"].sum() / 1e3, 1)
            report["stats"]["lane_ar_km"] = round(rd["road_lane_ar_m"].sum() / 1e3, 1)
            report["stats"]["bridge_km"] = round(rd["road_bridge_m"].sum() / 1e3, 1)

            all_ok &= _check(report, "road_non_negative",
                             bool((rd[TIER_COLUMNS] >= 0).all().all()))

            # ② đối soát Σ lớp = road_access_m (bắt lệch nhãn cột khi ghi bảng lớp)
            diff = float((rd["road_access_m"]
                          - sum(rd[m_col(t)] for t in TIERS)).abs().max())
            all_ok &= _check(report, "road_tiers_sum_eq_access", diff < 1e-6,
                             f"lệch tối đa {diff:.3g} m")

            # ③ mạng sinh cầu ⊆ mạng lối vào; cầu/hầm ⊆ mạng lối vào
            all_ok &= _check(report, "road_len_le_access",
                             bool((rd["road_len_m"] <= rd["road_access_m"] + 1e-6).all()))
            all_ok &= _check(report, "road_bridge_le_access",
                             bool((rd["road_bridge_m"] <= rd["road_access_m"] + 1e-6).all()))

            # ④ lane-mét >= chiều dài tim (mọi way >= 1 làn) & phần quan sát ⊆ tổng
            lane_ok = all(
                bool((rd[lane_col(t)] + 1e-6 >= rd[m_col(t)]).all())
                and bool((rd[lane_obs_col(t)] <= rd[lane_col(t)] + 1e-6).all())
                for t in TIERS)
            all_ok &= _check(report, "road_lane_invariants", lane_ok,
                             "lane_m >= m và lane_obs_m <= lane_m theo từng lớp")

            # ⑤ lane-mét trục lớn phải chủ yếu là số ĐO, không phải số suy đoán
            obs = major_lane_observed_share(rd)
            report["stats"]["major_lane_observed_share"] = round(obs, 4)
            all_ok &= _check(report, "major_lane_observed_share",
                             obs >= MAJOR_LANE_OBS_MIN,
                             f"{obs:.1%} lane-mét trục lớn có tag `lanes` "
                             f"(ngưỡng {MAJOR_LANE_OBS_MIN:.0%})")

            # ⑥ CỔNG NGOẠI VI: ô có trạm sạc đang vận hành phải có lối vào.
            #    Không đúng theo xây dựng -> có thể FAIL thật (đo lỗ hổng phủ đường OSM
            #    hoặc toạ độ trạm còn sai sau E-DQ1).
            all_ok &= _check_supply_access(report, rd)
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
