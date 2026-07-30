#!/usr/bin/env python3
"""build_buildable_h3.py — Gộp WorldCover + OSM + road access -> `buildable_h3`.

Đây là **bộ lọc khả thi cuối cùng** cho candidate site (P5). Với mỗi ô H3 trong AOI:

Loại cứng (`buildable=False`) nếu bất kỳ điều nào đúng:
  - frac_water >= WATER_MAX                       (hồ/sông/biển)
  - frac_water + frac_wetland >= WATER_WETLAND_MAX (đầm/bãi triều)
  - built_up_frac < BUILT_UP_MIN                  (núi/rừng/đất trống — chưa đô thị hoá)
  - có cờ loại trừ OSM (MILITARY/PROTECTED/AIRPORT/WATER_OSM)
  - access_tier == ISOLATED (không có đường trong ô LẪN hai vành — E-DQ8a)

Phạt mềm (giữ, hạ điểm — cột `penalty` + cờ):
  - frac_crop >= CROP_DOMINANT      -> CROP        (đất nông nghiệp)
  - built_up_frac < LOW_BUILTUP     -> LOW_BUILTUP (hạ tầng mỏng)
  - đường chỉ ở ô kề (vành 1/2)     -> NEEDS_ACCESS_ROAD    (E-DQ8a)
  - pop>0 & road=0                  -> POP_NO_ROAD (chẩn đoán E-DQ8, không loại cứng)
  - chỉ có service/track            -> ROAD_ACCESS_INFORMAL (E-DQ7b)
  - đường duy nhất là mặt cầu/hầm   -> ROAD_BRIDGE_ONLY     (E-DQ7b)
  - xa trạm biến áp                 -> dist_substation_m (proxy đấu nối lưới)

Gate F14: nếu tỷ lệ ô pop>0 mà không có đường tiếp cận (road_access_m <= 0)
vượt MAX_POP_NO_ROAD_FRAC -> fail-fast (đầu vào đường thiếu coverage).

**E-DQ8a — vì sao loại cứng theo `access_tier` chứ không `road_access_m <= 0`.** Bộ lọc cũ
loại **6.350 ô** vì "không có đường", nhưng **4.862 ô trong đó (72,1% khối lượng, 894.956
người) có đường ngay ở ô KỀ** — tâm hai ô res 8 chỉ cách 0,98 km. Đó là lỗi **thang đo**,
không phải lỗi dữ liệu, và là cùng cái bẫy mà E-DQ7a đã gỡ ở tầng biên giới (giao lục giác
thay vì tâm-ô-trong-polygon). Kiểm ngoại vi: **15 trạm đang vận hành** nằm ở ô `ADJACENT`
⇒ ô như thế xây được thật. Nay chỉ `ISOLATED` bị loại cứng, `ADJACENT`/`NEAR` chịu **phạt
mềm** (phải làm đường vào — chi phí thật). Phụ chú: bộ lọc cũ dù sao cũng gần vô ích —
chỉ **134/6.350 ô** bị loại RIÊNG bởi nó, phần còn lại đã vướng NOT_BUILT_UP/WATER/WETLAND.

**E-DQ7b — vì sao lối vào dùng `road_access_m` chứ không `road_len_m`.** Sau E-DQ7b,
`road_len_m` là mạng **sinh cầu** (đã bỏ `service`+`track`); dùng nó làm bộ lọc cứng
sẽ loại **27.828 ô**, trong đó **2.474 ô chứa 850.207 dân** và **36 ô chứa 145 trạm
sạc đang vận hành** — tức loại đúng những nơi đã chứng minh là xây được. `road_access_m`
= định nghĩa rộng (gồm `service`+`track`), **bằng đúng** `road_len_m` trước E-DQ7b nên
hành vi bộ lọc không đổi. Đường mòn vẫn là lối vào; nó chỉ không sinh nhu cầu sạc — hai
câu hỏi khác nhau, hai cột khác nhau. Xem `osm/road_semantics.py`.

Toàn bộ tính **vector hoá** (numpy + BallTree) để chạy được ở national (268k ô).

Output: data/interim/landuse/buildable_h3.parquet
  h3_r8, buildable(bool), built_up_frac, frac_water, frac_crop, road_access_m,
  road_len_m, road_bridge_m, pop, dist_substation_m, exclusion_flags(list),
  penalty_flags(list), penalty(float 0..1)

Chạy:
    PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3 --city hanoi
    PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3 --national
"""
import argparse

import numpy as np
import pandas as pd

import h3

from ev_siting.aoi import EARTH_R_KM, add_aoi_args, aoi_from_args
from ev_siting.data.osm.access_tiers import (BUILDABLE_EXCLUDED_TIERS,
                                             tiers_from_lookup)
from ev_siting.data.osm.paths import DEMAND_COMPONENTS
from ev_siting.data.worldpop.paths import DEMAND_H3
from .paths import (BUILDABLE_H3, BUILT_UP_MIN, CROP_DOMINANT, EXCLUSION_ZONES,
                    LANDUSE_H3, LOW_BUILTUP, MAX_POP_NO_ROAD_FRAC,
                    SUBSTATION_PENALTY_SCALE_M, SUBSTATIONS, WATER_MAX,
                    WATER_WETLAND_MAX, ensure_dirs)


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
    _ROAD_COLS = ["road_access_m", "road_len_m", "road_bridge_m"]
    if DEMAND_H3.exists():
        dem = pd.read_parquet(DEMAND_H3)
        stale = [c for c in _ROAD_COLS if c not in dem.columns]
        if stale:
            raise SystemExit(f"{DEMAND_H3.name} thiếu {stale} (bản trước E-DQ7b) "
                             f"— chạy lại `make demand`")
        if "access_tier" not in dem.columns:
            raise SystemExit(f"{DEMAND_H3.name} thiếu access_tier (bản trước E-DQ8a) "
                             f"— chạy lại `make demand`")
        df = df.merge(dem[["h3_r8", "pop", "access_tier"] + _ROAD_COLS],
                      on="h3_r8", how="left")
    df["pop"] = df.get("pop", 0.0).fillna(0.0).to_numpy()
    if "access_tier" not in df.columns:
        df["access_tier"] = None
    # Ô AOI KHÔNG có dòng trong `demand_h3` — hai nguồn: (a) AOI thành phố sinh đĩa hình
    # học nên chứa ô mà lưới (hợp của các ô CÓ đặc trưng) chưa biết tới; (b) ô `OUTSIDE`
    # đã bị E-DQ7a tách sang `demand_h3_clipped_out`. KHÔNG mặc định `ISOLATED` cho chúng:
    # bậc phải được TÍNH từ bảng đường, vì "không có dòng" chỉ nói lưới thiếu ô đó, không
    # nói quanh đó không có đường. Đo 30/07: 76 ô không-dòng chứa **83 trạm đang vận
    # hành**, và tính từ bảng đường ra 50 ADJACENT · 8 NEAR · 18 ISOLATED — mặc định
    # ISOLATED loại cứng đúng những ô đã có bằng chứng thực địa là xây được.
    gap = df["access_tier"].isna().to_numpy()
    if gap.any():
        comp = pd.read_parquet(DEMAND_COMPONENTS)
        lut = dict(zip(comp["h3_r8"], comp["road_access_m"]))
        cells_gap = df.loc[gap, "h3_r8"].tolist()
        df.loc[gap, "access_tier"] = tiers_from_lookup(cells_gap, lut)
        # cùng nguồn -> lấy luôn cột đường thật thay vì để 0 (0 mà bậc DIRECT là tự mâu
        # thuẫn, và `ROAD_ACCESS_INFORMAL`/`ROAD_BRIDGE_ONLY` cần số thật mới đúng)
        fill = comp.set_index("h3_r8").reindex(cells_gap)
        for c in _ROAD_COLS:
            if c in fill.columns:
                col = df[c].to_numpy(dtype=float, copy=True) if c in df.columns \
                    else np.zeros(len(df))
                col[gap] = fill[c].fillna(0.0).to_numpy()
                df[c] = col
        by = pd.Series(df.loc[gap, "access_tier"]).value_counts().to_dict()
        print(f"  [E-DQ8a] {int(gap.sum()):,} ô AOI không có trong demand_h3 -> bậc "
              f"tính từ {DEMAND_COMPONENTS.name}: {by}")
    for c in _ROAD_COLS:
        df[c] = df.get(c, 0.0).fillna(0.0).to_numpy()
    df["access_tier"] = df["access_tier"].to_numpy()

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
    # E-DQ7b: lối vào = định nghĩa RỘNG (gồm service/track) — xem docstring
    access = df["road_access_m"].to_numpy()
    # E-DQ8a: loại CỨNG theo bậc ISOLATED, không theo `road_access_m <= 0`. Bộ lọc cũ
    # loại 4.862 ô mà đường vào chỉ nằm ở ô KỀ (72% khối lượng E-DQ8) — lỗi thang đo, và
    # dù sao cũng gần vô ích: chỉ 134/6.350 ô bị loại RIÊNG bởi nó, phần còn lại đã vướng
    # NOT_BUILT_UP/WATER/WETLAND. Giữ `NO_ROAD_ACCESS` làm cờ CHẨN ĐOÁN (không loại cứng)
    # vì `buildable` vẫn cần biết ô đó chưa có đường tới tận nơi.
    tier = df["access_tier"].to_numpy()
    isolated = np.isin(tier, BUILDABLE_EXCLUDED_TIERS)
    has_osm_excl = np.array([len(f) > 0 for f in osm_flags])

    df["exclusion_flags"] = _flag_lists(
        {"WATER": water, "WETLAND": wetland,
         "NOT_BUILT_UP": not_built, "ROAD_ACCESS_ISOLATED": isolated},
        base_lists=osm_flags)
    df["buildable"] = ~(water | wetland | not_built | isolated | has_osm_excl)

    # --- PHẠT MỀM (vector hoá) ---
    crop = df["frac_crop"].to_numpy() >= CROP_DOMINANT
    low_built = df["built_up_frac"].to_numpy() < LOW_BUILTUP
    pop_no_road = (df["pop"].to_numpy() > 0) & (access <= 0)   # cờ chẩn đoán E-DQ8
    # E-DQ7b: lối vào chỉ qua service/track (giữ, hạ điểm — không loại cứng)
    informal = (access > 0) & (df["road_len_m"].to_numpy() <= 0)
    # E-DQ7b: đường duy nhất trong ô là mặt cầu/hầm -> không có chỗ đặt trụ
    bridge_only = (access > 0) & ((access - df["road_bridge_m"].to_numpy()) <= 0)
    finite = np.isfinite(dist)
    # F14 (port từ devky): chuẩn hoá bằng hằng VẬT LÝ 50 km thay vì dmax theo dữ
    # liệu — dmax làm `penalty` phụ thuộc AOI/run, không so sánh được giữa các lần.
    dist_term = np.where(finite, 0.5 * np.minimum(dist / SUBSTATION_PENALTY_SCALE_M, 1.0), 0.5)
    no_sub = ~finite

    # E-DQ8a: các cờ mềm dưới đây trước đây được PHÁT nhưng mang trọng số 0 — công thức
    # `penalty` chỉ gồm crop/low_built/dist, nên `ROAD_ACCESS_INFORMAL` (27.828 ô) và
    # `ROAD_BRIDGE_ONLY` (50 ô) bị bỏ qua trong lúc chấm điểm dù chúng nói đúng thứ P5
    # cần: chỗ đó khó đặt trụ. Nay vào công thức. Ô `ADJACENT`/`NEAR` (có đường ở vành,
    # không có trong ô) chịu phạt vì phải LÀM đường vào — đó là chi phí thật, không phải
    # lý do loại bỏ (15 trạm đang vận hành nằm ở ô ADJACENT).
    needs_access = np.isin(tier, ("ADJACENT", "NEAR"))
    penalty = np.clip(0.3 * crop + 0.2 * low_built
                      + 0.2 * needs_access + 0.1 * informal + 0.1 * bridge_only
                      + dist_term, 0.0, 1.0)
    df["penalty"] = np.round(penalty, 3)
    df["penalty_flags"] = _flag_lists(
        {"CROP": crop, "LOW_BUILTUP": low_built,
         "POP_NO_ROAD": pop_no_road, "NO_SUBSTATION": no_sub,
         "NEEDS_ACCESS_ROAD": needs_access,
         "ROAD_ACCESS_INFORMAL": informal, "ROAD_BRIDGE_ONLY": bridge_only})

    # `access_tier` là ĐẦU VÀO của bộ lọc cứng nên phải xuất ra cùng bảng — không thể
    # audit một quyết định loại bỏ bằng cột không có trong artefact (cùng lý do E-DQ7b
    # xuất `road_access_m` chứ không chỉ xuất `buildable`).
    out_cols = ["h3_r8", "buildable", "built_up_frac", "frac_water", "frac_crop",
                "road_access_m", "road_len_m", "road_bridge_m", "access_tier", "pop",
                "dist_substation_m", "exclusion_flags", "penalty_flags", "penalty"]
    out = df[out_cols].sort_values("h3_r8").reset_index(drop=True)
    out.to_parquet(BUILDABLE_H3, index=False)

    n = len(out)
    nb = int(out["buildable"].sum())
    print(f"[buildable] -> {BUILDABLE_H3}  ({n} ô AOI, {nb} buildable = {nb/n:.0%})")
    from collections import Counter
    c = Counter(f for fl in out["exclusion_flags"] for f in fl)
    print("  loại cứng theo cờ:", dict(c))
    print("  phạt mềm theo cờ:",
          dict(Counter(f for fl in out["penalty_flags"] for f in fl)))
    pop_mask = out["pop"].to_numpy() > 0
    if pop_mask.any():
        pop_excluded = int((pop_mask & ~out["buildable"].to_numpy()).sum())
        print(f"  ⚠️ ô pop>0 bị loại: {pop_excluded}/{int(pop_mask.sum())} = "
              f"{pop_excluded/pop_mask.sum():.0%} (nếu >70% -> BUILT_UP_MIN quá chặt)")
        # Gate F14 (port từ devky): quá nhiều ô có dân mà KHÔNG có đường tiếp cận
        # (`road_access_m <= 0`, ngữ nghĩa E-DQ7b) -> đầu vào đường thiếu coverage,
        # dừng sớm thay vì để bộ lọc chạy trên dữ liệu đường mù.
        no_road_pop = int(pop_no_road.sum())
        frac = no_road_pop / int(pop_mask.sum())
        print(f"  ô pop>0 không thấy road: {no_road_pop}/{int(pop_mask.sum())} "
              f"= {frac:.0%}")
        if frac > MAX_POP_NO_ROAD_FRAC:
            raise SystemExit(f"F14 FAIL: POP_NO_ROAD={frac:.1%} > "
                             f"{MAX_POP_NO_ROAD_FRAC:.0%}; road input thiếu coverage")
    return out


def run(args=None):
    ap = argparse.ArgumentParser(description="Gộp land-use -> buildable_h3 (P5)")
    add_aoi_args(ap)
    a = ap.parse_args(args)
    build(aoi_from_args(a))


if __name__ == "__main__":
    run()
