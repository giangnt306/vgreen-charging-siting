#!/usr/bin/env python3
"""transform_canonical.py — master CSV (crawl-shape) -> canonical parquet 2 tang.

Bien doi `data/interim/stations_master_evcs.csv` (khoa `station_code`, hinh dang
crawl tho) thanh HAI bang canonical dung SCHEMA_CONTRACT muc 2/3:

  - `stations`   : 1 dong/tram (khoa `station_id` = `vn-<code>`), co `h3_r8`,
                   `operator`, tin hieu chat luong (`confidence`/`freshness`/
                   `quality_flags`), cot admin de trong (enrich o Step B).
  - `connectors` : tang 2 — no `evse_powers` thanh 1 dong/nhom cong suat
                   (FK `station_id`). Day la mo hinh `station -> connector`.

PHAM VI (Step A): du an chi nham vao O TO -> MAC DINH BO `BATTERY_SWAP`
(tram doi pin khong phai tram sac oto). Co the keo lai bang `--keep-bss`.

Output: Parquet Hive-partitioned theo `province_code`:
  data/interim/canonical/stations/province_code=<XX>/*.parquet
  data/interim/canonical/connectors/province_code=<XX>/*.parquet

Chay:
    PYTHONPATH=src python -m ev_siting.data.evcs.transform_canonical
    PYTHONPATH=src python -m ev_siting.data.evcs.transform_canonical --keep-bss
"""
import argparse
import json
import re
import shutil

import h3
import pandas as pd

from .paths import MASTER_CSV, STATIONS_DIR, CONNECTORS_DIR, CANONICAL_DIR, PROJECT_ROOT
from ..vinfast_official.paths import XREF_PARQUET

H3_RES = 8

# Cot provenance/doi chieu nguon chinh thuc (match_official.py), join theo station_code.
XREF_COLS = [
    "official_matched", "match_method", "official_store_id",
    "match_dist_m", "match_name_sim", "official_charging_status",
    "official_access_type", "provenance",
]
AC_MAX_W = 25000                       # <=25 kW = AC, >25 kW = DC (khop build_master_evcs)
VN_BBOX = (8.0, 23.6, 102.0, 110.0)    # lat_min, lat_max, lng_min, lng_max
# Cot admin chua co nguon ranh gioi (Step B) -> tao san de dung schema, dien sau.
ADMIN_COLS = ["admin_l1_code", "province_name", "commune_name", "commune_kind"]


def station_id(code: str) -> str:
    """`C.AC000001` -> `vn-c-ac000001`. On dinh, tra nguoc ve `station_code`."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(code).lower()).strip("-")
    return f"vn-{slug}"


def coord_ok(lat, lng) -> bool:
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    return VN_BBOX[0] <= lat <= VN_BBOX[1] and VN_BBOX[2] <= lng <= VN_BBOX[3]


def flags_to_list(flag: str) -> list:
    """`ALL_ZERO;SPARSE` -> ['ALL_ZERO','SPARSE']; NaN/'' -> []."""
    if not isinstance(flag, str) or not flag:
        return []
    return [f for f in flag.split(";") if f]


def types_to_list(conn_types: str) -> list:
    """`AC-11kW|DC-120kW` -> ['AC-11kW','DC-120kW']; NaN/'' -> []."""
    if not isinstance(conn_types, str) or not conn_types:
        return []
    return [t for t in conn_types.split("|") if t]


def explode_connectors(evse_powers_json, sid, code, prov):
    """`evse_powers` (JSON) -> list dong connector (tang 2).

    evsePowers = [{type:<W>, totalEvse:<so sung lap>, numberOfAvailableEvse:<trong>}].
    Moi nhom cong suat -> 1 connector. current_type suy tu nguong AC_MAX_W.
    """
    try:
        groups = json.loads(evse_powers_json) if isinstance(evse_powers_json, str) else []
    except (ValueError, TypeError):
        groups = []
    rows = []
    idx = 0
    for g in groups if isinstance(groups, list) else []:
        if not isinstance(g, dict):
            continue
        try:
            w = int(g.get("type") or 0)
            n_total = int(g.get("totalEvse") or 0)
            n_avail = int(g.get("numberOfAvailableEvse") or 0)
        except (ValueError, TypeError):
            continue
        if w <= 0 and n_total <= 0:
            continue
        idx += 1
        cur = "AC" if 0 < w <= AC_MAX_W else "DC"
        rows.append({
            "connector_id": f"{sid}-c{idx}",
            "station_id": sid,
            "station_code": code,
            "province_code": prov,
            "power_kw": round(w / 1000, 1) if w else None,
            "current_type": cur if w > 0 else None,
            "connector_label": f"{cur}-{w / 1000:g}kW" if w > 0 else None,
            "count_total": n_total,
            "count_available": n_avail,
        })
    return rows


def completeness(row) -> float:
    """Diem hoan chinh du lieu 0..1 (trung binh 4 chi bao, tai lieu hoa ro):
    toa do hop le | biet nguon cung (evse_powers) | co status | co telemetry.

    Day la thanh phan HOAN CHINH. `confidence` cuoi cung = tron completeness voi
    tin hieu XAC MINH nguon chinh thuc (match_official.py) — xem `redefine_confidence`.
    Dung lam fallback khi chua co official_xref.parquet."""
    ind = [
        coord_ok(row["lat"], row["lng"]),
        isinstance(row.get("evse_powers"), str) and row["evse_powers"] not in ("", "[]"),
        isinstance(row.get("status"), str) and bool(row["status"]),
        bool(row.get("has_timeseries")),
    ]
    return round(sum(ind) / len(ind), 3)


def join_xref(df: pd.DataFrame) -> pd.DataFrame:
    """Left-join provenance tu official_xref.parquet theo `station_code`.

    Neu chua co xref -> tra cot provenance rong (pipeline van chay doc lap)."""
    # bo cot cung ten tu master (verified/confidence tho) de xref lam chu.
    df = df.drop(columns=[c for c in ("verified", "confidence", *XREF_COLS)
                          if c in df.columns])
    if XREF_PARQUET.exists():
        xref = pd.read_parquet(XREF_PARQUET)
        keep = ["station_code", "confidence", "verified"] + XREF_COLS
        xref = xref[[c for c in keep if c in xref.columns]]
        df = df.merge(xref, on="station_code", how="left")
        df["_has_xref"] = df["official_matched"].notna()
    else:
        for c in ["confidence", "verified", *XREF_COLS]:
            df[c] = pd.NA
        df["_has_xref"] = False
    return df


def redefine_confidence(df: pd.DataFrame) -> pd.DataFrame:
    """`confidence`/`verified` = tu official_xref (da tron completeness + xac minh
    first-party). Fallback ve `completeness` cho tram khong co trong xref."""
    comp = df.apply(completeness, axis=1)
    has = df["_has_xref"].fillna(False)
    df["confidence"] = df["confidence"].where(has, comp).astype(float).round(3)
    df["verified"] = df["verified"].where(has, False).fillna(False).astype(bool)
    df["provenance"] = df["provenance"].where(has, "evcs.vn").fillna("evcs.vn")
    df["official_matched"] = df["official_matched"].fillna(False).astype(bool)
    df["match_method"] = df["match_method"].fillna("none")
    return df


def run(keep_bss: bool = False):
    if not MASTER_CSV.exists():
        raise SystemExit(f"thieu {MASTER_CSV} — chay build_master_evcs truoc")

    df = pd.read_csv(MASTER_CSV, low_memory=False)
    n_all = len(df)

    # --- PHAM VI: chi tram sac oto (bo BATTERY_SWAP tru khi --keep-bss) ---
    if not keep_bss:
        df = df[df["station_type"] != "BATTERY_SWAP"].copy()
    n_kept = len(df)

    # --- so gau du lieu ban dau ---
    df["station_id"] = df["station_code"].map(station_id)
    df["h3_r8"] = [
        h3.latlng_to_cell(la, ln, H3_RES) if coord_ok(la, ln) else None
        for la, ln in zip(df["lat"], df["lng"])
    ]
    # freshness = so ngay ke tu telemetry cuoi (moc "as-of" = end moi nhat toan tap).
    as_of = pd.to_numeric(df["ts_time_end_ms"], errors="coerce").max()
    end_ms = pd.to_numeric(df["ts_time_end_ms"], errors="coerce")
    df["freshness"] = ((as_of - end_ms) / 86_400_000).round(2)
    df["quality_flags"] = df["quality_flag"].map(flags_to_list)
    df["connector_types"] = df["connector_types"].map(types_to_list)
    df["operator"] = df["network"].fillna("")

    num_conn = pd.to_numeric(df["num_connectors"], errors="coerce").fillna(0).astype("int64")
    df["num_connectors"] = num_conn
    for c in ("max_power_kw", "total_power_kw"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["is_public"] = df["is_public"].map(
        {True: True, False: False, "True": True, "False": False})
    for c in ADMIN_COLS:
        df[c] = pd.NA                       # dien o Step B (enrich ranh gioi)

    # --- provenance/verified/confidence tu doi chieu nguon chinh thuc ---
    df = join_xref(df)
    df = redefine_confidence(df)

    stations_cols = [
        "station_id", "station_code", "lat", "lng", "h3_r8",
        "admin_l1_code", "province_name", "province_code", "commune_name", "commune_kind",
        "name", "address", "operator", "station_type",
        "current_type", "max_power_kw", "total_power_kw", "num_connectors", "connector_types",
        "status", "is_public", "verified", "has_timeseries",
        "confidence", "freshness", "quality_flags",
        # provenance / doi chieu nguon chinh thuc (vinfastauto.com)
        "provenance", "official_matched", "match_method", "official_store_id",
        "match_dist_m", "match_name_sim", "official_charging_status", "official_access_type",
    ]
    stations = df[stations_cols].reset_index(drop=True)

    # --- tang 2: no connectors ---
    conn_rows = []
    for _, r in df.iterrows():
        conn_rows.extend(
            explode_connectors(r["evse_powers"], r["station_id"], r["station_code"],
                               r["province_code"])
        )
    connectors = pd.DataFrame(conn_rows, columns=[
        "connector_id", "station_id", "station_code", "province_code",
        "power_kw", "current_type", "connector_label", "count_total", "count_available",
    ])

    # --- ghi Parquet Hive-partitioned theo province_code (ghi de sach) ---
    for d in (STATIONS_DIR, CONNECTORS_DIR):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    # province_code rong -> "NA" de khong vo partition.
    stations["province_code"] = stations["province_code"].fillna("").replace("", "NA")
    connectors["province_code"] = connectors["province_code"].fillna("").replace("", "NA")
    stations.to_parquet(STATIONS_DIR, partition_cols=["province_code"], index=False)
    connectors.to_parquet(CONNECTORS_DIR, partition_cols=["province_code"], index=False)

    # --- bao cao ---
    rel = lambda p: p.relative_to(PROJECT_ROOT)
    n_orphan = (~connectors["station_id"].isin(set(stations["station_id"]))).sum()
    print("================ TRANSFORM CANONICAL (Step A) ================")
    print(f"Master doc                : {n_all:,} tram")
    print(f"Giu lai (bo BSS={not keep_bss}) : {n_kept:,} tram")
    print(f"  theo station_type       : {df['station_type'].value_counts().to_dict()}")
    print(f"stations  -> {rel(STATIONS_DIR)}  ({len(stations):,} dong)")
    print(f"connectors-> {rel(CONNECTORS_DIR)}  ({len(connectors):,} dong)")
    print(f"  h3_r8 null (toa do xau) : {stations['h3_r8'].isna().sum():,}")
    print(f"  tram khong co connector : {(stations['num_connectors'] == 0).sum():,}")
    print(f"  connector orphan (FK)   : {n_orphan}")
    print(f"  confidence trung binh   : {stations['confidence'].mean():.3f}")
    print(f"  verified (first-party)  : {int(stations['verified'].sum()):,} / {len(stations):,}")
    print(f"  match_method            : {stations['match_method'].value_counts().to_dict()}")
    print(f"  provenance              : {stations['provenance'].value_counts().to_dict()}")
    print("Con lai (Step B): enrich admin_l1_code/province_name/commune_* tu ranh gioi.")
    print("=============================================================")
    return stations, connectors


def main():
    ap = argparse.ArgumentParser(description="master CSV -> canonical parquet (stations/connectors)")
    ap.add_argument("--keep-bss", action="store_true",
                    help="giu lai BATTERY_SWAP (mac dinh bo — du an chi nham oto)")
    args = ap.parse_args()
    run(keep_bss=args.keep_bss)


if __name__ == "__main__":
    main()
