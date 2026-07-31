#!/usr/bin/env python3
"""export_supply.py — sinh lai `clean_supply.csv` + `excluded.csv` tu canonical.

VI SAO CAN FILE NAY. Hai CSV do da ton tai tu truoc nhung KHONG co module nao trong
`src/` sinh ra chung (grep `clean_supply src/` -> 0 hit). Hau qua do duoc, khong phai
gia thuyet: `dataset-inventory.md` liet ke `clean_supply.csv` la "cung sach cuoi cung
— input truc tiep cho MCLP/coverage", nhung vi no khong chay lai theo pipeline, no
dung yen o anh chup 28/07 trong khi canonical da di tiep. Ngay 30/07 no lech dung 16
dong = 16 tram `COORD_OUTSIDE_ADMIN` ma E-DQ3 loai (toa do khong roi vao bat ky don vi
hanh chinh nao). Bat ky consumer nao con doc file cu la dang nap 16 toa do SAI vao
MCLP/coverage.

NGUYEN TAC. File nay KHONG dinh nghia lai tap cung. Nguon chan ly duy nhat van la
`canonical/stations` + cong thuc cung; module chi EXPORT no ra CSV cho nguoi doc / cong
cu ngoai (Excel, QGIS). Vi vay:
  - 0 cot moi, 0 phep loc rieng: cong thuc o SUPPLY_FILTER trung voi validate/inventory.
  - Moi dong bi loai phai co DUNG MOT ly do, va tong phai doi soat het (cong ①/②).
  - Ghi kem `export_supply_report.json` de lineage tra loi duoc "file CSV nay sinh luc
    nao, tu bao nhieu dong input".

CONG THUC CUNG (T0/coverage) — giong `validate.py` va `dataset-inventory.md` §3.1:
    is_operational & access == 'PUBLIC' & is_primary & coord_resolved

THU TU LY DO LOAI (uu tien tu tren xuong; mot dong co the pham nhieu dieu kien, ta ghi
dieu kien DAU TIEN theo thu tu nay de tong khop voi ban 28/07):
    CROSS_SOURCE_DUP  (E-DQ2)  -> ban trung cheo nguon, khong phai tram vat ly rieng
    ACCESS_UNKNOWN    (P8)     -> khong biet public/private, khong dam nhan la cung
    OUT_OF_SERVICE    (P8)     -> da ngung van hanh
    COORD_PLACEHOLDER (E-DQ1)  -> toa do placeholder, `h3_r8` NULL
    COORD_OUTSIDE_ADMIN (E-DQ3)-> toa do ngoai moi don vi hanh chinh (MOI tu 30/07)
    RESTRICTED        (P8)     -> official ghi tu nhan/han che

Doi soat 30/07: 19.507 = 18.999 cung + 508 loai
    (329 dup + 63 access_unknown + 42 out_of_service + 38 placeholder
     + 16 outside_admin + 20 restricted)
Ban 28/07 co 492 dong loai; chenh dung 16 dong `COORD_OUTSIDE_ADMIN` cua E-DQ3.

DOI SO VOI BAN 28/07 (da diff tung o tren 18.999 dong chung, chi 1 cot lech):
`connector_types` cua ban cu ghi bang `str(numpy.ndarray)` nen ra `['A' 'B']` — THIEU
DAU PHAY, khong `ast.literal_eval` duoc, va chi lo ra o 3.747 dong nhieu loai (dong
mot loai thi hai dang trung nhau nen loi an rat lau). Nay ghi `str(list)` -> `['A', 'B']`.
Doc gia string-split theo dau cach se can sua; buoc nay la CO Y.

Chay:
    PYTHONPATH=src python -m ev_siting.data.evcs.export_supply          # ghi CSV
    PYTHONPATH=src python -m ev_siting.data.evcs.export_supply --check  # chi cham cong
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .paths import CONNECTORS_DIR, INTERIM_DIR, PROJECT_ROOT, STATIONS_DIR
from .connector_rollup import LIVE_COLS, attach as attach_live

CLEAN_SUPPLY_CSV = INTERIM_DIR / "clean_supply.csv"
EXCLUDED_CSV = INTERIM_DIR / "excluded.csv"
REPORT_JSON = INTERIM_DIR / "export_supply_report.json"

# Cot xuat ra, dung thu tu cua ban 28/07 (consumer ngoai co the dang doc theo vi tri).
SUPPLY_COLS = [
    "station_id", "station_code", "name", "operator", "province_code",
    "lat", "lng", "h3_r8", "current_type", "max_power_kw",
    "num_connectors", "connector_types", "vehicle_class", "op_status",
]
EXCLUDED_COLS = [
    "reason", "station_id", "station_code", "name", "province_code", "lat_raw", "lng_raw",
]

# 31/07: 4 cot LIVE trong SUPPLY_COLS khong con nam o `stations` — chung duoc suy tu
# bang `connectors` (nguon chan ly duy nhat, xem connector_rollup.py). CSV xuat ra
# GIU NGUYEN thu tu cot cua ban 28/07: chi doi CHO LAY, khong doi hop dong doc.
_LIVE_IN_SUPPLY = [c for c in SUPPLY_COLS if c in LIVE_COLS]

# Cot can doc TU `stations` (da tru phan suy tu connectors).
_READ_COLS = sorted((set(SUPPLY_COLS + EXCLUDED_COLS) - {"reason"} - set(_LIVE_IN_SUPPLY)) | {
    "access", "is_operational", "is_primary", "coord_resolved", "quality_flags",
})

# Nhan ly do: giu nguyen van ban 28/07 (khong dau, de doc trong Excel mac dinh Windows).
REASON_LABELS = {
    "CROSS_SOURCE_DUP": "CROSS_SOURCE_DUP (ban trung cheo nguon)",
    "ACCESS_UNKNOWN": "ACCESS_UNKNOWN (khong ro truy cap)",
    "OUT_OF_SERVICE": "OUT_OF_SERVICE (da ngung van hanh)",
    "COORD_PLACEHOLDER": "COORD_PLACEHOLDER (toa do sai)",
    "COORD_OUTSIDE_ADMIN": "COORD_OUTSIDE_ADMIN (toa do ngoai moi don vi hanh chinh)",
    "RESTRICTED": "RESTRICTED (official: tu nhan han che)",
}


def _has_flag(flags, flag: str) -> bool:
    if flags is None or (np.isscalar(flags) and pd.isna(flags)):
        return False
    return flag in list(flags)


def supply_mask(df: pd.DataFrame) -> pd.Series:
    """Cong thuc cung T0/coverage. Doi day = doi dinh nghia cung -> phai doi ca doc."""
    return (
        df["is_operational"].fillna(False).astype(bool)
        & df["access"].eq("PUBLIC")
        & df["is_primary"].fillna(False).astype(bool)
        & df["coord_resolved"].fillna(False).astype(bool)
    )


def exclusion_reason(df: pd.DataFrame) -> pd.Series:
    """Ly do DAU TIEN theo thu tu uu tien, cho moi dong KHONG thuoc tap cung.

    Tra ve Series cung index voi `df`; NA cho dong thuoc tap cung. Ket qua la khoa
    ngan (`CROSS_SOURCE_DUP`, ...), chua qua REASON_LABELS.
    """
    flags = df["quality_flags"]
    outside = flags.apply(_has_flag, flag="COORD_OUTSIDE_ADMIN")
    no_coord = ~df["coord_resolved"].fillna(False).astype(bool)

    rules = [
        ("CROSS_SOURCE_DUP", ~df["is_primary"].fillna(False).astype(bool)),
        ("ACCESS_UNKNOWN", df["access"].eq("UNKNOWN")),
        ("OUT_OF_SERVICE", ~df["is_operational"].fillna(False).astype(bool)),
        # E-DQ1 vs E-DQ3: ca hai deu lam `coord_resolved=False`, phan biet bang co.
        ("COORD_OUTSIDE_ADMIN", no_coord & outside),
        ("COORD_PLACEHOLDER", no_coord & ~outside),
        ("RESTRICTED", df["access"].eq("RESTRICTED")),
    ]

    reason = pd.Series(pd.NA, index=df.index, dtype=object)
    todo = ~supply_mask(df)
    for key, cond in rules:
        hit = todo & cond & reason.isna()
        reason[hit] = key
    return reason


def build(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """canonical stations -> (clean_supply, excluded), da sap cot va sap thu tu dong."""
    keep = supply_mask(df)
    reason = exclusion_reason(df)

    supply = df.loc[keep, SUPPLY_COLS].copy()
    # `connector_types` la list trong parquet; CSV giu dang repr de khop ban 28/07.
    supply["connector_types"] = supply["connector_types"].apply(
        lambda v: str(list(v)) if v is not None and not np.isscalar(v) else "[]")
    supply = supply.sort_values("station_id", kind="stable").reset_index(drop=True)

    excluded = df.loc[~keep].copy()
    excluded["reason"] = reason[~keep].map(REASON_LABELS)
    # Sap theo thu tu uu tien ly do roi den station_id: diff giua 2 lan chay doc duoc.
    order = {label: i for i, label in enumerate(REASON_LABELS.values())}
    excluded = (excluded.assign(_ord=excluded["reason"].map(order))
                .sort_values(["_ord", "station_id"], kind="stable")
                .loc[:, EXCLUDED_COLS]
                .reset_index(drop=True))
    return supply, excluded


def report(df: pd.DataFrame, supply: pd.DataFrame, excluded: pd.DataFrame) -> dict:
    """Bao cao + 6 cong QA. Moi cong CO THE FAIL (xem tests/test_export_supply.py)."""
    n_input = len(df)
    by_reason = excluded["reason"].value_counts(dropna=False).to_dict()

    gates = {
        # ① doi soat: input = output + loai. Cong quan trong nhat cua module.
        "reconciles_input": n_input == len(supply) + len(excluded),
        # ② moi dong loai co DUNG MOT ly do (khong NA, khong rong).
        "every_excluded_has_reason": bool(excluded["reason"].notna().all())
                                     and int(excluded["reason"].isna().sum()) == 0,
        # ③ ly do chi lay tu tu dien -> khong sinh nhan la khi them co moi.
        "reasons_are_known": set(by_reason) <= set(REASON_LABELS.values()),
        # ④ PK unique o ca hai file.
        "pk_unique": bool(supply["station_id"].is_unique and excluded["station_id"].is_unique),
        # ⑤ khong dong nao vua o cung vua bi loai (hai tap roi nhau).
        "sets_are_disjoint": not set(supply["station_id"]) & set(excluded["station_id"]),
        # ⑥ moi dong cung co toa do + h3 dung -> khong bao gio xuat NULL geometry.
        "supply_has_geometry": bool(
            supply[["lat", "lng"]].notna().all().all() and supply["h3_r8"].notna().all()),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(STATIONS_DIR.relative_to(PROJECT_ROOT)),
        "supply_filter": "is_operational & access=='PUBLIC' & is_primary & coord_resolved",
        "n_input": n_input,
        "n_supply": len(supply),
        "n_supply_cells": int(supply["h3_r8"].nunique()),
        "n_excluded": len(excluded),
        "excluded_by_reason": by_reason,
        # Ghi ro dinh dang de consumer khong phai doan (ban 28/07 ghi thieu dau phay).
        "connector_types_format": "python list repr, e.g. ['DC-30kW', 'AC-3.5kW']",
        "gates": gates,
        "all_gates_pass": all(gates.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sinh lai clean_supply.csv + excluded.csv tu canonical/stations")
    ap.add_argument("--check", action="store_true",
                    help="chi cham cong + in bao cao, KHONG ghi file")
    args = ap.parse_args()

    df = pd.read_parquet(STATIONS_DIR, columns=_READ_COLS)
    # gan lai tang LIVE tu `connectors` (khong con ban sao o `stations`)
    df = attach_live(df, pd.read_parquet(CONNECTORS_DIR, columns=[
        "station_id", "power_kw", "current_type", "connector_label", "count_total",
    ]), cols=_LIVE_IN_SUPPLY)
    supply, excluded = build(df)
    rep = report(df, supply, excluded)

    if not args.check:
        # utf-8-sig: hai file nay dung cho nguoi doc / Excel, giu BOM nhu ban 28/07.
        supply.to_csv(CLEAN_SUPPLY_CSV, index=False, encoding="utf-8-sig")
        excluded.to_csv(EXCLUDED_CSV, index=False, encoding="utf-8-sig")
        REPORT_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print("================ EXPORT CUNG SACH (canonical -> CSV) ============")
    print(f"  input canonical/stations : {rep['n_input']:,}")
    print(f"  cung (T0/coverage)       : {rep['n_supply']:,}  tren {rep['n_supply_cells']:,} o H3")
    print(f"  loai                     : {rep['n_excluded']:,}")
    for label, n in rep["excluded_by_reason"].items():
        print(f"      {n:>5,}  {label}")
    print(f"  doi soat                 : {rep['n_supply']:,} + {rep['n_excluded']:,} "
          f"= {rep['n_supply'] + rep['n_excluded']:,}")
    print(f"  QA gates (6 cong)        : {rep['gates']}")
    print(f"  ALL GATES PASS           : {rep['all_gates_pass']}")
    if args.check:
        print("  --check: khong ghi file")
    else:
        for p in (CLEAN_SUPPLY_CSV, EXCLUDED_CSV, REPORT_JSON):
            print(f"-> {p.relative_to(PROJECT_ROOT)}")
    print("================================================================")
    return 0 if rep["all_gates_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
