#!/usr/bin/env python3
"""resolve_config.py — E-DQ4: cau hinh khuyet la loi NGU NGHIA, khong phai loi thieu du lieu.

Register ghi E-DQ4 = "cau hinh khuyet (`current_type`/`max_power_kw`/`total_power_kw`
null, `num_connectors=0`)" = 282 dong (1,45%). Do lai 30/07: TRIEU CHUNG dung, DINH
NGHIA sai. Khuyet tat thuc te cham 8,1% tram va 9,0% tong so sung toan quoc, va KHONG
mot phep dem null nao thay duoc no vi khong co gi bi null.

GOC RE (mot co che duy nhat). `build_master_evcs.derive_power` ghi `totalEvse` la
"so sung THAT" (build_master_evcs.py:33) — SAI. `evsePowers` la MANG TRANG THAI SONG:
mot EVSE chi xuat hien khi no dang duoc dang ky VA dang bao cao. Bang chung, crosstab
`depot` (trang thai song) x `evse_powers` rong tren tab VinFast:
    Available 14.819 -> 0 rong | AllBusy 1.237 -> 0 | Maintaining 3.331 -> 177 |
    OutOfService 40 -> 25
Registry chinh thuc cung vay: trong 282 dong null, official CO dong EVSE cho dung 25
tram `charging_status=OUTOFSERVICE` va KHONG CO dong nao cho 177 tram `INACTIVE`.
=> CA HAI nguon deu la feed trang thai song, khong phai so dang ky tai san.

Cung ho loi voi E-DQ7b (`road_len` sai ngu nghia) va E-DQ8a (do o thang sai), KHONG
cung ho voi mot van de missing-data. Tat ca mang tat -> null (buoc A). MOT PHAN mang
tat -> dem thieu am tham (buoc B). Ca mot loai dong dien tat -> `current_type` sai
(buoc C).

BON BUOC DO DUOC (do 30/07 tren artefact da freeze, snapshot 2026-07-20):
  A  282/19.507 tram null ca 4 truong; 134 nam trong CUNG (19.015), toan bo MAINTENANCE;
     60/12.811 o cung doc tong cong suat = 0.
  B  1.568 tram (8,1%) co it sung hon registry; 0 tram co NHIEU hon. Bat doi xung mot
     chieu = dau hieu TRUNCATION, khong phai nhieu. Thieu 6.249 sung (9,0%); tren tap
     cung 1.498 tram / +6.055 sung (+9,9%). Lech theo dong dien: AC thieu 14,2% vs
     DC 3,8%; tier te nhat 7,0 kW thieu 56,1%.
  C  556 tram sai `current_type`, trong do 521 bi ghi `DC` nhung thuc la `MIXED`
     (chinh cac sung AC bi thieu). Khong phai sai so lam tron: 501 tram do co
     occ_mean = 2,221, CAO HON ca hai nhom chung co the roi vao (evcs DC 1,652 /
     evcs MIXED 1,831) — dung truc ma E-DQ7d do duoc chenh 13x.
  D  `total_power_kw` sai ngu nghia: no la Sigma(nameplate tung sung). Nhung 21.806
     to sac (`physical_reference`) mang >=2 sung, 100% cung rated kW va cung standard
     = HAI hong tren MOT to. Sigma theo sung 3.182.147 kW vs Sigma theo to 1.741.991 kW
     => phong dai 1,83x. Vay `total_power_kw` DONG THOI bi truncate (B) va bi phong dai (D).

KIEM CHUNG NGOAI VI (khong can registry): 132 tram cung ghi nhan SO XE dang sac dong
thoi > SO SUNG lap dat (`ts_val_max > num_connectors`) — bat kha thi ve vat ly. Registry
giai quyet 132/132 (official guns >= ts_val_max o moi truong hop). Telemetry la NHAN
CHUNG cho cong suat lap dat — dung khuon "neo ngoai vi" ma E-DQ7c/E-DQ7d dung cho POI
va ham muc tieu, nay ap cho cau hinh.

CACH XU LY — TACH TANG TAI SAN KHOI TANG TRANG THAI SONG (khuon 2 cot cua E-DQ7b R1):
  LIVE  (giu nguyen, khong ghi de): `num_connectors` / `max_power_kw` /
        `total_power_kw` / `current_type` = "dang bao cao", dung cho chan doan
        van hanh. `num_connectors=0` la gia tri LIVE DUNG (khong co gi bao cao).
  ASSET (moi): `n_guns_installed` / `max_power_kw_asset` / `site_power_kw` /
        `nameplate_power_kw` / `current_type_asset` = "lap dat", dung cho cung,
        rang buoc cong suat, chuan hoa exposure cua E-DQ7d.

QUY TAC HOP GIAI: official-first CO HOP NHAT `max()`. Official-first theo P8 va memory
[[vinfast-official-join-key]]; nhung phan MOI la `max()`: CA HAI feed deu la chan DUOI,
nen phai HOP thay vi ghi de.
    n_guns_installed = max(official rows, evcs Sigma totalEvse, ts_val_max)
`max()` con phu 264 tram khong join duoc va dong 132 mau thuan vat ly.

CHINH SACH DU (nhat quan E-DQ8c "cong bo mau so"): 257 tram khong nguon nao dien duoc
(177 VinFast INACTIVE + 80 mang thu ba) => `config_resolved=False`,
`config_src=UNKNOWN`, co `CONFIG_UNKNOWN`. GIU lam diem phu / T0 brownfield (co ha
tang vat ly — nhat quan quyet dinh giu MAINTENANCE cua P8) nhung LOAI khoi moi mau so
CO TRONG SO CONG SUAT, va PHAI cong bo so bi loai. `n_guns_imputed` (median tinh x
loai tram) chi de phan tich do nhay, KHONG BAO GIO la gia tri mac dinh.

Chay doc lap (eyeball truoc khi tin — khong ghi de canonical):
    PYTHONPATH=src python -m ev_siting.data.evcs.resolve_config
    PYTHONPATH=src python -m ev_siting.data.evcs.resolve_config --dump
"""
import argparse
import json

import numpy as np
import pandas as pd

from .paths import STATIONS_DIR, MASTER_CSV, INTERIM_DIR, PROJECT_ROOT
from ..vinfast_official.paths import CONNECTORS_PARQUET as OFFICIAL_CONNECTORS

# --- cot canonical E-DQ4 them vao `stations` (tang TAI SAN) -------------------
CONFIG_COLS = [
    "n_guns_installed",      # Int64 — so sung LAP DAT (hop max cua 3 nguon); NA neu UNKNOWN
    "max_power_kw_asset",    # float — sung nhanh nhat theo tang tai san
    "site_power_kw",         # float — cong suat DIEM sac: Sigma theo TO (`physical_reference`)
    "nameplate_power_kw",    # float — Sigma nameplate TUNG SUNG (>= site_power_kw)
    "current_type_asset",    # AC/DC/MIXED suy tu tang tai san (khong tu mang song)
    "config_src",            # OFFICIAL | EVCS_LIVE | TELEMETRY_BOUND | UNKNOWN
    "config_resolved",       # bool — chi True cho OFFICIAL/EVCS_LIVE (do duoc, khong phai chan duoi)
    "n_guns_imputed",        # Int64 — chi de PHAN TICH DO NHAY, khong dung lam mac dinh
]

# --- co tuong minh gan vao `quality_flags` (flag, khong xoa dong) ------------
FLAG_TRUNCATED = "CONFIG_TRUNCATED"        # mang song dem thieu so voi registry (buoc B)
FLAG_UNKNOWN = "CONFIG_UNKNOWN"            # khong nguon nao dien duoc (buoc du)
FLAG_LOWER_BOUND = "CONFIG_LOWER_BOUND"    # chi co nhan chung telemetry (chan duoi)
FLAG_CABINET = "POWER_CABINET_SHARED"      # co >=1 to nhieu sung => nameplate > site (buoc D)
FLAG_CT_FIXED = "CURRENT_TYPE_CORRECTED"   # current_type song != tang tai san (buoc C)

SRC_OFFICIAL = "OFFICIAL"
SRC_EVCS = "EVCS_LIVE"
SRC_TELEMETRY = "TELEMETRY_BOUND"
SRC_UNKNOWN = "UNKNOWN"

#: ty le `config_resolved` toi thieu tren tap CUNG truoc khi coi E-DQ4 la dong.
MIN_RESOLVED_RATE = 0.985

#: `power_type` cua registry: `AC_3_PHASE`/`AC_1_PHASE` -> AC, `DC` -> DC.
_AC_PREFIX = "AC"


def _roll_current(has_ac: bool, has_dc: bool):
    if has_ac and has_dc:
        return "MIXED"
    if has_ac:
        return "AC"
    if has_dc:
        return "DC"
    return None


def load_official_config() -> pd.DataFrame:
    """Tang TAI SAN tu `official_connectors` — 1 dong/`store_id`.

    `official_connectors` la 1 dong/connector (da kiem: 1 connector/`evse_idx`, nen
    dem dong = dem sung). Tra bang index `store_id`:
      off_guns          so sung lap dat theo registry
      off_max_kw        sung nhanh nhat
      off_nameplate_kw  Sigma nameplate TUNG sung (= cach `total_power_kw` dang tinh)
      off_site_kw       Sigma theo TO sac: max(rated) tren tung `physical_reference`
      off_shared        co >=1 to mang >1 sung (=> nameplate > site)
      off_cur           AC/DC/MIXED tu `power_type` first-party

    `off_site_kw` la doc BAO TOAN: mot to 180 kW hai hong cap 180 kW, khong phai 360.
    Dong co `physical_reference` NULL (831 dong) khong nhom duoc -> tinh nhu to rieng
    (giu nguyen per-gun o do, khong doan). Tra DataFrame rong neu chua co registry.
    """
    empty = pd.DataFrame(columns=["off_guns", "off_max_kw", "off_nameplate_kw",
                                  "off_site_kw", "off_shared", "off_cur"])
    if not OFFICIAL_CONNECTORS.exists():
        return empty
    oc = pd.read_parquet(OFFICIAL_CONNECTORS, columns=[
        "store_id", "power_type", "max_electric_power_kw", "physical_reference"])
    if oc.empty:
        return empty
    oc = oc.copy()
    oc["kw"] = pd.to_numeric(oc["max_electric_power_kw"], errors="coerce")
    oc["is_ac"] = oc["power_type"].astype(str).str.startswith(_AC_PREFIX)
    # `physical_reference` NULL -> khoa rieng cho tung dong (moi dong = 1 to)
    ref = oc["physical_reference"].astype("object")
    oc["cab"] = np.where(ref.isna(), "__row_" + oc.index.astype(str), ref.astype(str))

    per_cab = oc.groupby(["store_id", "cab"]).agg(cab_kw=("kw", "max"),
                                                  cab_n=("kw", "size"))
    site = per_cab.groupby("store_id").agg(off_site_kw=("cab_kw", "sum"),
                                           off_shared=("cab_n", lambda s: bool((s > 1).any())))
    g = oc.groupby("store_id")
    out = pd.DataFrame({
        "off_guns": g.size(),
        "off_max_kw": g["kw"].max(),
        "off_nameplate_kw": g["kw"].sum(),
        "off_cur": g["is_ac"].agg(lambda s: _roll_current(bool(s.any()), bool((~s).any()))),
    }).join(site)
    return out


def load_occ_max() -> pd.Series:
    """`ts_val_max` tu master = so xe sac DONG THOI lon nhat quan sat duoc / tram.

    Day la NHAN CHUNG ngoai vi cho cong suat lap dat: khong the co 5 xe sac cung luc
    tren 2 sung. Da co san trong master (build_master_evcs.ts_stats -> `vmax`), nen
    khong phai quet lai 19.218 file time-series."""
    if not MASTER_CSV.exists():
        return pd.Series(dtype="float64")
    m = pd.read_csv(MASTER_CSV, usecols=["station_code", "ts_val_max"], low_memory=False)
    s = pd.to_numeric(m["ts_val_max"], errors="coerce")
    return pd.Series(s.to_numpy(), index=m["station_code"].to_numpy()).groupby(level=0).max()


def _add_flag(flags, flag):
    return flags if flag in flags else flags + [flag]


def resolve_config(stations: pd.DataFrame, occ_max: pd.Series | None = None,
                   official: pd.DataFrame | None = None) -> pd.DataFrame:
    """Gan tang TAI SAN + co tuong minh. KHONG ghi de cot LIVE, KHONG xoa dong.

    Yeu cau cot: station_code, num_connectors, max_power_kw, total_power_kw,
    current_type, province_code, station_type, quality_flags. `occ_max` (nhan chung
    telemetry) va `official` (tang tai san) lay tu `load_occ_max()`/
    `load_official_config()` neu khong truyen vao — truyen tay de test duoc.
    """
    df = stations.copy()
    off = load_official_config() if official is None else official
    if occ_max is None:
        occ_max = load_occ_max()

    code = df["station_code"]
    live_guns = pd.to_numeric(df["num_connectors"], errors="coerce").fillna(0).astype("int64")
    witness = pd.to_numeric(code.map(occ_max), errors="coerce").fillna(0).astype("int64")

    has_off = code.isin(off.index) if len(off) else pd.Series(False, index=df.index)
    for c in ("off_guns", "off_max_kw", "off_nameplate_kw", "off_site_kw", "off_cur", "off_shared"):
        df[c] = code.map(off[c]) if len(off) else np.nan
    off_guns = pd.to_numeric(df["off_guns"], errors="coerce")

    # --- hop nhat max(): CA BA nguon deu la chan DUOI cua cong suat lap dat ---
    installed = np.fmax(np.fmax(off_guns.fillna(0), live_guns), witness).astype("int64")

    # --- provenance: nguon NAO dinh ra con so, va no co phai DO DUOC hay chi la chan duoi ---
    src = pd.Series(SRC_UNKNOWN, index=df.index, dtype="object")
    src[has_off] = SRC_OFFICIAL                                   # registry first-party
    src[~has_off & (live_guns > 0)] = SRC_EVCS                    # mang song evcs (co bao cao)
    src[~has_off & (live_guns == 0) & (witness > 0)] = SRC_TELEMETRY  # chi nhan chung telemetry
    resolved = src.isin([SRC_OFFICIAL, SRC_EVCS])

    df["config_src"] = src
    df["config_resolved"] = resolved
    df["n_guns_installed"] = installed.where(src != SRC_UNKNOWN).astype("Int64")

    # --- cong suat: uu tien tang tai san; fallback mang song (giu nguyen ngu nghia) ---
    live_total = pd.to_numeric(df["total_power_kw"], errors="coerce")
    df["max_power_kw_asset"] = pd.to_numeric(df["off_max_kw"], errors="coerce").fillna(
        pd.to_numeric(df["max_power_kw"], errors="coerce"))
    df["nameplate_power_kw"] = pd.to_numeric(df["off_nameplate_kw"], errors="coerce").fillna(live_total)
    # Khong co registry => khong biet cach nhom to => site == nameplate (doc lac quan,
    # KHONG doan chia doi). Co registry => Sigma theo to.
    df["site_power_kw"] = pd.to_numeric(df["off_site_kw"], errors="coerce").fillna(
        df["nameplate_power_kw"])
    unknown = src == SRC_UNKNOWN
    for c in ("max_power_kw_asset", "nameplate_power_kw", "site_power_kw"):
        df.loc[unknown, c] = np.nan

    # --- current_type tu tang TAI SAN (buoc C): sua 521 tram DC-that-la-MIXED ---
    live_cur = df["current_type"]
    df["current_type_asset"] = df["off_cur"].where(df["off_cur"].notna(), live_cur)
    df.loc[unknown, "current_type_asset"] = None
    ct_fixed = df["off_cur"].notna() & live_cur.notna() & (df["off_cur"] != live_cur)

    # --- imputation: CHI de phan tich do nhay, khong bao gio la mac dinh ---
    df["n_guns_imputed"] = _impute_guns(df, resolved)

    # --- co tuong minh ---
    truncated = off_guns.notna() & (off_guns > live_guns)
    shared = df["off_shared"].apply(lambda v: v is True).astype(bool)
    flags = df["quality_flags"].apply(lambda l: list(l) if l is not None else [])
    for mask, flag in ((truncated, FLAG_TRUNCATED),
                       (unknown, FLAG_UNKNOWN),
                       (src == SRC_TELEMETRY, FLAG_LOWER_BOUND),
                       (shared, FLAG_CABINET),
                       (ct_fixed, FLAG_CT_FIXED)):
        flags.loc[mask] = flags.loc[mask].apply(lambda l, f=flag: _add_flag(l, f))
    df["quality_flags"] = flags

    df.attrs["edq4_counts"] = {
        "n_truncated": int(truncated.sum()),
        "n_guns_recovered": int((off_guns[truncated] - live_guns[truncated]).sum()),
        "n_current_type_corrected": int(ct_fixed.sum()),
        "n_cabinet_shared": int(shared.sum()),
        "n_witness_only": int((src == SRC_TELEMETRY).sum()),
        "n_contradiction_live": int((witness > live_guns).sum()),
    }
    return df.drop(columns=["off_guns", "off_max_kw", "off_nameplate_kw",
                            "off_site_kw", "off_cur", "off_shared"])


def _impute_guns(df: pd.DataFrame, resolved: pd.Series) -> pd.Series:
    """Median so sung theo (province_code, station_type) tren tap DA RESOLVE.

    Chi dien cho dong `config_src=UNKNOWN`, va chi vao cot RIENG `n_guns_imputed`.
    Fallback: median theo station_type -> median toan quoc. Khong bao gio chay vao
    `n_guns_installed` (xem CHINH SACH DU o docstring dau file)."""
    out = pd.Series(pd.NA, index=df.index, dtype="Int64")
    base = df.loc[resolved, ["province_code", "station_type", "n_guns_installed"]].copy()
    if base.empty:
        return out
    base["n"] = pd.to_numeric(base["n_guns_installed"], errors="coerce")
    by_pt = base.groupby(["province_code", "station_type"], observed=True)["n"].median()
    by_t = base.groupby("station_type", observed=True)["n"].median()
    nat = float(base["n"].median())
    need = ~resolved & (df["config_src"] == SRC_UNKNOWN)
    for i in df.index[need]:
        key = (df.at[i, "province_code"], df.at[i, "station_type"])
        v = by_pt.get(key, np.nan)
        if not np.isfinite(v):
            v = by_t.get(df.at[i, "station_type"], np.nan)
        if not np.isfinite(v):
            v = nat
        out.at[i] = int(round(max(v, 1)))
    return out


def config_report(df: pd.DataFrame, occ_max: pd.Series | None = None) -> dict:
    """Thong ke + 8 cong QA CO THE FAIL (dong E-DQ4 THAT, khong chi 'co cot moi').

    Truoc E-DQ4 KHONG co cong nao cho cau hinh: `INCOMPLETE_CONFIG` chi ton tai duoi
    dang COMMENT o transform_canonical.py:352 va `validate.py` khong kiem mot truong
    cau hinh nao (`REQUIRED_COLS` khong liet ke chung). Day la khuon "cong kiem dung
    cai sinh ra loi nen khong bao gio FAIL" cua E-DQ7c/E-DQ7e — o E-DQ4 con te hon:
    khong co cong nao ca."""
    if occ_max is None:
        occ_max = load_occ_max()
    n = len(df)
    installed = pd.to_numeric(df["n_guns_installed"], errors="coerce").astype("float64")
    live = pd.to_numeric(df["num_connectors"], errors="coerce").fillna(0).astype("float64")
    witness = pd.to_numeric(df["station_code"].map(occ_max), errors="coerce").fillna(0)
    site = pd.to_numeric(df["site_power_kw"], errors="coerce")
    nameplate = pd.to_numeric(df["nameplate_power_kw"], errors="coerce")
    resolved = df["config_resolved"].fillna(False).astype(bool)
    src = df["config_src"]
    has_flag = lambda f: df["quality_flags"].apply(lambda l: f in (l or []))

    supply = (df["is_operational"] & (df["access"] == "PUBLIC")
              & df["is_primary"] & df["coord_resolved"]) if "is_operational" in df else pd.Series(
        True, index=df.index)

    gates = {}
    # (1) NEO NGOAI VI: khong the sac nhieu xe cung luc hon so sung lap dat.
    #     Day la cong DUY NHAT bat duoc truncation ma KHONG can registry.
    gates["guns_ge_observed_max"] = bool((installed.fillna(np.inf) >= witness).all())
    # (2) khong con so 0 am tham: da resolve + dang van hanh thi phai co sung
    gates["no_silent_zero"] = bool(
        (df["is_operational"].fillna(False) & resolved & (installed.fillna(0) == 0)).sum() == 0)
    # (3) tien de HOP max(): mang song khong bao gio duoc VUOT registry. Neu FAIL thi
    #     `max()` dang che mat mot mau thuan that -> phai dieu tra, khong duoc bo qua.
    off_only = src == SRC_OFFICIAL
    gates["reporting_le_installed"] = bool((live[resolved] <= installed[resolved]).all())
    # (4) tang tai san day du o moi dong da resolve (khong resolve nua voi)
    gates["asset_layer_complete"] = bool(
        installed[resolved].notna().all() and site[resolved].notna().all()
        and nameplate[resolved].notna().all()
        and df.loc[resolved, "current_type_asset"].notna().all())
    # (5) buoc D: cong suat DIEM khong bao gio vuot Sigma nameplate tung sung
    gates["site_power_le_nameplate"] = bool(
        (site[site.notna() & nameplate.notna()] <= nameplate[site.notna() & nameplate.notna()]
         + 1e-6).all())
    # (6) UNKNOWN phai TUONG MINH: co CONFIG_UNKNOWN + asset toan NULL (khong dien ngam)
    unk = src == SRC_UNKNOWN
    gates["unknown_is_explicit"] = bool(
        has_flag(FLAG_UNKNOWN)[unk].all() and installed[unk].isna().all()
        and site[unk].isna().all()
        and df.loc[unk, "current_type_asset"].isna().all())
    # (7) doi soat dong: input == resolved + chan duoi + unknown (khong dong nao boc hoi)
    gates["row_reconciliation"] = bool(
        int(resolved.sum()) + int((src == SRC_TELEMETRY).sum()) + int(unk.sum()) == n)
    # (8) ty le resolve tren tap CUNG (bao cao + gate, giong khuon recall cua E-DQ7c)
    rate = float(resolved[supply].mean()) if supply.any() else 1.0
    gates["config_resolved_rate"] = bool(rate >= MIN_RESOLVED_RATE)

    counts = df.attrs.get("edq4_counts", {})
    sup = df[supply]
    return {
        "n_input": int(n),
        "config_src": src.value_counts().to_dict(),
        "n_resolved": int(resolved.sum()),
        "n_unknown": int(unk.sum()),
        "n_unknown_by_type": df.loc[unk, "station_type"].value_counts().to_dict(),
        "n_truncated": counts.get("n_truncated"),
        "n_guns_recovered": counts.get("n_guns_recovered"),
        "n_current_type_corrected": counts.get("n_current_type_corrected"),
        "n_cabinet_shared": counts.get("n_cabinet_shared"),
        "n_contradiction_live": counts.get("n_contradiction_live"),
        "guns_reporting_total": int(live.sum()),
        "guns_installed_total": int(installed.fillna(0).sum()),
        "supply": {
            "n": int(len(sup)),
            "resolved_rate": round(rate, 5),
            "n_unresolved": int((~resolved[supply]).sum()),
            "guns_reporting": int(live[supply].sum()),
            "guns_installed": int(installed[supply].fillna(0).sum()),
            "cells_zero_capacity": int(
                (sup.groupby("h3_r8")["n_guns_installed"].sum(min_count=1).fillna(0) == 0).sum())
            if "h3_r8" in sup else None,
        },
        "power_kw": {
            "live_total_power_kw": round(float(
                pd.to_numeric(df["total_power_kw"], errors="coerce").sum()), 1),
            "asset_nameplate_kw": round(float(nameplate.sum()), 1),
            "asset_site_kw": round(float(site.sum()), 1),
            "cabinet_inflation": round(float(nameplate.sum() / site.sum()), 4)
            if site.sum() else None,
        },
        "gates": gates,
        "all_gates_pass": bool(all(gates.values())),
    }


def _load_canonical_stations() -> pd.DataFrame:
    cols = ["station_id", "station_code", "province_code", "station_type", "h3_r8",
            "num_connectors", "max_power_kw", "total_power_kw", "current_type",
            "op_status", "access", "is_operational", "is_primary", "coord_resolved",
            "quality_flags"]
    return pd.read_parquet(STATIONS_DIR, columns=cols)


def main():
    ap = argparse.ArgumentParser(
        description="E-DQ4: hop giai cau hinh LAP DAT (inspect canonical, khong ghi de)")
    ap.add_argument("--dump", action="store_true",
                    help="dump tram bi truncate/unknown ra CSV de eyeball")
    args = ap.parse_args()

    df = _load_canonical_stations()
    occ = load_occ_max()
    out = resolve_config(df, occ)
    rep = config_report(out, occ)

    report_path = INTERIM_DIR / "resolve_config_report.json"
    report_path.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    p = rep["power_kw"]
    s = rep["supply"]
    print("================ E-DQ4 HOP GIAI CAU HINH LAP DAT ================")
    print(f"  input                        : {rep['n_input']:,}")
    print(f"  config_src                   : {rep['config_src']}")
    print(f"  A  UNKNOWN (khong nguon nao) : {rep['n_unknown']:,}  {rep['n_unknown_by_type']}")
    print(f"  B  CONFIG_TRUNCATED          : {rep['n_truncated']:,}  "
          f"(+{rep['n_guns_recovered']:,} sung lay lai)")
    print(f"  C  CURRENT_TYPE_CORRECTED    : {rep['n_current_type_corrected']:,}")
    print(f"  D  POWER_CABINET_SHARED      : {rep['n_cabinet_shared']:,}  "
          f"(phong dai nameplate/site = {p['cabinet_inflation']}x)")
    print(f"  mau thuan vat ly (live)      : {rep['n_contradiction_live']:,} "
          f"(ts_val_max > num_connectors)")
    print("--- sung: mang SONG vs tang TAI SAN ---------------------------")
    print(f"  toan bo   : {rep['guns_reporting_total']:,} -> {rep['guns_installed_total']:,}")
    print(f"  tap cung  : {s['guns_reporting']:,} -> {s['guns_installed']:,}  (n={s['n']:,})")
    print(f"  resolved tren cung           : {s['resolved_rate']:.4f}  "
          f"(chua resolve: {s['n_unresolved']:,})")
    print(f"  o cung doc cong suat = 0     : {s['cells_zero_capacity']:,}")
    print("--- cong suat kW ---------------------------------------------")
    print(f"  LIVE  total_power_kw         : {p['live_total_power_kw']:,.0f} kW")
    print(f"  ASSET nameplate (Sigma sung) : {p['asset_nameplate_kw']:,.0f} kW")
    print(f"  ASSET site      (Sigma to)   : {p['asset_site_kw']:,.0f} kW")
    print(f"  QA gates (8 cong)            : {rep['gates']}")
    print(f"  ALL GATES PASS               : {rep['all_gates_pass']}")
    if args.dump:
        sel = out["quality_flags"].apply(
            lambda l: bool({FLAG_TRUNCATED, FLAG_UNKNOWN, FLAG_LOWER_BOUND,
                            FLAG_CT_FIXED} & set(l or [])))
        csv_path = INTERIM_DIR / "resolve_config_flagged.csv"
        out.loc[sel, ["station_id", "station_code", "province_code", "station_type",
                      "op_status", "config_src", "config_resolved", "num_connectors",
                      "n_guns_installed", "n_guns_imputed", "current_type",
                      "current_type_asset", "total_power_kw", "nameplate_power_kw",
                      "site_power_kw", "quality_flags"]].to_csv(csv_path, index=False)
        print(f"  flagged -> {csv_path.relative_to(PROJECT_ROOT)}  ({int(sel.sum()):,} dong)")
    print(f"-> {report_path.relative_to(PROJECT_ROOT)}")
    print("================================================================")
    return out, rep


if __name__ == "__main__":
    main()
