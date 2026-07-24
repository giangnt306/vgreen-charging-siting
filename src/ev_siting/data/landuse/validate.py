#!/usr/bin/env python3
"""validate.py — Cổng QA cho tầng land-use / buildable (P5).

Kiểm trên `buildable_h3.parquet` rồi ghi `landuse_quality_report.json`:
  - buildable là bool, không null; h3_r8 unique.
  - built_up_frac / frac_water trong [0, 1].
  - có ít nhất 1 ô buildable (nếu 0 -> ngưỡng chắc chắn sai).
  - WARN nếu >70% ô pop>0 bị loại (BUILT_UP_MIN quá chặt — cần hiệu chỉnh).

Thoát != 0 nếu có FAIL (chặn pipeline). WARN không chặn.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.landuse.validate
"""
import json
import sys

import pandas as pd

from .paths import BUILDABLE_H3, QUALITY_REPORT, ensure_dirs


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def run():
    ensure_dirs()
    report = {"checks": [], "stats": {}}
    all_ok = True

    if not BUILDABLE_H3.exists():
        _check(report, "buildable_exists", False, str(BUILDABLE_H3))
        with open(QUALITY_REPORT, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    df = pd.read_parquet(BUILDABLE_H3)
    report["stats"]["n_cells"] = int(len(df))
    report["stats"]["n_buildable"] = int(df["buildable"].sum())
    report["stats"]["pct_buildable"] = round(float(df["buildable"].mean()), 4)

    all_ok &= _check(report, "buildable_bool_no_null",
                     bool(df["buildable"].notna().all() and df["buildable"].dtype == bool))
    dup = df.duplicated(["h3_r8"]).sum()
    all_ok &= _check(report, "h3_unique", dup == 0, f"{dup} trùng")
    all_ok &= _check(report, "fracs_in_range",
                     bool(df["built_up_frac"].between(0, 1).all()
                          and df["frac_water"].between(0, 1).all()))
    all_ok &= _check(report, "has_buildable", int(df["buildable"].sum()) > 0,
                     f"{int(df['buildable'].sum())} ô buildable")

    # cảnh báo hiệu chỉnh ngưỡng
    pop_mask = df["pop"] > 0
    if pop_mask.any():
        excl_ratio = float((pop_mask & ~df["buildable"]).sum() / pop_mask.sum())
        report["stats"]["pop_excluded_ratio"] = round(excl_ratio, 4)
        all_ok &= _check(report, "builtup_threshold_sane", excl_ratio <= 0.70,
                         f"{excl_ratio:.0%} ô pop>0 bị loại (>70% -> BUILT_UP_MIN quá chặt)",
                         fatal=False)

    report["overall"] = "PASS" if all_ok else "FAIL"
    with open(QUALITY_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n[{report['overall']}] -> {QUALITY_REPORT}")
    print("stats:", json.dumps(report["stats"], ensure_ascii=False))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    run()
