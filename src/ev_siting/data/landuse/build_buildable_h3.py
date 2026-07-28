#!/usr/bin/env python3
"""build_buildable_h3.py — Gộp WorldCover + OSM + road access -> `buildable_h3`.

Đây là **bộ lọc khả thi cuối cùng** cho candidate site (P5). Với mỗi ô H3 trong AOI:

Loại cứng (`buildable=False`) nếu bất kỳ điều nào đúng:
  - frac_water >= WATER_MAX                       (hồ/sông/biển)
  - frac_water + frac_wetland >= WATER_WETLAND_MAX (đầm/bãi triều)
  - built_up_frac < BUILT_UP_MIN                  (núi/rừng/đất trống — chưa đô thị hoá)
  - có cờ loại trừ OSM (MILITARY/PROTECTED/AIRPORT/WATER_OSM)
  - road_len_m <= 0 trong ô (không có đường tiếp cận — từ demand_h3)

Phạt mềm (giữ, hạ điểm — cột `penalty` + cờ):
  - frac_crop >= CROP_DOMINANT      -> CROP        (đất nông nghiệp)
  - built_up_frac < LOW_BUILTUP     -> LOW_BUILTUP (hạ tầng mỏng)
  - pop>0 & road=0                  -> POP_NO_ROAD (lỗi OSM khả nghi — §7 #9)
  - xa trạm biến áp                 -> dist_substation_m (proxy đấu nối lưới)

Toàn bộ tính **vector hoá** (numpy + BallTree) để chạy được ở national (268k ô).

Output: data/interim/landuse/buildable_h3.parquet
  h3_r8, buildable(bool), built_up_frac, frac_water, frac_crop, road_len_m, pop,
  dist_substation_m, exclusion_flags(list), penalty_flags(list), penalty(float 0..1)

Chạy:
    PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3 --city hanoi
    PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3 --national
"""
import argparse

import h3
import numpy as np
import pandas as pd

from ev_siting.aoi import EARTH_R_KM, add_aoi_args, aoi_from_args
from ev_siting.data.worldpop.paths import DEMAND_H3

from .paths import (
    BUILDABLE_H3,
    BUILT_UP_MIN,
    CROP_DOMINANT,
    EXCLUSION_ZONES,
    LANDUSE_H3,
    LOW_BUILTUP,
    MAX_POP_NO_ROAD_FRAC,
    NOT_BUILT_PENALTY,
    NO_ROAD_PENALTY,
    SUBSTATION_PENALTY_SCALE_M,
    SUBSTATIONS,
    WATER_MAX,
    WATER_WETLAND_MAX,
    ensure_dirs,
)


def _dist_to_substations_m(latlng, subs):
    """Khoảng cách (m) từ mỗi ô tới trạm biến áp gần nhất (BallTree haversine).
    inf nếu không có trạm nào."""
    n = len(latlng)
    if subs is None or subs.empty:
        return np.full(n, np.inf)
    from sklearn.neighbors import BallTree
    sub_rad = np.radians(subs[["lat", "lng"]].to_numpy())
    tree = BallTree(sub_rad, metric="haversine")
    cell_rad = np.radians(np.asarray(latlng))
    dist_rad, _ = tree.query(cell_rad, k=1)
    return dist_rad[:, 0] * EARTH_R_KM * 1000.0


def _flag_lists(masks: dict[str, np.ndarray], base_lists=None):
    """Ghép cờ theo mask boolean thành cột list (vector hoá theo cột, không iterrows).

    `masks`: nhãn -> mảng bool. `base_lists`: list gốc mỗi dòng (vd cờ OSM) để nối thêm.
    """
    n = len(next(iter(masks.values())))
    out = [list(base_lists[i]) if base_lists is not None else [] for i in range(n)]
    for label, m in masks.items():
        idx = np.nonzero(m)[0]
        for i in idx:
            out[i].append(label)
    return [sorted(set(x)) for x in out]


def build(aoi):
    ensure_dirs()
    cells = aoi.cells()
    latlng = np.array([h3.cell_to_latlng(c) for c in cells])
    df = pd.DataFrame({"h3_r8": cells})

    # --- WorldCover lớp phủ ---
    if not LANDUSE_H3.exists():
        raise SystemExit(f"thiếu {LANDUSE_H3} — chạy landuse.worldcover trước")
    wc = pd.read_parquet(LANDUSE_H3)
    df = df.merge(wc, on="h3_r8", how="left")
    for col in ("built_up_frac", "frac_water", "frac_wetland", "frac_crop"):
        df[col] = df.get(col, 0.0).fillna(0.0).to_numpy()

    # --- demand_h3: road access + pop ---
    if DEMAND_H3.exists():
        dem = pd.read_parquet(DEMAND_H3)[["h3_r8", "road_len_m", "pop"]]
        df = df.merge(dem, on="h3_r8", how="left")
    df["road_len_m"] = df.get("road_len_m", 0.0).fillna(0.0).to_numpy()
    df["pop"] = df.get("pop", 0.0).fillna(0.0).to_numpy()

    # --- OSM exclusion flags ---
    osm_flags = [[] for _ in range(len(df))]
    if EXCLUSION_ZONES.exists():
        ez = pd.read_parquet(EXCLUSION_ZONES).set_index("h3_r8")["excl_flags"]
        pos = {c: i for i, c in enumerate(cells)}
        for cell, fl in ez.items():
            i = pos.get(cell)
            if i is not None:
                osm_flags[i] = list(fl)

    # --- khoảng cách trạm biến áp ---
    subs = pd.read_parquet(SUBSTATIONS) if SUBSTATIONS.exists() else None
    dist = _dist_to_substations_m(latlng, subs)
    df["dist_substation_m"] = dist

    # --- LOẠI CỨNG (vector hoá) ---
    water = df["frac_water"].to_numpy() >= WATER_MAX
    wetland = (df["frac_water"].to_numpy() + df["frac_wetland"].to_numpy()) >= WATER_WETLAND_MAX
    not_built = df["built_up_frac"].to_numpy() < BUILT_UP_MIN
    no_road = df["road_len_m"].to_numpy() <= 0
    has_osm_excl = np.array([len(f) > 0 for f in osm_flags])

    df["exclusion_flags"] = _flag_lists({"WATER": water, "WETLAND": wetland}, base_lists=osm_flags)
    df["buildable"] = ~(water | wetland | has_osm_excl)

    # --- PHẠT MỀM (vector hoá) ---
    crop = df["frac_crop"].to_numpy() >= CROP_DOMINANT
    low_built = df["built_up_frac"].to_numpy() < LOW_BUILTUP
    pop_no_road = (df["pop"].to_numpy() > 0) & (df["road_len_m"].to_numpy() == 0)
    finite = np.isfinite(dist)
    dist_term = np.where(finite, 0.5 * np.minimum(dist / SUBSTATION_PENALTY_SCALE_M, 1.0), 0.5)
    no_sub = ~finite

    penalty = np.clip(0.3 * crop + 0.2 * low_built + NOT_BUILT_PENALTY * not_built
                      + NO_ROAD_PENALTY * no_road + dist_term, 0.0, 1.0)
    df["penalty"] = np.round(penalty, 3)
    df["penalty_flags"] = _flag_lists(
        {"CROP": crop, "LOW_BUILTUP": low_built, "NOT_BUILT_UP": not_built,
         "NO_ROAD_ACCESS": no_road,
         "POP_NO_ROAD": pop_no_road, "NO_SUBSTATION": no_sub})

    out_cols = ["h3_r8", "buildable", "built_up_frac", "frac_water", "frac_crop",
                "road_len_m", "pop", "dist_substation_m",
                "exclusion_flags", "penalty_flags", "penalty"]
    out = df[out_cols].sort_values("h3_r8").reset_index(drop=True)
    out.to_parquet(BUILDABLE_H3, index=False)

    n = len(out)
    nb = int(out["buildable"].sum())
    print(f"[buildable] -> {BUILDABLE_H3}  ({n} ô AOI, {nb} buildable = {nb/n:.0%})")
    from collections import Counter
    c = Counter(f for fl in out["exclusion_flags"] for f in fl)
    print("  loại cứng theo cờ:", dict(c))
    pop_mask = out["pop"].to_numpy() > 0
    if pop_mask.any():
        no_road_pop = int(pop_no_road.sum())
        frac = no_road_pop / int(pop_mask.sum())
        print(f"  ô pop>0 không thấy road: {no_road_pop}/{int(pop_mask.sum())} = {frac:.0%}")
        if frac > MAX_POP_NO_ROAD_FRAC:
            raise SystemExit(f"F14 FAIL: POP_NO_ROAD={frac:.1%} > {MAX_POP_NO_ROAD_FRAC:.0%}; road input thiếu coverage")
    return out


def run(args=None):
    ap = argparse.ArgumentParser(description="Gộp land-use -> buildable_h3 (P5)")
    add_aoi_args(ap)
    a = ap.parse_args(args)
    build(aoi_from_args(a))


if __name__ == "__main__":
    run()
