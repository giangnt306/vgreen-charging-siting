#!/usr/bin/env python3
"""dedup_crosssource.py — E-DQ2: giai quyet TRUNG CHEO NGUON (evcs vs official).

Cung mot tram sac VAT LY co the xuat hien >1 dong trong canonical vi (a) evcs.vn
gom tu nhieu tab/nguon voi ma khac nhau, va (b) evcs <-> registry official chua duoc
hop nhat ve dinh danh vat ly. Day KHAC voi P6 (trung PK noi bo evcs, cung station_code)
va KHAC voi E-DQ1 (toa do placeholder). E-DQ2 = hop nhat cac dong la CUNG 1 tram vat ly.

KHONG dedup bang H3 don thuan: o res 8 ~0,83 km2 -> mot mall/san bay co the chua nhieu
tram that. Dong-o != trung. Phai dua vao KHOANG CACH + DINH DANH, khong phai o luoi.

BA TANG (giam dan do chac chan):
  T1 official_store : >1 dong evcs cung tro ve mot `official_store_id`
                      (mot exact_code + cac spatial_fuzzy roi vao cung store) ->
                      trung KHONG CAN NGUONG (dinh danh first-party trung khop).
  T2 coord_name     : con lai, cap tram cach nhau < NEAR_M met VA ten giong
                      (>=NAME_SIM_MIN). Ten BAT BUOC: cung 1 tram vat ly o 2 feed
                      thi TEN trung; toa do trung ma ten khac = tram khac nhau
                      dung chung toa do placeholder (E-DQ1), KHONG phai trung.
  GUARD blob        : cac tram noi nhau qua canh < NEAR_M tao "blob"; blob >=
                      PLACEHOLDER_STACK_MIN thanh vien = cum toa do dang ngo
                      (vd chuoi "Tư nhân" toa do ramp tang deu, hoac stack trung
                      khit) -> KHONG merge trong blob, gan co DUP_COORD_SUSPECT
                      va de E-DQ1 phan xu. Tranh chaining bac cau thanh blob khong lo.

CHINH SACH (nhat quan voi P6/P8): FLAG, khong xoa dong; KHONG cong cong suat giua
cac ban trung. Moi nhom chon 1 SURVIVOR (is_primary=True); cac ban con lai
is_primary=False + co CROSS_SOURCE_DUP. `physical_id` = station_id cua survivor.
Cung (supply) / coverage / T0 anchor chi dung `is_primary` (giong `is_operational` P8).
Doi soat: n_input = n_primary + n_duplicate.

Chay doc lap (eyeball nhom truoc khi tin): doc canonical/stations, in report + dump
nhom trung ra CSV; KHONG ghi de canonical (viec do o transform_canonical).
    PYTHONPATH=src python -m ev_siting.data.evcs.dedup_crosssource
"""
import argparse
import json

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sklearn.neighbors import BallTree

from ..vinfast_official.match_official import EARTH_R, strip_accents
from .paths import INTERIM_DIR, PROJECT_ROOT, STATIONS_DIR

# --- tham so (default hop ly, khop match_official de nhat quan nguong) ---
NEAR_M = 50.0               # ban kinh coi la CO THE cung 1 diem vat ly
NAME_SIM_MIN = 82.0         # nguong token_set_ratio de xac nhan trung (khop matcher)
PLACEHOLDER_STACK_MIN = 5   # blob proximity >= n thanh vien => cum ngo (E-DQ1), khong merge
VN_BBOX = (8.0, 23.6, 102.0, 110.0)

DUP_FLAG = "CROSS_SOURCE_DUP"
SUSPECT_FLAG = "DUP_COORD_SUSPECT"

# cot canonical E-DQ2 them vao `stations`
DUP_COLS = ["physical_id", "is_primary", "dup_group_id",
            "dup_method", "dup_dist_m", "n_dup_members"]


def _coord_ok(lat, lng) -> bool:
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    return VN_BBOX[0] <= lat <= VN_BBOX[1] and VN_BBOX[2] <= lng <= VN_BBOX[3]


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    p = np.radians
    dlat = p(lat2 - lat1); dlon = p(lng2 - lng1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p(lat1)) * np.cos(p(lat2)) * np.sin(dlon / 2) ** 2
    return float(2 * EARTH_R * np.arcsin(np.sqrt(a)))


class _UnionFind:
    def __init__(self, keys):
        self.parent = {k: k for k in keys}

    def find(self, x):
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:      # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _pick_survivor(group: pd.DataFrame) -> str:
    """Chon dong CHINH cho mot nhom trung. Uu tien dinh danh first-party manh nhat:
    exact_code > official_matched > confidence cao > co telemetry > station_id nho
    (tat dinh)."""
    g = group.copy()
    g["_exact"] = (g["match_method"] == "exact_code").astype(int)
    g["_matched"] = g["official_matched"].fillna(False).astype(int)
    g["_conf"] = pd.to_numeric(g["confidence"], errors="coerce").fillna(0.0)
    g["_ts"] = g["has_timeseries"].fillna(False).astype(int)
    g = g.sort_values(["_exact", "_matched", "_conf", "_ts", "station_id"],
                      ascending=[False, False, False, False, True])
    return g.iloc[0]["station_id"]


def assign_physical_id(stations: pd.DataFrame) -> pd.DataFrame:
    """Gan `physical_id`/`is_primary`/`dup_*` + co CROSS_SOURCE_DUP / DUP_COORD_PLACEHOLDER.

    Yeu cau cot: station_id, station_code, lat, lng, name, official_store_id,
    match_method, official_matched, confidence, has_timeseries, quality_flags.
    Tra ve BAN SAO co them DUP_COLS + cap nhat quality_flags. KHONG xoa dong."""
    df = stations.copy().reset_index(drop=True)
    ids = df["station_id"].tolist()
    uf = _UnionFind(ids)
    method_of = {}          # station_id -> ly do bi keo vao nhom (uu tien official_store)

    name_norm = df["name"].map(strip_accents)
    good = df.apply(lambda r: _coord_ok(r["lat"], r["lng"]), axis=1)

    # --- T1: cung official_store_id -> union khong can nguong ---
    has_store = df["official_store_id"].notna() & (df["official_store_id"].astype(str) != "")
    for store, idx in df[has_store].groupby("official_store_id").groups.items():
        idx = list(idx)
        if len(idx) < 2:
            continue
        anchor = df.at[idx[0], "station_id"]
        for i in idx:
            uf.union(df.at[i, "station_id"], anchor)
            method_of[df.at[i, "station_id"]] = "official_store"

    # --- T2 (coord + name), co GUARD blob de tranh chaining qua cum toa do ngo ---
    suspect = pd.Series(False, index=df.index)
    t2 = df[good]
    if len(t2) > 1:
        pos = t2.index.to_numpy()
        coords = np.radians(t2[["lat", "lng"]].to_numpy(dtype=float))
        tree = BallTree(coords, metric="haversine")
        neigh = tree.query_radius(coords, r=NEAR_M / EARTH_R)

        # (i) blob = component noi nhau qua canh < NEAR_M (BAT KE ten) -> do dam dac
        prox = _UnionFind(list(pos))
        pairs = []                            # (i, j, dist_m) cac cap < NEAR_M
        for a_local, others in enumerate(neigh):
            i = pos[a_local]
            for b_local in others:
                if b_local <= a_local:
                    continue                  # moi cap 1 lan
                j = pos[b_local]
                d_m = _haversine_m(df.at[i, "lat"], df.at[i, "lng"],
                                   df.at[j, "lat"], df.at[j, "lng"])
                if d_m <= NEAR_M:
                    prox.union(i, j)
                    pairs.append((i, j, d_m))
        blob_size = pd.Series([prox.find(i) for i in pos], index=pos).value_counts()

        # (ii) blob dam dac (>= PLACEHOLDER_STACK_MIN) = cum ngo -> flag, KHONG merge
        for i in pos:
            if blob_size.get(prox.find(i), 1) >= PLACEHOLDER_STACK_MIN:
                suspect.loc[i] = True

        # (iii) merge coord_name CHI trong blob nho + ten trung (khong bac cau qua cum ngo)
        for i, j, d_m in pairs:
            if suspect.loc[i] or suspect.loc[j]:
                continue
            sim = fuzz.token_set_ratio(name_norm[i], name_norm[j]) \
                if name_norm[i] and name_norm[j] else 0
            if sim >= NAME_SIM_MIN:
                uf.union(df.at[i, "station_id"], df.at[j, "station_id"])
                for k in (i, j):
                    method_of.setdefault(df.at[k, "station_id"], "coord_name")

    # --- gom component -> physical_id / survivor / co ---
    df["_root"] = df["station_id"].map(uf.find)
    survivor_of, size_of = {}, {}
    for root, grp in df.groupby("_root"):
        size_of[root] = len(grp)
        survivor_of[root] = grp.iloc[0]["station_id"] if len(grp) == 1 \
            else _pick_survivor(grp)

    coord_lut = df.set_index("station_id")[["lat", "lng"]].to_dict("index")

    physical_id, is_primary, group_id = [], [], []
    dup_method, dup_dist, n_members = [], [], []
    new_flags = []
    for _, r in df.iterrows():
        root = r["_root"]
        surv = survivor_of[root]
        size = size_of[root]
        is_prim = (r["station_id"] == surv)
        physical_id.append(surv)
        is_primary.append(bool(is_prim))
        group_id.append(surv if size > 1 else None)
        n_members.append(int(size))
        dup_method.append(method_of.get(r["station_id"]) if size > 1 else None)

        fl = list(r["quality_flags"]) if isinstance(r["quality_flags"], (list, np.ndarray)) else []
        if suspect.loc[r.name] and SUSPECT_FLAG not in fl:
            fl.append(SUSPECT_FLAG)
        d = np.nan
        if size > 1 and not is_prim:
            if DUP_FLAG not in fl:
                fl.append(DUP_FLAG)
            s = coord_lut[surv]
            if _coord_ok(r["lat"], r["lng"]) and _coord_ok(s["lat"], s["lng"]):
                d = round(_haversine_m(r["lat"], r["lng"], s["lat"], s["lng"]), 1)
        dup_dist.append(d)
        new_flags.append(fl)

    df["physical_id"] = physical_id
    df["is_primary"] = is_primary
    df["dup_group_id"] = group_id
    df["dup_method"] = dup_method
    df["dup_dist_m"] = dup_dist
    df["n_dup_members"] = n_members
    df["quality_flags"] = new_flags
    return df.drop(columns=["_root"])


def dedup_report(df: pd.DataFrame) -> dict:
    """Thong ke + 5 cong QA (dong E-DQ2 THAT, khong chi 'co cot dup')."""
    n = len(df)
    dup = df[~df["is_primary"]]
    groups = df[df["dup_group_id"].notna()]
    n_groups = groups["dup_group_id"].nunique()
    prim = df[df["is_primary"]]

    # --- cong QA ---
    gates = {}
    # (1) doi soat: input = primary + duplicate
    gates["reconcile"] = bool(n == len(prim) + len(dup))
    # (2) physical_id unique giua cac primary
    gates["physical_id_unique"] = bool(prim["physical_id"].is_unique)
    # (3) khong over-merge: nhom coord_name phai NHO (< PLACEHOLDER_STACK_MIN) -> chung
    #     minh blob dam dac da bi chan, khong chaining bac cau thanh cum khong lo
    cn_groups = df[(df["dup_method"] == "coord_name") & df["dup_group_id"].notna()]
    max_cn = cn_groups.groupby("dup_group_id").size().max() if len(cn_groups) else 0
    gates["no_over_merge"] = bool(max_cn < PLACEHOLDER_STACK_MIN)
    # (4) moi primary la physical_id cua chinh no
    gates["primary_is_self"] = bool((prim["physical_id"] == prim["station_id"]).all())
    # (5) moi dup co dup_group_id + co CROSS_SOURCE_DUP
    has_grp = dup["dup_group_id"].notna().all() if len(dup) else True
    has_flag = dup["quality_flags"].apply(lambda l: DUP_FLAG in l).all() if len(dup) else True
    gates["dup_labeled"] = bool(has_grp and has_flag)

    suspect = df["quality_flags"].apply(lambda l: SUSPECT_FLAG in l)
    return {
        "n_input_carsonly": int(n),
        "n_primary": int(len(prim)),
        "n_duplicate": int(len(dup)),
        "n_dup_groups": int(n_groups),
        "dup_by_method": dup["dup_method"].value_counts().to_dict(),
        "largest_group": int(df["n_dup_members"].max()) if n else 0,
        "n_suspect_coord_deferred_edq1": int(suspect.sum()),
        "gates": gates,
        "all_gates_pass": bool(all(gates.values())),
    }


def _load_canonical_stations() -> pd.DataFrame:
    cols = ["station_id", "station_code", "lat", "lng", "name", "official_store_id",
            "match_method", "official_matched", "confidence", "has_timeseries",
            "quality_flags"]
    df = pd.read_parquet(STATIONS_DIR, columns=[c for c in cols])
    return df


def main():
    ap = argparse.ArgumentParser(
        description="E-DQ2: dedup cheo nguon evcs<->official (inspect canonical, khong ghi de)")
    ap.add_argument("--dump", action="store_true",
                    help="dump cac nhom trung ra CSV de eyeball")
    args = ap.parse_args()

    df = _load_canonical_stations()
    if "has_timeseries" not in df.columns:
        df["has_timeseries"] = False
    out = assign_physical_id(df)
    rep = dedup_report(out)

    report_path = INTERIM_DIR / "crosssource_dedup_report.json"
    report_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print("================ E-DQ2 DEDUP CHEO NGUON (evcs <-> official) ================")
    print(f"  input car-only          : {rep['n_input_carsonly']:,}")
    print(f"  primary (supply that)   : {rep['n_primary']:,}")
    print(f"  duplicate (flag, giu)   : {rep['n_duplicate']:,}  {rep['dup_by_method']}")
    print(f"  so nhom trung           : {rep['n_dup_groups']:,} (max {rep['largest_group']}/nhom)")
    print(f"  cum ngo -> E-DQ1        : {rep['n_suspect_coord_deferred_edq1']:,}")
    print(f"  QA gates                : {rep['gates']}")
    print(f"  ALL GATES PASS          : {rep['all_gates_pass']}")
    if args.dump:
        groups = out[out["dup_group_id"].notna()].sort_values(
            ["dup_group_id", "is_primary"], ascending=[True, False])
        csv_path = INTERIM_DIR / "crosssource_dedup_groups.csv"
        groups[["dup_group_id", "physical_id", "station_id", "station_code",
                "is_primary", "dup_method", "dup_dist_m", "name", "lat", "lng"]
               ].to_csv(csv_path, index=False)
        print(f"  nhom trung -> {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"-> {report_path.relative_to(PROJECT_ROOT)}")
    print("===========================================================================")
    return out, rep


if __name__ == "__main__":
    main()
