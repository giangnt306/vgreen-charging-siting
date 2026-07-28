#!/usr/bin/env python3
"""fix_coords.py — E-DQ1: TOA DO PLACEHOLDER / TRUNG KHIT.

Toa do khong THIEU (0 null / 0 zero / 0 ngoai bbox VN) — chung deu "hop le ve hinh
thuc" — nhung nhieu tram vat ly KHAC nhau bi don ve MOT diem mac dinh (placeholder).
Vd: 35 tram "Tu nhan" dia chi Ha Noi / Bac Ninh / Hung Yen nhung toa do = 1 diem HCM
(10.773106, 106.694794); ca registry official cung ghi dung diem placeholder do (111
store, 100% ma prefix HNO). => "snap ve official" (official-first nhu P7/P8) KHONG cuu
duoc E-DQ1 vi official SAI o dung truong nay. Nhung `province_code` (rut tu prefix ma
`C.HNO...` -> HNO, DOC LAP voi toa do) LAI la ground-truth tinh dang tin.

`lat`/`lng` la khoa join cua MOI buoc ha nguon (h3_r8, coverage/gap, anchor T0, demand
proxy). Toa do placeholder => cung ao o HCM + gap gia o Ha Noi => MCLP khuyen nghi SAI
cho. Day la poisoning ham muc tieu, khong phai loi cosmetic.

BA CHE DO LOI (mo giong P5/E-DQ2):
  1a placeholder xep chong : nhieu physical_id KHAC nhau don ve 1 diem exact
  1b lech toa do<->dia chi  : toa do roi sai vung so voi tinh (province_code / centroid)
  1c chuoi ramp/tong hop    : toa do gia tang deu -> E-DQ2 da co lap san (DUP_COORD_SUSPECT)

HAI DETECTOR — KHAC NHAU VE MUC DO CHAC CHAN "TOA DO la truong SAI":

  A COORD_PLACEHOLDER (chac chan toa do SAI -> LOAI khoi cung):
      nhom exact-coord co >= STACK_MIN physical_id KHAC nhau VA diem chung do cach
      centroid-tinh cua chinh cac thanh vien > MISMATCH_KM (union DUP_COORD_SUSPECT E-DQ2).
      Ket hop 2 dieu kien la CHU DICH: 1 venue that (mall/san bay) cung don nhieu tram ve
      1 diem POI NHUNG diem do GAN tinh cua no -> KHONG flag (giu). Chi khi >=STACK_MIN
      tram vat ly khac nhau don ve 1 diem XA tinh cua chung thi toa do moi la placeholder
      (nhieu tram khong the cung ngau nhien sai province_code giong het -> diem chung la
      artifact). Da kiem: 35 tram ma HNO don ve 1 diem HCM bi bat; 10 tram thuc o Hai
      Phong (gan tinh) duoc GIU.

  B COORD_ADDR_MISMATCH (KHONG ro truong nao sai -> CO ADVISORY, KHONG loai):
      toa do <-> province_code lech (Voronoi: centroid gan nhat la tinh KHAC, margin >
      MARGIN_KM). Da kiem tren 324 ca lech >300km: dia chi khop TOA DO 92 lan (province_code
      prefix moi la loi) vs khop PROVINCE_CODE 113 lan (toa do moi la loi) -> ~50/50, KHONG
      the tu quyet truong nao sai. Nen: gan co de audit + GIU toa do & h3_r8 & GIU trong
      cung; TRONG TAI la E-DQ3 (spatial-join admin polygon = point-in-polygon tren toa do).
      Nhat quan cach E-DQ2 hoan DUP_COORD_SUSPECT sang E-DQ1.

CAY GROUND-TRUTH TOA DO (FLAG khong xoa, nhat quan P6/P8/E-DQ2) — chi DETECTOR A dieu khien:
  1. tin toa do goc  : KHONG placeholder -> coord_src='evcs', resolved=True
  2. snap official   : placeholder NHUNG official co toa do TOT (khong placeholder, gan
                       centroid-tinh) va DOI diem -> snap, coord_src='official'. (Da kiem:
                       official VN mang DUNG diem placeholder do nen tier nay hau nhu khong
                       kich hoat — giu de dung nguyen tac official-first & phong ho tuong lai.)
  3. unresolved      : placeholder, khong co toa do tot -> resolved=False,
                       coord_src='placeholder', h3_r8=NULL (khong the neo phu o vi tri chua
                       biet — giong is_operational=False/is_primary=False). Giu lat_raw/lng_raw
                       de DAO NGUOC & geocode tuong lai (E-DQ3 commune polygon / roadmap).

Cot E-DQ1 them vao `stations`: lat_raw, lng_raw, coord_src, coord_fix_dist_m,
coord_resolved. `h3_r8` duoc TINH LAI tu toa do da resolve (NULL neu unresolved).
Cung/coverage/T0 chi dung `coord_resolved` (them dieu kien nhu is_primary/is_operational).

Chay doc lap (eyeball truoc khi tin): doc canonical/stations, in report + dump cac cum
placeholder ra CSV; KHONG ghi de canonical (viec do o transform_canonical).
    PYTHONPATH=src python -m ev_siting.data.evcs.fix_coords --dump
"""
import argparse
import json

import h3
import numpy as np
import pandas as pd

from ..vinfast_official.match_official import EARTH_R
from .paths import STATIONS_DIR, INTERIM_DIR, PROJECT_ROOT

# --- tham so ---
STACK_MIN = 5          # nhom exact-coord >= n physical_id khac nhau => nghi placeholder (khop E-DQ2 PLACEHOLDER_STACK_MIN)
MISMATCH_KM = 100.0    # toa do cach centroid tinh cua no > nguong => lech dia chi
MARGIN_KM = 75.0       # detector B: centroid gan nhat phai gan hon centroid-tinh-goc it nhat ngan nay (chong FP tinh lon)
MIN_PROV_N = 20        # tinh phai co >= n tram thi centroid median moi dang tin
H3_RES = 8
VN_BBOX = (8.0, 23.6, 102.0, 110.0)
SUSPECT_FLAG = "DUP_COORD_SUSPECT"   # E-DQ2 chuyen sang (blob ramp/stack)

PLACEHOLDER_FLAG = "COORD_PLACEHOLDER"
MISMATCH_FLAG = "COORD_ADDR_MISMATCH"

# cot canonical E-DQ1 them vao `stations`
FIX_COLS = ["lat_raw", "lng_raw", "coord_src", "coord_fix_dist_m", "coord_resolved"]

OFFICIAL_PARQUET = INTERIM_DIR / "vinfast_official" / "official_stations.parquet"


def _coord_ok(lat, lng) -> bool:
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    if np.isnan(lat) or np.isnan(lng):
        return False
    return VN_BBOX[0] <= lat <= VN_BBOX[1] and VN_BBOX[2] <= lng <= VN_BBOX[3]


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    p = np.radians
    dlat = p(lat2 - lat1); dlon = p(lng2 - lng1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p(lat1)) * np.cos(p(lat2)) * np.sin(dlon / 2) ** 2
    return float(2 * (EARTH_R / 1000.0) * np.arcsin(np.sqrt(a)))


def province_centroids(df: pd.DataFrame, min_n: int = MIN_PROV_N) -> dict:
    """Centroid MEDIAN moi province_code (doc lap toa do — province_code rut tu ma).

    Median robust voi placeholder THIEU SO trong tinh: 111 store HNO don ve HCM van
    khong keo median HNO ra khoi Ha Noi vi hang nghin tram HNO that ap dao. Chi tin
    tinh co >= min_n tram (tranh centroid do tren mau qua nho)."""
    good = df[df.apply(lambda r: _coord_ok(r["lat"], r["lng"]), axis=1)]
    cen = {}
    for prov, g in good.groupby("province_code", observed=True):
        if not prov or prov == "NA" or len(g) < min_n:
            continue
        cen[prov] = (float(g["lat"].median()), float(g["lng"].median()))
    return cen


def _official_placeholder_points(min_stack: int = STACK_MIN):
    """(lut store_id->(lat,lng), set diem placeholder official). Diem official bi >=
    min_stack store don ve => chinh no la placeholder => KHONG dung de snap."""
    if not OFFICIAL_PARQUET.exists():
        return {}, set()
    off = pd.read_parquet(OFFICIAL_PARQUET, columns=["store_id", "lat", "lng"])
    lut = {r.store_id: (r.lat, r.lng) for r in off.itertuples()}
    stack = off.groupby([off.lat.round(6), off.lng.round(6)]).size()
    ph = {pt for pt, n in stack.items() if n >= min_stack}
    return lut, ph


def resolve_coords(stations: pd.DataFrame) -> pd.DataFrame:
    """Gan lat_raw/lng_raw/coord_src/coord_fix_dist_m/coord_resolved + co
    COORD_PLACEHOLDER/COORD_ADDR_MISMATCH + TINH LAI h3_r8. KHONG xoa dong.

    Yeu cau cot: station_id, lat, lng, h3_r8, province_code, physical_id, quality_flags,
    official_store_id."""
    df = stations.copy().reset_index(drop=True)
    df["lat_raw"] = df["lat"]
    df["lng_raw"] = df["lng"]

    cen = province_centroids(df)
    provs = list(cen)
    cen_arr = np.array([cen[p] for p in provs]) if provs else np.empty((0, 2))

    def _dist_own(r):
        """Khoang cach toa do -> centroid province_code cua chinh no (NaN neu khong tra cuu duoc)."""
        c = cen.get(r["province_code"])
        if c is None or not _coord_ok(r["lat"], r["lng"]):
            return np.nan
        return _haversine_km(r["lat"], r["lng"], c[0], c[1])

    def _nearest(r):
        """(tinh centroid gan nhat, khoang cach) — Voronoi de xac dinh toa do 'thuoc' tinh nao."""
        if not len(provs) or not _coord_ok(r["lat"], r["lng"]):
            return None, np.nan
        d = np.array([_haversine_km(r["lat"], r["lng"], c[0], c[1]) for c in cen_arr])
        j = int(d.argmin())
        return provs[j], float(d[j])

    d_own = df.apply(_dist_own, axis=1)
    valid = df.apply(lambda r: _coord_ok(r["lat"], r["lng"]), axis=1)
    is_far = valid & (d_own > MISMATCH_KM)   # toa do xa tinh cua no (co the do toa do HOAC province_code sai)

    # === DETECTOR A: placeholder (chac chan toa do SAI): stack >= STACK_MIN VA xa tinh ===
    # Ket hop 2 dieu kien: venue that (nhieu tram cung 1 POI) GAN tinh -> khong flag;
    # chi diem chung XA tinh cua >= STACK_MIN tram vat ly moi la artifact placeholder.
    key = df["lat"].round(6).astype(str) + "," + df["lng"].round(6).astype(str)
    n_phys = df.groupby(key)["physical_id"].transform("nunique")   # so tram VAT LY khac nhau don ve diem
    suspect = df["quality_flags"].apply(
        lambda l: SUSPECT_FLAG in l if isinstance(l, (list, np.ndarray)) else False)
    is_placeholder = (valid & (n_phys >= STACK_MIN) & is_far) \
        | (suspect & valid & (n_phys >= 2) & is_far)

    # === DETECTOR B: lech toa do<->province (ADVISORY, khong loai): Voronoi + margin ===
    # Centroid gan nhat la tinh KHAC & gan hon centroid-goc >= MARGIN_KM (chong FP tinh lon).
    # KHONG the tu quyet toa do hay province_code sai -> chi gan co, de E-DQ3 trong tai.
    near_prov, d_near = zip(*df.apply(_nearest, axis=1)) if len(df) else ((), ())
    near_prov = pd.Series(near_prov, index=df.index)
    d_near = pd.Series(d_near, index=df.index)
    is_mismatch = is_far & (near_prov != df["province_code"]) \
        & ((d_own - d_near) > MARGIN_KM) & ~is_placeholder

    # === RESOLVER: chi DETECTOR A dieu khien resolved; B chi la co advisory ===
    off_lut, off_ph = _official_placeholder_points()
    coord_src, resolved, fix_dist = [], [], []
    new_lat, new_lng, new_flags = [], [], []
    for i, r in df.iterrows():
        lat, lng = r["lat"], r["lng"]
        fl = list(r["quality_flags"]) if isinstance(r["quality_flags"], (list, np.ndarray)) else []
        if is_placeholder[i] and PLACEHOLDER_FLAG not in fl:
            fl.append(PLACEHOLDER_FLAG)
        if is_mismatch[i] and MISMATCH_FLAG not in fl:
            fl.append(MISMATCH_FLAG)

        if not is_placeholder[i]:
            # (1) tin toa do goc (ke ca khi CO co advisory B — giu toa do & h3, trong tai o E-DQ3)
            src, res, d = "evcs", _coord_ok(lat, lng), 0.0
        else:
            # (2) thu snap official (chi khi official co toa do TOT — khong placeholder,
            #     gan centroid tinh — va DOI diem)
            snapped = False
            oc = off_lut.get(r.get("official_store_id"))
            if oc is not None and _coord_ok(oc[0], oc[1]):
                opt = (round(oc[0], 6), round(oc[1], 6))
                cprov = cen.get(r["province_code"])
                off_near_prov = cprov is not None and _haversine_km(oc[0], oc[1], cprov[0], cprov[1]) <= MISMATCH_KM
                if opt not in off_ph and off_near_prov and _coord_ok(lat, lng) \
                        and _haversine_km(lat, lng, oc[0], oc[1]) > 0.05:
                    lat, lng = float(oc[0]), float(oc[1])
                    src, res, d = "official", True, round(_haversine_km(r["lat"], r["lng"], lat, lng) * 1000, 1)
                    snapped = True
            if not snapped:
                # (3) unresolved — giu toa do goc de dao nguoc, nhung LOAI khoi cung
                src, res, d = "placeholder", False, np.nan
        coord_src.append(src)
        resolved.append(bool(res))
        fix_dist.append(d)
        new_lat.append(lat)
        new_lng.append(lng)
        new_flags.append(fl)

    df["lat"] = new_lat
    df["lng"] = new_lng
    df["coord_src"] = coord_src
    df["coord_resolved"] = resolved
    df["coord_fix_dist_m"] = fix_dist
    df["quality_flags"] = new_flags

    # === TINH LAI h3_r8 tu toa do da resolve (NULL neu unresolved / toa do xau) ===
    df["h3_r8"] = [
        h3.latlng_to_cell(la, ln, H3_RES) if (res and _coord_ok(la, ln)) else None
        for la, ln, res in zip(df["lat"], df["lng"], df["coord_resolved"])
    ]
    return df


def fix_report(df: pd.DataFrame) -> dict:
    """Thong ke + 5 cong QA (dong E-DQ1 THAT, khong chi 'co cot lat_raw')."""
    n = len(df)
    ph = df["quality_flags"].apply(lambda l: PLACEHOLDER_FLAG in l)
    mm = df["quality_flags"].apply(lambda l: MISMATCH_FLAG in l)
    unresolved = ~df["coord_resolved"]

    gates = {}
    # (1) provenance day du: coord_src + lat_raw/lng_raw giu nguyen moi dong (flag khong xoa;
    #     doi soat input==output kiem o transform_canonical)
    gates["provenance_complete"] = bool(
        df["coord_src"].notna().all()
        and df["lat_raw"].notna().all() and df["lng_raw"].notna().all())
    # (2) unresolved => h3_r8 NULL (khong the neo phu o vi tri chua biet)
    gates["unresolved_no_h3"] = bool((df.loc[unresolved, "h3_r8"].isna()).all())
    # (3) KHONG con placeholder chua sua trong tap TIN CAY: PLACEHOLDER_FLAG & resolved
    #     chi hop le khi da SNAP official (toa do tot). Con lai phai unresolved (loai cung).
    bad_ph = df["coord_resolved"] & ph & (df["coord_src"] != "official")
    gates["no_unfixed_placeholder_in_supply"] = bool(bad_ph.sum() == 0)
    # (4) detector A da xu ly (placeholder -> coord_src in {placeholder, official}); B chi advisory
    #     nen mismatch VAN giu coord_src='evcs' (khong loai) — dung theo thiet ke.
    gates["placeholder_labeled"] = bool(
        df.loc[ph, "coord_src"].isin(["placeholder", "official"]).all() if ph.any() else True)
    # (5) h3_r8 nhat quan voi toa do da resolve
    def _h3ok(r):
        if not r["coord_resolved"] or not _coord_ok(r["lat"], r["lng"]):
            return True  # unresolved/xau: gate (2) da kiem h3 NULL
        return r["h3_r8"] == h3.latlng_to_cell(r["lat"], r["lng"], H3_RES)
    gates["h3_consistent"] = bool(df.apply(_h3ok, axis=1).all())

    return {
        "n_input": int(n),
        "n_placeholder": int(ph.sum()),
        "n_addr_mismatch_advisory": int(mm.sum()),
        "n_unresolved": int(unresolved.sum()),
        "n_snapped_official": int((df["coord_src"] == "official").sum()),
        "coord_src": df["coord_src"].value_counts().to_dict(),
        "gates": gates,
        "all_gates_pass": bool(all(gates.values())),
    }


def _load_canonical_stations() -> pd.DataFrame:
    cols = ["station_id", "station_code", "lat", "lng", "h3_r8", "province_code",
            "name", "address", "physical_id", "is_primary", "official_store_id",
            "quality_flags"]
    return pd.read_parquet(STATIONS_DIR, columns=cols)


def main():
    ap = argparse.ArgumentParser(
        description="E-DQ1: sua toa do placeholder/trung (inspect canonical, khong ghi de)")
    ap.add_argument("--dump", action="store_true", help="dump cum placeholder ra CSV de eyeball")
    args = ap.parse_args()

    df = _load_canonical_stations()
    out = resolve_coords(df)
    rep = fix_report(out)

    report_path = INTERIM_DIR / "fix_coords_report.json"
    report_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print("================ E-DQ1 SUA TOA DO PLACEHOLDER / TRUNG KHIT ================")
    print(f"  input                       : {rep['n_input']:,}")
    print(f"  COORD_PLACEHOLDER (toa do sai): {rep['n_placeholder']:,}")
    print(f"  COORD_ADDR_MISMATCH (advisory): {rep['n_addr_mismatch_advisory']:,}  (giu toa do, -> E-DQ3 trong tai)")
    print(f"  snap official (cuu duoc)    : {rep['n_snapped_official']:,}")
    print(f"  unresolved (loai khoi cung) : {rep['n_unresolved']:,}  (h3_r8=NULL)")
    print(f"  coord_src                   : {rep['coord_src']}")
    print(f"  QA gates                    : {rep['gates']}")
    print(f"  ALL GATES PASS              : {rep['all_gates_pass']}")
    if args.dump:
        flagged = out[out["quality_flags"].apply(
            lambda l: PLACEHOLDER_FLAG in l or MISMATCH_FLAG in l)].copy()
        csv_path = INTERIM_DIR / "fix_coords_flagged.csv"
        flagged[["station_id", "station_code", "province_code", "coord_src",
                 "coord_resolved", "lat_raw", "lng_raw", "name", "address"]
                ].to_csv(csv_path, index=False)
        print(f"  cum flag -> {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"-> {report_path.relative_to(PROJECT_ROOT)}")
    print("==========================================================================")
    return out, rep


if __name__ == "__main__":
    main()
