#!/usr/bin/env python3
"""build_demand_h3.py — Ghép pop (WorldPop) + thành phần OSM -> bảng `demand_h3`.

Đầu vào:
  - data/interim/worldpop/worldpop_pop_h3.parquet         (h3_r8, pop)  — WorldPop 2020
  - data/interim/worldpop/worldpop_pop_2025_h3.parquet    (h3_r8, pop)  — WorldPop 2025
  - data/interim/osm/osm_demand_components_h3.parquet     (h3_r8, n_poi, n_parking,
                                                           n_fuel, road_len_m, road_len_mt_m)

Đầu ra:
  - data/interim/demand/demand_h3.parquet  — các cột thô của `demand_h3`
    (SCHEMA_CONTRACT mục 3): h3_r8, pop, road_len_m, road_len_mt_m,
    n_poi, n_parking, n_fuel + `pop_2025` và 3 cờ phủ. Cột admin (admin_l1_code,
    province_name, commune_*) enrich sau; `demand_weight` chốt ở Sprint 2.

Full outer join theo h3_r8: ô có dân nhưng không đường vẫn giữ (và ngược lại).

BA THAY ĐỔI 2026-07-29 — cả ba đều để **không nói dối bằng số 0**:

1. CẮT LÃNH THỔ (E-DQ11). Lưới trước đây lấy nguyên union nên nhiễm **15.752 ô ngoài VN**
   (5,9%), 7.000 trong số đó tồn tại CHỈ nhờ POI Thái/Campuchia lọt qua bbox Overpass.
   AOI quốc gia = `demand_h3.h3_r8` nên rác này chảy thẳng vào MCLP: 24,5% `candidate_sites`
   nằm ngoài lãnh thổ. Nay giữ ô nào **chạm** đa giác VN (intersects, không chỉ tâm-trong —
   quy tắc tâm-trong bỏ mất 0,075M người và 11.259 km đường ở vành biên).

2. KHÔNG PHỦ ≠ BẰNG 0 (E-DQ8). `fillna(0)` cũ khiến "ô nằm ngoài mặt nạ raster" không phân
   biệt được với "đo được 0 người". Với bản 2020 đó là **60,3% số ô có đường** bị ghi
   `pop = 0.0` như một phép đo. Nay: `pop`/`road_len_*` để **NaN** khi nguồn không có bản
   ghi, kèm cờ `pop_covered` / `pop_2025_covered` / `osm_covered`. Dtype vẫn float64 nên
   không consumer nào phải đổi (`.fillna(0.0)` hạ nguồn giữ nguyên, và giờ nó là một
   *quyết định tường minh* chứ không phải mặc định vô hình).

3. HAI NIÊN ĐẠI SONG SONG. `pop` = 2020 (giữ nguyên mặc định, không phá pre-reg track
   assess), `pop_2025` = R2024B. Xem docstring `worldpop_pop.py` cho bằng chứng trọng tài
   OSM: mặt nạ 2020 quá chặt, nhưng 2025 lại thấp bất thường ở Tây Nam Bộ. Giữ cả hai để
   chạy MCLP hai lần và **đo** độ nhạy thay vì chọn mù.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3
"""
import pandas as pd

from ev_siting.data.osm.paths import DEMAND_COMPONENTS
from ev_siting.vn_boundary import mask_cells_touching_vn

from .paths import DEMAND_H3, POP_H3, POP_H3_2025, ensure_dirs

_NUM_COLS = ["pop", "pop_2025", "road_len_m", "road_len_mt_m"]
_INT_COLS = ["n_poi", "n_parking", "n_fuel"]
_FLAG_COLS = ["pop_covered", "pop_2025_covered", "osm_covered"]
# Cột do `settlement.py` sinh (DEGURBA + đĩa k=1 + cờ đất đai). Ghép vào đây nếu đã có, để
# rebuild `demand_h3` KHÔNG âm thầm làm mất chúng; niên đại phụ nằm ở `settlement_h3.parquet`.
_SETTLE_COLS = [
    "pop_k1",
    "dens_ppkm2",
    "settlement_class",
    "cluster_id",
    "cluster_pop",
    "cluster_n_cells",
    "centre_id",
    "centre_pop",
    "centre_n_cells",
    "pop_unsupported",
]
OUT_COLS = ["h3_r8"] + _NUM_COLS + _INT_COLS + _FLAG_COLS


def run():
    ensure_dirs()
    if not POP_H3.exists():
        raise SystemExit(f"thiếu {POP_H3} — chạy worldpop_pop.py trước")
    if not DEMAND_COMPONENTS.exists():
        raise SystemExit(f"thiếu {DEMAND_COMPONENTS} — chạy osm.build_osm_h3 trước")

    pop = pd.read_parquet(POP_H3)
    osm = pd.read_parquet(DEMAND_COMPONENTS)
    df = pop.merge(osm, on="h3_r8", how="outer", indicator="_src")
    df["pop_covered"] = df["_src"].isin(["left_only", "both"]).to_numpy()
    df["osm_covered"] = df["_src"].isin(["right_only", "both"]).to_numpy()
    df = df.drop(columns="_src")

    if POP_H3_2025.exists():
        p25 = pd.read_parquet(POP_H3_2025).rename(columns={"pop": "pop_2025"})
        df = df.merge(p25, on="h3_r8", how="outer")
        df["pop_2025_covered"] = df["pop_2025"].notna().to_numpy()
    else:
        print(f"[demand_h3] ! chưa có {POP_H3_2025.name} — chạy `worldpop_pop --vintage 2025`")
        df["pop_2025"] = float("nan")
        df["pop_2025_covered"] = False
    for c in _FLAG_COLS:
        df[c] = df[c].fillna(False).astype(bool)

    # E-DQ11: cắt về lãnh thổ VN TRƯỚC khi báo cáo, để mọi con số dưới đây là số của VN.
    n_before = len(df)
    keep = mask_cells_touching_vn(df["h3_r8"])
    dropped = df[~keep]
    df = df[keep].reset_index(drop=True)
    print(f"[demand_h3] cắt lãnh thổ: {n_before:,} -> {len(df):,} ô (bỏ {n_before - len(df):,} ngoài VN; "
          f"trong đó {int((dropped['n_poi'] + dropped['n_parking'] + dropped['n_fuel']).sum()):,} POI, "
          f"{dropped['road_len_m'].sum() / 1e3:,.0f} km đường)")

    # KHÔNG fillna cột đo được: NaN = nguồn không phủ ô này (đọc kèm cờ *_covered).
    for c in _NUM_COLS:
        if c not in df.columns:
            df[c] = float("nan")
        df[c] = df[c].astype("float64")
    for c in _INT_COLS:
        df[c] = df.get(c, 0).fillna(0).astype(int)

    from .settlement import SETTLEMENT_H3

    cols = list(OUT_COLS)
    if SETTLEMENT_H3.exists():
        st = pd.read_parquet(SETTLEMENT_H3)
        have = [c for c in _SETTLE_COLS if c in st.columns]
        df = df.merge(st[["h3_r8"] + have], on="h3_r8", how="left")
        cols += have
        print(f"[demand_h3] ghép {len(have)} cột từ {SETTLEMENT_H3.name}")
    else:
        print(f"[demand_h3] ! chưa có {SETTLEMENT_H3.name} — chạy `settlement` sau bước này")

    df = df[cols].sort_values("pop", ascending=False, na_position="last").reset_index(drop=True)
    df.to_parquet(DEMAND_H3, index=False)

    print(f"[demand_h3] -> {DEMAND_H3}  ({len(df)} ô)")
    print("  tổng:", {
        "pop_M": round(df["pop"].sum() / 1e6, 2),
        "pop_2025_M": round(df["pop_2025"].sum() / 1e6, 2),
        "n_poi": int(df.n_poi.sum()), "n_parking": int(df.n_parking.sum()),
        "n_fuel": int(df.n_fuel.sum()),
        "road_km": round(df.road_len_m.sum() / 1e3),
        "road_mt_km": round(df.road_len_mt_m.sum() / 1e3),
    })
    print("  phủ:", {c: f"{int(df[c].sum()):,} ({100 * df[c].mean():.1f}%)" for c in _FLAG_COLS})
    both = (df["pop"].fillna(0) > 0) & (df.road_len_m.fillna(0) > 0)
    print(f"  ô có cả dân & đường: {int(both.sum())} / {len(df)}")
    # E-DQ8 hai chiều — giờ đọc được vì "không phủ" đã tách khỏi "bằng 0".
    road_no_pop = df["osm_covered"] & (df.road_len_m > 0) & ~(df["pop"] > 0)
    pop_no_road = (df["pop"] > 0) & ~(df.road_len_m > 0)
    print(f"  E-DQ8: ô có đường mà pop(2020)=0/NaN: {int(road_no_pop.sum()):,} "
          f"({100 * road_no_pop.mean():.1f}%) | ô có dân mà không đường: {int(pop_no_road.sum()):,}")
    road_no_pop25 = df["osm_covered"] & (df.road_len_m > 0) & ~(df["pop_2025"] > 0)
    print(f"         cùng phép đo với pop_2025: {int(road_no_pop25.sum()):,} ({100 * road_no_pop25.mean():.1f}%)")
    return df


if __name__ == "__main__":
    run()
