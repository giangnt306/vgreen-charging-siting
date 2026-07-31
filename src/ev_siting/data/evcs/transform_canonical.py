#!/usr/bin/env python3
"""transform_canonical.py — master CSV (crawl-shape) -> canonical parquet 2 tang.

Bien doi `data/interim/stations_master_evcs.csv` (khoa `station_code`, hinh dang
crawl tho) thanh HAI bang canonical dung SCHEMA_CONTRACT muc 2/3:

  - `stations`   : 1 dong/tram (khoa `station_id` = `vn-<code>`), co `h3_r8`,
                   `operator`, tin hieu chat luong (`confidence`/`freshness`/
                   `quality_flags`), nhan hanh chinh (E-DQ3).
  - `connectors` : tang 2 — no `evse_powers` thanh 1 dong/nhom cong suat
                   (FK `station_id`). Day la mo hinh `station -> connector`.

PHAM VI: du an chi nham vao O TO -> MAC DINH BO `BATTERY_SWAP`
(tram doi pin khong phai tram sac oto). Co the keo lai bang `--keep-bss`.

P7 (nhiem xe may / power tier): evcs.vn chi lo cong suat, khong lo chuan cam ->
gan `connector_standard`/`vehicle_class` + sua AC/DC tu registry chinh thuc
(`official_connectors.standard`, join store_id==station_code). Xem `load_official_std`.

Output: Parquet Hive-partitioned theo `province_code`:
  data/interim/canonical/stations/province_code=<XX>/*.parquet
  data/interim/canonical/connectors/province_code=<XX>/*.parquet

F7/F12 (port tu review 28/07): `join_xref` FAIL-FAST khi `official_xref.parquet`
thieu hoac cu (doi chieu sha256 byte-for-byte voi master, khoa unique, PHU du
station_code canonical can); recovery tuong minh bang `--allow-missing-xref`.
Ghi canonical NGUYEN TU — swap ca generation (`_write_partitioned_atomically`),
crash giua chung khong bao gio de canonical cut nua.

Chay:
    PYTHONPATH=src python -m ev_siting.data.evcs.transform_canonical
    PYTHONPATH=src python -m ev_siting.data.evcs.transform_canonical --keep-bss
"""
import argparse
import hashlib
import json
import re
import shutil
import uuid

import h3
import numpy as np
import pandas as pd

from .paths import MASTER_CSV, STATIONS_DIR, CONNECTORS_DIR, CANONICAL_DIR, PROJECT_ROOT
from .connector_rollup import rollup as live_rollup
from .dedup_crosssource import assign_physical_id, dedup_report, DUP_COLS
from .fix_coords import resolve_coords, fix_report, FIX_COLS
from .resolve_config import resolve_config, config_report, load_occ_max, CONFIG_COLS
from ..admin.enrich_stations import (ADMIN_COLS, admin_report, build_crosswalk,
                                     enrich_admin)
from ..admin.paths import PROVINCE_CROSSWALK, ensure_dirs as ensure_admin_dirs
from ..vinfast_official.paths import XREF_PARQUET, CONNECTORS_PARQUET as OFFICIAL_CONNECTORS

H3_RES = 8

# --- P7: chuan cam (plug standard) tu registry chinh thuc, KHONG suy tu power tier ---
# evcs.vn chi lo cong suat (kW), khong lo chuan cam -> power tier khong tach duoc
# xe may/o to va gan sai AC/DC o dai 20-22 kW (thuc te la DC CCS2). VinFast official
# (`official_connectors.standard`) la nguon su that; join theo store_id==station_code
# (xem memory vinfast-official-join-key). Chi CCS2/Type2 moi la chuan O TO.
STD_SHORT = {"IEC_62196_T2_COMBO": "CCS2", "IEC_62196_T2": "TYPE2"}
CAR_STANDARDS = {"CCS2", "TYPE2"}

# Cot provenance/doi chieu nguon chinh thuc (match_official.py), join theo station_code.
XREF_COLS = [
    "official_matched", "match_method", "official_store_id",
    "match_dist_m", "match_name_sim", "official_charging_status",
    "official_access_type", "provenance",
]
AC_MAX_W = 25000                       # <=25 kW = AC, >25 kW = DC (khop build_master_evcs)
VN_BBOX = (8.0, 23.6, 102.0, 110.0)    # lat_min, lat_max, lng_min, lng_max
# ADMIN_COLS nay gio do E-DQ3 (admin/enrich_stations.py) dien tu ranh gioi xa VNSDI —
# KHONG con la "cot de trong cho Step B". `province_code` (he 63 tinh CU, prefix ma evcs)
# GIU NGUYEN canh `admin_l1_code` (34 tinh, nien dai 2025-06-16): mot cai la provenance
# tho, mot cai la su that hinh hoc. Khong doi ten cai nay thanh cai kia.

# --- P8: loc trang thai van hanh & access (private vs public) — QUYET DINH TUONG MINH ---
# Hai truc DOC LAP, deu resolve OFFICIAL-FIRST (registry VinFast la ground truth,
# xem memory vinfast-official-join-key), fallback evcs chi khi tram evcs-only.
# LY DO official-first: `status` cua evcs la SNAPSHOT telemetry (trang thai tuc thoi
# luc polling occupancy) -> "Available" mot khoanh khac KHONG lat nguoc registry ghi
# INACTIVE. `official_charging_status` la trang thai lifecycle on dinh (crawl 2026-07-20).
# op_status: gom telemetry occupancy (Available/AllBusy/BUSY) ve OPERATIONAL; maintenance
# la tam thoi; OUT_OF_SERVICE la da ngung. access: Public/Restricted/Unknown.
OFFICIAL_OP_STATUS = {
    "ACTIVE": "OPERATIONAL", "BUSY": "OPERATIONAL",
    "INACTIVE": "MAINTENANCE",
    "OUTOFSERVICE": "OUT_OF_SERVICE", "UNAVAILABLE": "OUT_OF_SERVICE",
}
EVCS_OP_STATUS = {
    "Available": "OPERATIONAL", "AllBusy": "OPERATIONAL",
    "Maintaining": "MAINTENANCE", "OutOfService": "OUT_OF_SERVICE",
}
# Co P8 gan vao quality_flags theo op_status/access -> model (Ky) tu quyet loc them.
OP_STATUS_FLAG = {"OUT_OF_SERVICE": "NOT_OPERATIONAL",
                  "MAINTENANCE": "UNDER_MAINTENANCE", "UNKNOWN": "STATUS_UNKNOWN"}
ACCESS_FLAG = {"RESTRICTED": "NON_PUBLIC", "UNKNOWN": "ACCESS_UNKNOWN"}


def resolve_status_access(df: pd.DataFrame) -> pd.DataFrame:
    """P8: sinh cot canonical `op_status`/`access`/`is_operational` (official-first)
    + gan co P8 vao `quality_flags`. KHONG xoa dong, KHONG default ngam — chi phoi
    bay tuong minh de model quyet dinh (chay ca 2 chieu voi UNKNOWN/MAINTENANCE).

    - op_status  : OPERATIONAL / MAINTENANCE / OUT_OF_SERVICE / UNKNOWN
    - access     : PUBLIC / RESTRICTED / UNKNOWN
    - is_operational : loc cung DUY NHAT — loai OUT_OF_SERVICE (tram da ngung, khong
      con la cung thuc). MAINTENANCE/UNKNOWN GIU (co ha tang vat ly; flag de model
      loc them neu muon)."""
    off_st = df["official_charging_status"].map(OFFICIAL_OP_STATUS)
    evcs_st = df["status"].map(EVCS_OP_STATUS)
    df["op_status"] = off_st.fillna(evcs_st).fillna("UNKNOWN")

    off_ac = df["official_access_type"].map({"Public": "PUBLIC", "Restricted": "RESTRICTED"})
    evcs_ac = df["is_public"].map({True: "PUBLIC", False: "RESTRICTED"})
    df["access"] = off_ac.fillna(evcs_ac).fillna("UNKNOWN")

    df["is_operational"] = df["op_status"] != "OUT_OF_SERVICE"

    def _add_flags(row):
        fl = list(row["quality_flags"])
        for cand in (OP_STATUS_FLAG.get(row["op_status"]), ACCESS_FLAG.get(row["access"])):
            if cand and cand not in fl:
                fl.append(cand)
        return fl
    df["quality_flags"] = df.apply(_add_flags, axis=1)
    return df


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


def load_official_std():
    """Lookup `(station_code, power_kw)` -> `(connector_standard, current_type)`.

    Xay tu `official_connectors` (VinFast first-party) — nguon DUY NHAT lo `standard`
    (chuan cam). Dung de gan `vehicle_class` va SUA AC/DC (P7): power tier cua evcs
    gan sai 20-22 kW la AC, thuc te la DC CCS2. `power_type` (`AC_3_PHASE`/`DC`) la
    AC/DC dung theo first-party. Tra {} neu chua co registry -> fallback power tier."""
    if not OFFICIAL_CONNECTORS.exists():
        return {}
    oc = pd.read_parquet(
        OFFICIAL_CONNECTORS,
        columns=["store_id", "standard", "power_type", "max_electric_power_kw"],
    )
    lut = {}
    for code, kw, std, pt in zip(oc["store_id"], oc["max_electric_power_kw"],
                                 oc["standard"], oc["power_type"]):
        try:
            key = (code, round(float(kw), 1))
        except (TypeError, ValueError):
            continue
        cur = "AC" if str(pt).startswith("AC") else "DC"
        lut.setdefault(key, (STD_SHORT.get(std, "OTHER"), cur))
    return lut


def explode_connectors(evse_powers_json, sid, code, prov, std_lut):
    """`evse_powers` (JSON) -> list dong connector (tang 2).

    evsePowers = [{type:<W>, totalEvse:<so sung lap>, numberOfAvailableEvse:<trong>}].
    Moi nhom cong suat -> 1 connector. `current_type` + `connector_standard` +
    `vehicle_class` lay tu registry chinh thuc (`std_lut`) khi khop; neu khong khop
    (tram evcs-only) -> fallback power tier + `UNKNOWN`/`UNVERIFIED` (P7).
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
        pw = round(w / 1000, 1) if w else None
        official = std_lut.get((code, pw)) if pw is not None else None
        if official:
            std_short, cur = official                 # chuan cam + AC/DC first-party
        else:
            std_short = "UNKNOWN"                       # evcs-only: khong xac minh duoc
            cur = "AC" if 0 < w <= AC_MAX_W else "DC"   # fallback power tier
        veh = "CAR" if std_short in CAR_STANDARDS else "UNVERIFIED"
        rows.append({
            "connector_id": f"{sid}-c{idx}",
            "station_id": sid,
            "station_code": code,
            "province_code": prov,
            "power_kw": pw,
            "current_type": cur if w > 0 else None,
            "connector_standard": std_short,
            "vehicle_class": veh,
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


def _sha256(path) -> str:
    """sha256 noi dung file — cung ham bam voi match_official (cong F7)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def join_xref(df: pd.DataFrame, *, require_xref: bool = True) -> pd.DataFrame:
    """Left-join provenance tu official_xref.parquet theo `station_code`.

    F7: xref phai duoc sinh tu DUNG master hien tai (sha256 byte-for-byte), khoa
    unique va PHU du station_code canonical can — sai la FAIL-FAST, khong join am
    tham tren xref cu. `--allow-missing-xref` chi danh cho recovery co chu dich."""
    # bo cot cung ten tu master (verified/confidence tho) de xref lam chu.
    df = df.drop(columns=[c for c in ("verified", "confidence", *XREF_COLS)
                          if c in df.columns])
    if XREF_PARQUET.exists():
        xref = pd.read_parquet(XREF_PARQUET)
        missing = {"station_code", "source_master_sha256"} - set(xref.columns)
        if missing:
            raise SystemExit(f"F7 FAIL: xref thieu cot gate {sorted(missing)}; "
                             f"chay match_official lai")
        hashes = set(xref["source_master_sha256"].dropna().astype(str))
        if hashes != {_sha256(MASTER_CSV)}:
            raise SystemExit("F7 FAIL: official_xref stale so voi "
                             "stations_master_evcs.csv; chay match_official lai")
        if xref["station_code"].duplicated().any():
            raise SystemExit("F7 FAIL: official_xref station_code khong unique")
        # PHU chu khong BANG: matcher chay tren master DAY DU (gom BATTERY_SWAP),
        # con `df` o day da loc pham vi. Doi bang nhau => canonical FAIL 100% o
        # duong mac dinh. Dieu kien dung: xref phai phu MOI ma canonical can.
        missing_codes = (set(df["station_code"].astype(str))
                         - set(xref["station_code"].astype(str)))
        if missing_codes:
            raise SystemExit(
                f"F7 FAIL: official_xref thieu {len(missing_codes)} station_code "
                f"cua master (vd {sorted(missing_codes)[:3]}); chay match_official lai")
        keep = ["station_code", "confidence", "verified"] + XREF_COLS
        xref = xref[[c for c in keep if c in xref.columns]]
        df = df.merge(xref, on="station_code", how="left")
        df["_has_xref"] = df["official_matched"].notna()
    elif require_xref:
        raise SystemExit("F7 FAIL: thieu official_xref.parquet; "
                         "chay `make match-official` truoc canonical")
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


def _write_partitioned_atomically(stations: pd.DataFrame, connectors: pd.DataFrame) -> None:
    """F12: dung ca hai dataset NGOAI duong dan roi swap nguyen the he canonical.

    Ghi truc tiep (rmtree roi to_parquet thang vao cho) nghia la crash giua chung
    de lai canonical cut nua chung (stations moi + connectors cu, hoac thieu han
    mot bang). Swap ca generation: hoac the he moi day du, hoac giu the he cu."""
    parent = CANONICAL_DIR.parent
    tmp = parent / f".canonical-tmp-{uuid.uuid4().hex}"
    backup = parent / f".canonical-prev-{uuid.uuid4().hex}"
    try:
        tmp.mkdir(parents=True)
        stations.to_parquet(tmp / "stations", partition_cols=["province_code"], index=False)
        connectors.to_parquet(tmp / "connectors", partition_cols=["province_code"], index=False)
        moved_old = False
        if CANONICAL_DIR.exists():
            CANONICAL_DIR.replace(backup)
            moved_old = True
        try:
            tmp.replace(CANONICAL_DIR)
        except Exception:
            if CANONICAL_DIR.exists():
                shutil.rmtree(CANONICAL_DIR)
            if moved_old and backup.exists():
                backup.replace(CANONICAL_DIR)
            raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


def run(keep_bss: bool = False, *, require_xref: bool = True):
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

    # --- provenance/verified/confidence tu doi chieu nguon chinh thuc ---
    df = join_xref(df, require_xref=require_xref)
    df = redefine_confidence(df)

    stations_cols = [
        "station_id", "station_code", "lat", "lng", "h3_r8",
        # E-DQ3: nhan hanh chinh (VNSDI cap xa, nien dai 2025-06-16) + provenance/trong tai
        *ADMIN_COLS, "province_code",
        "name", "address", "operator", "station_type", "vehicle_class",
        # 31/07 — 5 cot LIVE (current_type/max_power_kw/total_power_kw/num_connectors/
        # connector_types) DA GO khoi `stations`: chung la ban sao cua `connectors`
        # (doi soat 0/19.225 lech tren ca 4 cot scalar). Ban sao khong co cong -> P7
        # da sua `connectors` + `current_type` nhung QUEN `connector_types`, de lai
        # 1.579 tram tu mau thuan. Consumer can thi goi `connector_rollup.attach()`.
        # Tang TAI SAN (E-DQ4, CONFIG_COLS ben duoi) O LAI: KHONG suy duoc tu connectors.
        "status", "is_public", "op_status", "access", "is_operational",
        "verified", "has_timeseries",
        "confidence", "freshness", "quality_flags",
        # provenance / doi chieu nguon chinh thuc (vinfastauto.com)
        "provenance", "official_matched", "match_method", "official_store_id",
        "match_dist_m", "match_name_sim", "official_charging_status", "official_access_type",
        # E-DQ2: dedup cheo nguon (physical_id/is_primary/dup_*)
        *DUP_COLS,
        # E-DQ1: toa do placeholder (lat_raw/lng_raw/coord_src/coord_fix_dist_m/coord_resolved)
        *FIX_COLS,
        # E-DQ4: tang TAI SAN (n_guns_installed/site_power_kw/... + config_src/config_resolved)
        *CONFIG_COLS,
    ]

    # --- tang 2: no connectors (kem chuan cam + vehicle_class tu registry chinh thuc) ---
    std_lut = load_official_std()
    conn_rows = []
    for _, r in df.iterrows():
        conn_rows.extend(
            explode_connectors(r["evse_powers"], r["station_id"], r["station_code"],
                               r["province_code"], std_lut)
        )
    connectors = pd.DataFrame(conn_rows, columns=[
        "connector_id", "station_id", "station_code", "province_code",
        "power_kw", "current_type", "connector_standard", "vehicle_class",
        "connector_label", "count_total", "count_available",
    ])

    # --- P7: roll-up tu connector da sua chuan cam ve station ---
    # current_type dung (AC/DC/MIXED) suy tu connector, ghi de nhan power-tier cu.
    def _roll_current(s):
        has_ac, has_dc = (s == "AC").any(), (s == "DC").any()
        return "MIXED" if has_ac and has_dc else ("AC" if has_ac else "DC" if has_dc else None)
    cur_by_st = connectors.groupby("station_id")["current_type"].apply(_roll_current)
    # vehicle_class: CAR neu moi connector la chuan o to; UNVERIFIED neu con connector
    # chua co chuan chinh thuc (evcs-only); UNKNOWN neu tram khong co connector nao.
    veh_by_st = connectors.groupby("station_id")["vehicle_class"].apply(
        lambda s: "CAR" if (s == "CAR").all() else "UNVERIFIED")
    n_wrong_ct = int((df["station_id"].map(cur_by_st).notna()
                      & (df["current_type"] != df["station_id"].map(cur_by_st))).sum())
    df["current_type"] = df["station_id"].map(cur_by_st).fillna(df["current_type"])
    df["vehicle_class"] = df["station_id"].map(veh_by_st).fillna("UNKNOWN")
    # flag tuong minh cho tram CO connector nhung chua xac minh duoc chuan cam
    # (khong default ngam). Tram khong co connector -> E-DQ4 gan CONFIG_UNKNOWN /
    # CONFIG_LOWER_BOUND + tang ASSET (xem resolve_config.py).
    unv = df["vehicle_class"] == "UNVERIFIED"
    df.loc[unv, "quality_flags"] = df.loc[unv, "quality_flags"].apply(
        lambda l: l if "STD_UNVERIFIED" in l else l + ["STD_UNVERIFIED"])

    # --- P8: loc trang thai van hanh & access (official-first, tuong minh) ---
    df = resolve_status_access(df)

    # --- E-DQ2: dedup CHEO NGUON (evcs<->official) — gan physical_id + is_primary ---
    # Cung 1 tram vat ly co the co >1 dong (nhieu app/feed cung 1 store official, hoac
    # cung 1 tram o 2 feed). FLAG khong xoa: primary=cung that; duplicate giu+co
    # CROSS_SOURCE_DUP. Cum toa do ngo -> DUP_COORD_SUSPECT, de E-DQ1 phan xu.
    df = assign_physical_id(df)
    dq2 = dedup_report(df)
    if not dq2["all_gates_pass"]:
        raise SystemExit(f"E-DQ2 QA gate FAIL: {dq2['gates']}")

    # --- E-DQ1: toa do placeholder / trung khit (chay SAU E-DQ2 — nhan DUP_COORD_SUSPECT) ---
    # Detector A (stack xa tinh) = toa do chac chan sai -> coord_resolved=False, h3_r8=NULL,
    # loai khoi cung. Detector B (lech province, advisory) giu toa do, de E-DQ3 trong tai.
    df = resolve_coords(df)
    dq1 = fix_report(df)
    if not dq1["all_gates_pass"]:
        raise SystemExit(f"E-DQ1 QA gate FAIL: {dq1['gates']}")

    # --- E-DQ4: tang TAI SAN vs tang TRANG THAI SONG (chay SAU P8/E-DQ2/E-DQ1) ---
    # `evse_powers` la mang trang thai SONG, khong phai so dang ky tai san: EVSE tat
    # thi roi khoi mang -> `num_connectors` doc THIEU am tham (1.568 tram, 0 tram doc
    # THUA). Hop giai official-first CO `max()` (ca 3 nguon deu la chan DUOI), them 8
    # cot ASSET; KHONG ghi de cot LIVE. Phai chay sau P8/E-DQ2/E-DQ1 vi bao cao/cong
    # do tren tap CUNG (is_operational & PUBLIC & is_primary & coord_resolved).
    occ_max = pd.Series(pd.to_numeric(df["ts_val_max"], errors="coerce").to_numpy(),
                        index=df["station_code"].to_numpy())
    df = resolve_config(df, occ_max)
    dq4 = config_report(df, occ_max)
    if not dq4["all_gates_pass"]:
        raise SystemExit(f"E-DQ4 QA gate FAIL: {dq4['gates']}")

    # cung TRUOC E-DQ3 — de doi soat tac dong cua trong tai toa do bang ranh gioi xa.
    n_supply_pre = int((df["is_operational"] & (df["access"] == "PUBLIC")
                        & df["is_primary"] & df["coord_resolved"]).sum())

    # --- E-DQ3: nhan hanh chinh + TRONG TAI toa do (chay SAU E-DQ1 — doc coord_resolved) ---
    # Point-in-polygon tren ranh gioi xa VNSDI dien 4 cot khai bao (null 100% tu truoc
    # den nay) VA phan xu not phan du ma E-DQ1 co y hoan: 758 COORD_ADDR_MISMATCH. Ranh
    # gioi xa chi co DAT nen no bat duoc toa do sai ma `in_vn` cua E-DQ7a khong bat duoc
    # (polygon adm2 GOM lanh hai) -> COORD_OUTSIDE_ADMIN loai them khoi cung.
    df = enrich_admin(df)
    dq3 = admin_report(df)
    if not dq3["all_gates_pass"]:
        raise SystemExit(f"E-DQ3 QA gate FAIL: {dq3['gates']}")
    ensure_admin_dirs()
    build_crosswalk(df).to_csv(PROVINCE_CROSSWALK, index=False)

    # --- cong: go cot LIVE khoi `stations` phai KHONG mat thong tin ---
    # Truoc khi bo 5 cot LIVE, chung minh `connectors` tai tao duoc chung ĐUNG BIT.
    # Day chinh la cong ma ban denormalize cu THIEU: P7 sua `connectors` roi ma
    # `connector_types` o `stations` van giu nhan AC cu, khong ai bao.
    _live = live_rollup(connectors)
    _chk = df[["station_id", "num_connectors", "max_power_kw", "total_power_kw"]].copy()
    _chk = _chk.join(_live[["num_connectors", "max_power_kw", "total_power_kw"]],
                     on="station_id", rsuffix="_der")
    _has = _chk["station_id"].isin(_live.index)
    _bad = {}
    for c in ("num_connectors", "max_power_kw", "total_power_kw"):
        a = pd.to_numeric(_chk.loc[_has, c], errors="coerce")
        b = pd.to_numeric(_chk.loc[_has, c + "_der"], errors="coerce")
        n = int((~np.isclose(a.fillna(-1), b.fillna(-1), rtol=1e-9, atol=1e-6)).sum())
        if n:
            _bad[c] = n
    if _bad:
        raise SystemExit(f"LIVE rollup KHONG tai tao duoc tu connectors: {_bad} "
                         f"-> khong duoc go cot LIVE khoi stations")

    stations = df[stations_cols].reset_index(drop=True)

    # --- ghi Parquet Hive-partitioned theo province_code (F12: swap ca generation) ---
    # province_code rong -> "NA" de khong vo partition.
    stations["province_code"] = stations["province_code"].fillna("").replace("", "NA")
    connectors["province_code"] = connectors["province_code"].fillna("").replace("", "NA")
    _write_partitioned_atomically(stations, connectors)

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
    print(f"  tram 0 sung DANG BAO CAO: {(df['num_connectors'] == 0).sum():,} "
          f"(gia tri LIVE dung — cau hinh LAP DAT xem E-DQ4)")
    print(f"  connector orphan (FK)   : {n_orphan}")
    print("--- P7 (chuan cam thay power tier) ------------------------")
    print(f"  connector_standard      : {connectors['connector_standard'].value_counts().to_dict()}")
    print(f"  vehicle_class (station) : {stations['vehicle_class'].value_counts().to_dict()}")
    print(f"  current_type sua tu tier : {n_wrong_ct:,} tram (20-22 kW: AC->DC CCS2)")
    print(f"  STD_UNVERIFIED (evcs-only): {int(stations['quality_flags'].apply(lambda l: 'STD_UNVERIFIED' in l).sum()):,}")
    print("--- P8 (trang thai van hanh & access, official-first) ------")
    print(f"  op_status               : {stations['op_status'].value_counts().to_dict()}")
    print(f"  access                  : {stations['access'].value_counts().to_dict()}")
    print(f"  is_operational=False    : {int((~stations['is_operational']).sum()):,} (OUT_OF_SERVICE, loai khoi cung)")
    n_supply = int((stations['is_operational'] & (stations['access'] == 'PUBLIC')
                    & stations['is_primary'] & stations['coord_resolved']).sum())
    print(f"  cung cong khai kha dung : {n_supply:,} (is_operational & PUBLIC & is_primary & coord_resolved)")
    print("--- E-DQ1 (toa do placeholder / trung khit) --------------")
    print(f"  COORD_PLACEHOLDER       : {dq1['n_placeholder']:,} (toa do sai -> coord_resolved=False, h3_r8=NULL)")
    print(f"  COORD_ADDR_MISMATCH     : {dq1['n_addr_mismatch_advisory']:,} (advisory, giu toa do -> E-DQ3 trong tai)")
    print(f"  snap official           : {dq1['n_snapped_official']:,}")
    print(f"  unresolved (loai cung)  : {dq1['n_unresolved']:,}")
    print(f"  h3_r8 null (toa do xau + placeholder): {int(stations['h3_r8'].isna().sum()):,}")
    print(f"  QA gates (5 cong)       : {'PASS' if dq1['all_gates_pass'] else 'FAIL'}  {dq1['gates']}")
    print("--- E-DQ2 (dedup cheo nguon evcs<->official) --------------")
    print(f"  primary (cung that)     : {dq2['n_primary']:,}")
    print(f"  duplicate (flag, giu)   : {dq2['n_duplicate']:,}  {dq2['dup_by_method']}")
    print(f"  so nhom trung           : {dq2['n_dup_groups']:,} (max {dq2['largest_group']}/nhom)")
    print(f"  cum toa do ngo -> E-DQ1 : {dq2['n_suspect_coord_deferred_edq1']:,} (DUP_COORD_SUSPECT)")
    print(f"  QA gates (5 cong)       : {'PASS' if dq2['all_gates_pass'] else 'FAIL'}  {dq2['gates']}")
    print("--- E-DQ4 (cau hinh LAP DAT vs mang trang thai SONG) ------")
    print(f"  config_src              : {dq4['config_src']}")
    print(f"  CONFIG_TRUNCATED        : {dq4['n_truncated']:,} (+{dq4['n_guns_recovered']:,} sung lay lai)")
    print(f"  CURRENT_TYPE_CORRECTED  : {dq4['n_current_type_corrected']:,} (DC-that-la-MIXED)")
    print(f"  CONFIG_UNKNOWN (du)     : {dq4['n_unknown']:,} {dq4['n_unknown_by_type']} "
          f"-> loai khoi mau so CO TRONG SO CONG SUAT")
    print(f"  sung: SONG -> LAP DAT   : {dq4['guns_reporting_total']:,} -> {dq4['guns_installed_total']:,} "
          f"(cung: {dq4['supply']['guns_reporting']:,} -> {dq4['supply']['guns_installed']:,})")
    print(f"  kW: live/nameplate/site : {dq4['power_kw']['live_total_power_kw']:,.0f} / "
          f"{dq4['power_kw']['asset_nameplate_kw']:,.0f} / {dq4['power_kw']['asset_site_kw']:,.0f} "
          f"(to chia cong suat: {dq4['power_kw']['cabinet_inflation']}x)")
    print(f"  resolved tren cung      : {dq4['supply']['resolved_rate']:.4f} "
          f"(chua resolve {dq4['supply']['n_unresolved']:,}; o cung cong suat 0: "
          f"{dq4['supply']['cells_zero_capacity']:,})")
    print(f"  QA gates (8 cong)       : {'PASS' if dq4['all_gates_pass'] else 'FAIL'}  {dq4['gates']}")
    print("--- E-DQ3 (nhan hanh chinh + trong tai toa do) ------------")
    print(f"  nguon / nien dai        : VNSDI cap xa / {dq3['admin_vintage']} "
          f"({dq3['n_provinces']} tinh · {dq3['n_communes']:,} xa co tram)")
    print(f"  gan nhan duoc           : {dq3['n_labelled']:,} "
          f"({dq3['join_rate_on_resolved']:.4%} tren tap coord_resolved) {dq3['admin_src']}")
    print(f"  COORD_OUTSIDE_ADMIN     : {dq3['n_outside_admin']:,} (toa do ngoai moi xa "
          f"> {dq3['snap_tol_m']:.0f} m -> loai khoi cung, h3_r8=NULL)")
    print(f"  snap bien 1:1M          : {dq3['n_snapped']:,} (ven bien/song, xa gan nhat khop dia chi)")
    print(f"  phan xu COORD_ADDR_MISMATCH: CONFIRMED {dq3['verdicts'].get('COORD_CONFIRMED', 0):,} "
          f"· BAD {dq3['verdicts'].get('COORD_BAD', 0):,} · UNRESOLVED "
          f"{dq3['verdicts'].get('UNRESOLVED', 0):,} (E-DQ1 hoan lai, nay dong duoc)")
    print(f"  ADMIN_PROVINCE_CONFLICT : {dq3['n_province_conflict']:,} (advisory — "
          f"province_code he 63 CU vs admin_l1_code 34)")
    print(f"  crosswalk 63 -> 34      : {dq3['n_crosswalk_ok']} ma OK, "
          f"AMBIGUOUS {dq3['crosswalk_ambiguous']} -> {PROVINCE_CROSSWALK.relative_to(PROJECT_ROOT)}")
    print(f"  cung sau E-DQ3          : {dq3['n_supply']:,} (= {n_supply_pre:,} - "
          f"{dq3['n_outside_admin']:,} toa do ngoai moi xa)")
    print(f"  QA gates (7 cong)       : {'PASS' if dq3['all_gates_pass'] else 'FAIL'}  {dq3['gates']}")
    print(f"  confidence trung binh   : {stations['confidence'].mean():.3f}")
    print(f"  verified (first-party)  : {int(stations['verified'].sum()):,} / {len(stations):,}")
    print(f"  match_method            : {stations['match_method'].value_counts().to_dict()}")
    print(f"  provenance              : {stations['provenance'].value_counts().to_dict()}")
    print("Buoc ke: `make admin-grid` de gan nhan hanh chinh cho `demand_h3` + rollup xa.")
    print("=============================================================")
    return stations, connectors


def main():
    ap = argparse.ArgumentParser(description="master CSV -> canonical parquet (stations/connectors)")
    ap.add_argument("--keep-bss", action="store_true",
                    help="giu lai BATTERY_SWAP (mac dinh bo — du an chi nham oto)")
    ap.add_argument("--allow-missing-xref", action="store_true",
                    help="recovery tuong minh: cho phep canonical chay khong co official_xref (F7)")
    args = ap.parse_args()
    run(keep_bss=args.keep_bss, require_xref=not args.allow_missing_xref)


if __name__ == "__main__":
    main()
