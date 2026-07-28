#!/usr/bin/env python3
"""match_official.py — doi chieu evcs.vn <-> nguon CHINH THUC vinfastauto.com.

Nguon official (nha san xuat) la first-party -> dung lam CAN CU XAC MINH cho
master crawl tho evcs.vn (`stations_master_evcs.csv`). Module nay xay MATCHER
2 tang + phat sinh cot provenance/verified va DINH NGHIA LAI `confidence`.

TANG MATCH
  1. exact_code  : `station_code` (evcs) == `store_id` (official). Khoa dinh danh
                   dung chung 1 backend VinFast -> match manh nhat, toa do trung khop.
  2. spatial_fuzzy: cho phan con lai co toa do hop le -> BallTree(haversine) tim
                   tram official gan nhat trong ban kinh R, chap nhan neu ten
                   giong (rapidfuzz token_set_ratio) HOAC rat gan (< NEAR_M met).

PHAM VI XAC MINH
  Nguon official chi phu tram sac O TO VinFast. Mot tram evcs "duoc ky vong co
  trong official" (`expected_official`) khi thuoc mang VinFast + ma bat dau `C.`
  (tram sac oto). Tram NGOAI pham vi (doi pin `B.`, mang khac) khong bi tru diem
  vi vang mat khoi registry official khong phai bang chung tram gia.

OUTPUT
  official_xref.parquet : 1 dong / station_code evcs, gom cot provenance:
    official_matched, match_method, official_store_id, match_dist_m,
    match_name_sim, official_* (status/access/connector/admin...),
    expected_official, provenance, verified, confidence.
  official_xref_report.json : thong ke match.

Chay:
    PYTHONPATH=src python -m ev_siting.data.vinfast_official.match_official
    PYTHONPATH=src python -m ev_siting.data.vinfast_official.match_official --radius 300 --name-sim 80
"""
import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sklearn.neighbors import BallTree

from .paths import ADMIN_PARQUET, CONNECTORS_PARQUET, MASTER_CSV, STATIONS_PARQUET, XREF_PARQUET, XREF_REPORT

# --- tham so matcher (default hop ly, override qua CLI) ---
RADIUS_M = 250.0        # ban kinh tim official gan nhat cho tang spatial
NAME_SIM_MIN = 82.0     # nguong token_set_ratio de chap nhan spatial match
NEAR_M = 40.0           # < nguong nay: chap nhan bat ke ten (co-location chac chan)
VERIFY_DIST_M = 200.0   # exact_code + toa do lech <= nguong nay -> verified
EARTH_R = 6_371_000.0
VN_BBOX = (8.0, 23.6, 102.0, 110.0)   # lat_min, lat_max, lng_min, lng_max


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def strip_accents(s: str) -> str:
    """Bo dau tieng Viet + lowercase -> chuoi so sanh mo (khong phu thuoc unidecode)."""
    if not isinstance(s, str):
        return ""
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def coord_ok(lat, lng) -> bool:
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    return VN_BBOX[0] <= lat <= VN_BBOX[1] and VN_BBOX[2] <= lng <= VN_BBOX[3]


def haversine_m(lat1, lng1, lat2, lng2):
    """Khoang cach haversine (met), vector hoa."""
    p = np.radians
    dlat = p(lat2 - lat1); dlon = p(lng2 - lng1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p(lat1)) * np.cos(p(lat2)) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------------------
# load official (registry + connector rollup + admin)
# ---------------------------------------------------------------------------
def load_official():
    off = pd.read_parquet(STATIONS_PARQUET)
    off = off.drop_duplicates("store_id", keep="first").reset_index(drop=True)

    # rollup connector: dem AC/DC + cong suat max moi tram
    if CONNECTORS_PARQUET.exists():
        c = pd.read_parquet(CONNECTORS_PARQUET)
        c["is_dc"] = c["power_type"].astype(str).str.upper().str.startswith("DC")
        roll = c.groupby("store_id").agg(
            official_n_connectors=("connector_id", "size"),
            official_n_dc=("is_dc", "sum"),
            official_power_kw_max=("max_electric_power_kw", "max"),
        ).reset_index()
        roll["official_n_ac"] = roll["official_n_connectors"] - roll["official_n_dc"]
        off = off.merge(roll, on="store_id", how="left")

    if ADMIN_PARQUET.exists():
        a = pd.read_parquet(ADMIN_PARQUET)[
            ["store_id", "province", "district", "commune"]
        ].rename(columns={"province": "official_province",
                          "district": "official_district",
                          "commune": "official_commune"})
        off = off.merge(a, on="store_id", how="left")

    off["_name_norm"] = off["name"].map(strip_accents)
    return off


# ---------------------------------------------------------------------------
# matcher
# ---------------------------------------------------------------------------
def match(ev: pd.DataFrame, off: pd.DataFrame,
          radius_m=RADIUS_M, name_sim_min=NAME_SIM_MIN, near_m=NEAR_M):
    """Tra ve DataFrame 1 dong/station_code voi cot match/provenance."""
    off = off.copy()
    if "_name_norm" not in off.columns:
        off["_name_norm"] = off["name"].map(strip_accents)
    off_by_code = off.set_index("store_id")
    off_codes = set(off_by_code.index)

    # --- Tang 1: exact code ---
    ev = ev.copy()
    ev["station_code"] = ev["station_code"].astype(str)
    ev["_matched_code"] = ev["station_code"].where(ev["station_code"].isin(off_codes))

    # --- Tang 2: spatial_fuzzy cho phan chua match code + toa do hop le ---
    off_geo = off[off.apply(lambda r: coord_ok(r["lat"], r["lng"]), axis=1)].reset_index(drop=True)
    tree = (BallTree(np.radians(off_geo[["lat", "lng"]].to_numpy()), metric="haversine")
            if not off_geo.empty else None)
    rad = radius_m / EARTH_R

    ev["_name_norm"] = ev["name"].map(strip_accents)
    need_spatial = ev["_matched_code"].isna() & ev.apply(
        lambda r: coord_ok(r["lat"], r["lng"]), axis=1)

    spat_store = {}    # idx evcs -> store_id official
    spat_dist = {}
    if need_spatial.any() and tree is not None:
        q = ev.loc[need_spatial]
        qrad = np.radians(q[["lat", "lng"]].to_numpy())
        ind, dist = tree.query_radius(qrad, r=rad, return_distance=True, sort_results=True)
        for i, cand_idx, cand_dist in zip(q.index, ind, dist):
            best = None
            qname = ev.at[i, "_name_norm"]
            for j, d_rad in zip(cand_idx, cand_dist):
                d_m = d_rad * EARTH_R
                sim = fuzz.token_set_ratio(qname, off_geo.at[j, "_name_norm"]) if qname else 0
                if d_m <= near_m or sim >= name_sim_min:
                    best = (off_geo.at[j, "store_id"], d_m)
                    break
            if best:
                spat_store[i], spat_dist[i] = best

    # --- lap ket qua ---
    rows = []
    for i, r in ev.iterrows():
        code = r["station_code"]
        method = "none"; store = None; dist_m = np.nan
        if pd.notna(r["_matched_code"]):
            method, store = "exact_code", r["_matched_code"]
        elif i in spat_store:
            method, store = "spatial_fuzzy", spat_store[i]
            dist_m = spat_dist[i]

        o = off_by_code.loc[store] if store is not None else None
        # dist cho exact_code: tinh truc tiep tu toa do 2 nguon (neu ca hai hop le)
        if method == "exact_code" and o is not None and coord_ok(r["lat"], r["lng"]) \
                and coord_ok(o["lat"], o["lng"]):
            dist_m = float(haversine_m(np.float64(r["lat"]), np.float64(r["lng"]),
                                       np.float64(o["lat"]), np.float64(o["lng"])))
        name_sim = (float(fuzz.token_set_ratio(r["_name_norm"], o["_name_norm"]))
                    if o is not None else np.nan)

        # Exact code chua du toa do van la match identity, nhung KHONG duoc goi la
        # spatially verified. Tach method de consumer/coi review khong lam mo no.
        if method == "exact_code" and pd.isna(dist_m):
            method = "exact_code_no_coord"

        rows.append({
            "station_code": code,
            "official_matched": store is not None,
            "match_method": method,
            "official_store_id": store,
            "match_dist_m": round(dist_m, 1) if pd.notna(dist_m) else np.nan,
            "match_name_sim": round(name_sim, 1) if pd.notna(name_sim) else np.nan,
            "official_charging_status": o["charging_status"] if o is not None else None,
            "official_access_type": o["access_type"] if o is not None else None,
            "official_lat": float(o["lat"]) if o is not None and coord_ok(o["lat"], o["lng"]) else None,
            "official_lng": float(o["lng"]) if o is not None and coord_ok(o["lat"], o["lng"]) else None,
            "official_status": bool(o["status"]) if o is not None else None,
            "official_charging_publish": bool(o["charging_publish"]) if o is not None else None,
            "official_n_connectors": (int(o["official_n_connectors"])
                                      if o is not None and pd.notna(o.get("official_n_connectors"))
                                      else None),
            "official_n_ac": (int(o["official_n_ac"])
                              if o is not None and pd.notna(o.get("official_n_ac")) else None),
            "official_n_dc": (int(o["official_n_dc"])
                              if o is not None and pd.notna(o.get("official_n_dc")) else None),
            "official_power_kw_max": (float(o["official_power_kw_max"])
                                      if o is not None and pd.notna(o.get("official_power_kw_max"))
                                      else None),
            "official_province": o.get("official_province") if o is not None else None,
            "official_district": o.get("official_district") if o is not None else None,
            "official_commune": o.get("official_commune") if o is not None else None,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# provenance / verified / confidence
# ---------------------------------------------------------------------------
def _expected_official(ev_row) -> bool:
    """Tram co DUOC KY VONG nam trong registry official khong?
    -> mang VinFast + tram sac oto (station_type VINFAST_CS hoac ma `C.`)."""
    net = str(ev_row.get("network") or "")
    st = str(ev_row.get("station_type") or "")
    code = str(ev_row.get("station_code") or "")
    is_vinfast = "vin" in net.lower() or "vgreen" in net.lower()
    is_car = st == "VINFAST_CS" or code.startswith("C.")
    return is_vinfast and is_car


def _completeness(ev_row) -> float:
    """4 chi bao hoan chinh du lieu (giu dinh nghia cu tu transform_canonical)."""
    ind = [
        coord_ok(ev_row.get("lat"), ev_row.get("lng")),
        isinstance(ev_row.get("evse_powers"), str) and ev_row["evse_powers"] not in ("", "[]"),
        isinstance(ev_row.get("status"), str) and bool(ev_row.get("status")),
        bool(ev_row.get("has_timeseries")),
    ]
    return sum(ind) / len(ind)


def enrich(xref: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """Them expected_official, provenance, verified, confidence."""
    ev_ix = ev.set_index("station_code")
    x = xref.set_index("station_code").copy()

    expected, verified, provenance, confidence = [], [], [], []
    for code, r in x.iterrows():
        e = ev_ix.loc[code] if code in ev_ix.index else pd.Series(dtype=object)
        exp = _expected_official(e)
        comp = _completeness(e)
        method = r["match_method"]
        dist = r["match_dist_m"]
        sim = r["match_name_sim"]

        # --- verified: co corroboration first-party khong ---
        if method == "exact_code":
            v = pd.notna(dist) and dist <= VERIFY_DIST_M
        elif method == "exact_code_no_coord":
            v = False                                        # code-only, khong co corroboration toa do
        elif method == "spatial_fuzzy":
            v = pd.notna(sim) and sim >= NAME_SIM_MIN and pd.notna(dist) and dist <= RADIUS_M
        else:
            v = False

        # --- verification score (chi ap dung cho tram ky vong co trong official) ---
        if method == "exact_code":
            verif = 1.0 if v else 0.6
        elif method == "exact_code_no_coord":
            verif = 0.6
        elif method == "spatial_fuzzy":
            verif = 0.5 + 0.4 * (min(sim, 100) / 100) if pd.notna(sim) else 0.5
        else:
            verif = 0.0

        # --- confidence: tram ky vong -> tron completeness + verification;
        #     tram ngoai pham vi official -> chi completeness (khong bi tru) ---
        if exp:
            conf = 0.4 * comp + 0.6 * verif
        else:
            conf = comp

        expected.append(exp)
        verified.append(bool(v))
        provenance.append("vinfast_official+evcs.vn" if r["official_matched"] else "evcs.vn")
        confidence.append(round(conf, 3))

    x["expected_official"] = expected
    x["verified"] = verified
    x["provenance"] = provenance
    x["confidence"] = confidence
    return x.reset_index()


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------
def run(radius_m=RADIUS_M, name_sim_min=NAME_SIM_MIN, near_m=NEAR_M):
    if not MASTER_CSV.exists():
        raise SystemExit(f"thieu {MASTER_CSV} — chay build_master_evcs truoc")
    if not STATIONS_PARQUET.exists():
        raise SystemExit("thieu official_stations.parquet — chay `fetch_locators bulk` truoc")

    ev = pd.read_csv(MASTER_CSV, low_memory=False)
    off = load_official()
    print(f"[match] evcs={len(ev):,} tram | official={len(off):,} tram")

    xref = match(ev, off, radius_m, name_sim_min, near_m)
    xref = enrich(xref, ev)
    xref["matched_at"] = _now_iso()
    # Canonical gate so sanh hash nay voi master hien tai: xref cu khong duoc
    # silently tro thanh fallback sau mot lan crawl/build master moi.
    xref["source_master_sha256"] = _sha256(MASTER_CSV)

    XREF_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    xref.to_parquet(XREF_PARQUET, index=False)

    # --- report ---
    vc_method = xref["match_method"].value_counts().to_dict()
    exp = xref["expected_official"]
    report = {
        "matched_at": xref["matched_at"].iloc[0],
        "params": {"radius_m": radius_m, "name_sim_min": name_sim_min, "near_m": near_m,
                   "verify_dist_m": VERIFY_DIST_M},
        "n_evcs": int(len(ev)),
        "n_official": int(len(off)),
        "match_method": {k: int(v) for k, v in vc_method.items()},
        "n_matched": int(xref["official_matched"].sum()),
        "n_verified": int(xref["verified"].sum()),
        "n_expected_official": int(exp.sum()),
        "expected_but_unmatched": int((exp & ~xref["official_matched"]).sum()),
        "confidence_mean": round(float(xref["confidence"].mean()), 3),
        "confidence_mean_expected": round(float(xref.loc[exp, "confidence"].mean()), 3) if exp.any() else None,
        "official_only_not_in_evcs": int(len(set(off["store_id"]) - set(ev["station_code"].astype(str)))),
    }
    XREF_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("================ MATCH OFFICIAL (evcs.vn <-> vinfastauto) ================")
    print(f"  match_method            : {vc_method}")
    print(f"  matched / verified      : {report['n_matched']:,} / {report['n_verified']:,}")
    print(f"  expected_official       : {report['n_expected_official']:,}  "
          f"(unmatched: {report['expected_but_unmatched']:,})")
    print(f"  confidence mean (all)   : {report['confidence_mean']}")
    print(f"  confidence mean (exp.)  : {report['confidence_mean_expected']}")
    print(f"  official-only (khong o evcs): {report['official_only_not_in_evcs']:,}")
    print(f"-> {XREF_PARQUET.name} | {XREF_REPORT.name}")
    print("=========================================================================")
    return xref


def main():
    ap = argparse.ArgumentParser(description="doi chieu evcs.vn <-> nguon chinh thuc vinfastauto.com")
    ap.add_argument("--radius", type=float, default=RADIUS_M, help="ban kinh spatial (met)")
    ap.add_argument("--name-sim", type=float, default=NAME_SIM_MIN, help="nguong ten (0..100)")
    ap.add_argument("--near", type=float, default=NEAR_M, help="nguong 'rat gan' bo qua ten (met)")
    args = ap.parse_args()
    run(radius_m=args.radius, name_sim_min=args.name_sim, near_m=args.near)


if __name__ == "__main__":
    main()
