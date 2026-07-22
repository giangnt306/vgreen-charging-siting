#!/usr/bin/env python3
"""build_demand_h3.py — Ghép pop (WorldPop) + thành phần OSM -> bảng `demand_h3`.

Đầu vào:
  - data/interim/worldpop/worldpop_pop_h3.parquet         (h3_r8, pop)
  - data/interim/osm/osm_demand_components_h3.parquet     (h3_r8, n_poi, n_parking,
                                                           n_fuel, road_len_m, road_len_mt_m)

Đầu ra:
  - data/interim/demand/demand_h3.parquet  — các cột thô của `demand_h3`
    (SCHEMA_CONTRACT mục 3): h3_r8, pop, road_len_m, road_len_mt_m,
    n_poi, n_parking, n_fuel. Cột admin (admin_l1_code, province_name, commune_*)
    enrich sau; `demand_weight` chốt ở Sprint 2.

Full outer join theo h3_r8: ô có dân nhưng không đường vẫn giữ (và ngược lại).

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3
"""
import pandas as pd

from ev_siting.data.osm.paths import DEMAND_COMPONENTS
from .paths import DEMAND_H3, POP_H3, ensure_dirs

_NUM_COLS = ["pop", "road_len_m", "road_len_mt_m"]
_INT_COLS = ["n_poi", "n_parking", "n_fuel"]


def run():
    ensure_dirs()
    if not POP_H3.exists():
        raise SystemExit(f"thiếu {POP_H3} — chạy worldpop_pop.py trước")
    if not DEMAND_COMPONENTS.exists():
        raise SystemExit(f"thiếu {DEMAND_COMPONENTS} — chạy osm.build_osm_h3 trước")

    pop = pd.read_parquet(POP_H3)
    osm = pd.read_parquet(DEMAND_COMPONENTS)
    df = pop.merge(osm, on="h3_r8", how="outer")

    for c in _NUM_COLS:
        df[c] = df.get(c, 0.0).fillna(0.0)
    for c in _INT_COLS:
        df[c] = df.get(c, 0).fillna(0).astype(int)

    df = df[["h3_r8"] + _NUM_COLS + _INT_COLS].sort_values(
        "pop", ascending=False).reset_index(drop=True)
    df.to_parquet(DEMAND_H3, index=False)

    print(f"[demand_h3] -> {DEMAND_H3}  ({len(df)} ô)")
    print("  tổng:", {
        "pop_M": round(df["pop"].sum() / 1e6, 2),
        "n_poi": int(df.n_poi.sum()), "n_parking": int(df.n_parking.sum()),
        "n_fuel": int(df.n_fuel.sum()),
        "road_km": round(df.road_len_m.sum() / 1e3),
        "road_mt_km": round(df.road_len_mt_m.sum() / 1e3),
    })
    both = ((df["pop"] > 0) & (df.road_len_m > 0)).sum()
    print(f"  ô có cả dân & đường: {both} / {len(df)}")
    return df


if __name__ == "__main__":
    run()
