#!/usr/bin/env python3
"""build_covered0.py — Baseline coverage của mạng trạm hiện có (`covered0`).

`covered0` = tập **trạm hiện có ĐANG hoạt động & công cộng** — điểm xuất phát
(subscript 0) cho bài toán tối ưu: MCLP đo coverage tăng thêm *trên nền* baseline
này, và so sánh "mạng hiện tại vs. vị trí model đề xuất" (problem-analysis §4).

Định nghĩa baseline (F5 — đồng bộ P8/E-DQ2, cùng cột canonical với anchor T0):
  `is_operational & access == "PUBLIC" & is_primary & sạch-toạ-độ`
  — đúng công thức "cung công khai khả dụng" của known-issues P8/E-DQ2.

  1. `is_operational` (op_status resolve official-first, P8): chỉ loại `OUT_OF_SERVICE`.
     `MAINTENANCE` **giữ** (quyết định P8: hạ tầng bảo trì vẫn là cung brownfield đa
     năm) — cột `op_status` được export để model tự loại qua cờ nếu muốn. Sensitivity
     `covered0_operational.*` = baseline nhưng chỉ giữ `op_status == "OPERATIONAL"`.
  2. `access == "PUBLIC"` (strict): `RESTRICTED` lẫn `UNKNOWN` không vào baseline
     (không xác nhận được là cung công khai). Lưu ý khác T0 có chủ đích: T0 giữ
     access-UNKNOWN làm anchor (chỉ cần không-RESTRICTED), baseline thì bảo thủ.
  3. `is_primary` (E-DQ2): bản trùng chéo nguồn không được phủ 2 lần.
  4. Sạch toạ độ (F4, tập cờ dùng chung `features.paths.DIRTY_COORD_FLAGS`):
     placeholder coords tạo **coverage ảo** — cùng lý do với gate `coord_resolved` ở T0.

Mọi loại trừ được **đếm + ghi log** theo lý do (nguyên tắc "flag, không xoá ngầm" §7 #5).

**E-DQ4 (30/07)** — export kèm tầng **TÀI SẢN** (`n_guns_installed`/`site_power_kw`/
`current_type_asset`, xem `resolve_config.py`) BÊN CẠNH tầng trạng thái sống
(`num_connectors`/`total_power_kw`), và áp CHÍNH SÁCH DƯ: mọi con số CÓ TRỌNG SỐ
CÔNG SUẤT chỉ cộng trên `config_resolved`, phần dư (`CONFIG_UNKNOWN`) **được công bố
tường minh** trong report chứ không đọng thành mẫu số im lặng (khuôn E-DQ8c).

(Món nợ khai ở bản trước — bộ lọc đọc `status`/`is_public` THÔ + cờ ma `DUP_COORD` —
đã đóng bằng **F5**: baseline dùng đúng cột canonical P8/E-DQ2 + tập cờ F4, nên kế
toán E-DQ4 bên dưới chạy trên đúng tập cung canonical.)

Output: data/processed/covered0.{parquet,geojson} (+ covered0_operational.* — sensitivity)
Chạy:
    PYTHONPATH=src python -m ev_siting.features.build_covered0 --city hanoi
    PYTHONPATH=src python -m ev_siting.features.build_covered0 --national
"""
import argparse
import json

import numpy as np
import pandas as pd

from ev_siting.aoi import add_aoi_args, aoi_from_args
from ev_siting.data.evcs.paths import STATIONS_DIR
from .paths import (COVERED0_GEOJSON, COVERED0_OPERATIONAL_GEOJSON,
                    COVERED0_OPERATIONAL_SITES, COVERED0_SITES, ensure_dirs,
                    has_dirty_coord)

#: cột export (điểm trạm + thuộc tính không gian + trạng thái P8 đã resolve).
#: Hai tầng cấu hình đi CẠNH nhau (E-DQ4): LIVE = đang báo cáo, ASSET = lắp đặt.
_OUT_COLS = ["station_id", "lat", "lng", "h3_r8", "province_code", "op_status",
             "access", "operator", "current_type", "max_power_kw",
             "total_power_kw", "num_connectors", "verified",
             # E-DQ4 — tầng TÀI SẢN + provenance cấu hình
             "n_guns_installed", "site_power_kw", "nameplate_power_kw",
             "current_type_asset", "config_src", "config_resolved"]

#: cờ E-DQ4 đánh dấu dòng KHÔNG có cấu hình lắp đặt từ bất kỳ nguồn nào.
_CONFIG_UNKNOWN_FLAG = "CONFIG_UNKNOWN"


def _baseline_mask(df):
    """Mask baseline + bộ đếm lý do loại (tách thuần để test được — F16).

    Trả về (mask, reasons): mask = is_operational & PUBLIC & is_primary & sạch toạ độ.
    Các counter độc lập (1 dòng có thể dính nhiều lý do)."""
    operational = df["is_operational"].fillna(False).astype(bool)
    public = df["access"].eq("PUBLIC")
    primary = df["is_primary"].fillna(False).astype(bool)
    clean = ~df["quality_flags"].apply(has_dirty_coord)

    reasons = {
        "not_operational": int((~operational).sum()),
        "access_restricted": int(df["access"].eq("RESTRICTED").sum()),
        "access_unknown": int((~df["access"].isin(["PUBLIC", "RESTRICTED"])).sum()),
        "cross_source_dup": int((~primary).sum()),
        "dirty_coord": int((~clean).sum()),
    }
    return operational & public & primary & clean, reasons


def _operational_only_mask(df):
    """Baseline sensitivity: chỉ trạm PUBLIC đang OPERATIONAL ngay lúc snapshot.

    Baseline chuẩn vẫn giữ MAINTENANCE theo chính sách quy hoạch brownfield; tập này
    cho thấy mức coverage hiện tại khi không coi hạ tầng bảo trì là đang phục vụ."""
    baseline, _ = _baseline_mask(df)
    return baseline & df["op_status"].eq("OPERATIONAL")


def _capacity_accounting(out: pd.DataFrame) -> dict:
    """E-DQ4 — kế toán công suất trên tầng TÀI SẢN, công bố phần DƯ tường minh.

    Mọi tổng CÓ TRỌNG SỐ CÔNG SUẤT chỉ cộng trên `config_resolved`; số trạm/ô bị loại
    vì `CONFIG_UNKNOWN` được ghi ra để không đọng thành mẫu số im lặng (khuôn E-DQ8c).
    `guns_reporting` giữ lại để đo đúng khoảng cách LIVE↔ASSET, không phải để dùng."""
    if "config_resolved" not in out:
        return {}
    ok = out["config_resolved"].fillna(False).astype(bool)
    guns = pd.to_numeric(out["n_guns_installed"], errors="coerce")
    site = pd.to_numeric(out["site_power_kw"], errors="coerce")
    live = pd.to_numeric(out["num_connectors"], errors="coerce").fillna(0)
    unresolved = out.loc[~ok]
    return {
        "n_config_resolved": int(ok.sum()),
        "n_config_unknown_excluded": int((~ok).sum()),
        "config_src": out["config_src"].value_counts().to_dict(),
        # chỉ cộng trên phần đã resolve
        "guns_installed": int(guns[ok].fillna(0).sum()),
        "site_power_kw": round(float(site[ok].fillna(0).sum()), 1),
        # tầng LIVE, để đo khoảng cách — KHÔNG dùng làm công suất
        "guns_reporting": int(live.sum()),
        # phần dư: bao nhiêu ô mất TOÀN BỘ công suất vì không resolve được
        "cells_all_unknown": int(
            out.groupby("h3_r8")["config_resolved"].apply(
                lambda s: not s.fillna(False).any()).sum()) if "h3_r8" in out else None,
        "unresolved_station_ids": sorted(unresolved["station_id"].astype(str))[:50],
    }


def build(aoi, strict=True):
    """Lọc trạm operational+public+primary trong AOI -> covered0.{parquet,geojson}."""
    ensure_dirs()
    print(f"[covered0] {aoi}")
    cols = _OUT_COLS + ["is_operational", "is_primary", "quality_flags"]
    df = pd.read_parquet(STATIONS_DIR, columns=cols)
    n_total = len(df)

    # --- lọc theo AOI (đồng bộ candidate_sites) ---
    in_aoi = np.asarray(aoi.contains(df["lat"].to_numpy(), df["lng"].to_numpy()))
    df = df[in_aoi].copy()
    n_aoi = len(df)

    # --- bộ lọc baseline F5 + bộ đếm lý do loại (flag, không xoá ngầm — §7 #5) ---
    mask, reasons = _baseline_mask(df)
    covered0 = df[mask].copy()
    out = covered0[_OUT_COLS].reset_index(drop=True)
    operational_out = df[_operational_only_mask(df)][_OUT_COLS].reset_index(drop=True)

    # --- report ---
    report = {
        "aoi": aoi.to_dict(),
        "baseline_def": "is_operational & access==PUBLIC & is_primary & clean_coord (P8/E-DQ2/F4)",
        "n_stations_total": n_total,
        "n_stations_in_aoi": n_aoi,
        "n_covered0": len(out),
        "n_covered0_operational_only": len(operational_out),
        "dropped_by_reason": reasons,
        "op_status_breakdown": {str(k): int(v) for k, v in
                                covered0["op_status"].value_counts().items()},
        "config_capacity": _capacity_accounting(out),
    }

    out.to_parquet(COVERED0_SITES, index=False)
    operational_out.to_parquet(COVERED0_OPERATIONAL_SITES, index=False)
    _write_geojson(out, report, COVERED0_GEOJSON,
                   "covered0 — planning baseline (P8)")
    _write_geojson(operational_out, report, COVERED0_OPERATIONAL_GEOJSON,
                   "covered0_operational — current-service sensitivity (P8)")
    with open(str(COVERED0_SITES).replace(".parquet", "_report.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[covered0] trong AOI: {n_aoi}/{n_total} trạm")
    print(f"[covered0] loại: {reasons}")
    print(f"[covered0] -> {COVERED0_SITES}  ({len(out)} trạm operational+public+primary)")
    print(f"[covered0] -> {COVERED0_OPERATIONAL_SITES}  ({len(operational_out)} trạm OPERATIONAL-only)")
    print("  theo op_status:", report["op_status_breakdown"])
    cap = report["config_capacity"]
    if cap:
        print(f"  [E-DQ4] súng: ĐANG BÁO CÁO {cap['guns_reporting']:,} -> "
              f"LẮP ĐẶT {cap['guns_installed']:,}  |  công suất ĐIỂM "
              f"{cap['site_power_kw']:,.0f} kW")
        print(f"  [E-DQ4] loại khỏi kế toán công suất (CONFIG_UNKNOWN): "
              f"{cap['n_config_unknown_excluded']:,} trạm; ô mất toàn bộ công suất: "
              f"{cap['cells_all_unknown']:,}")

    # sanity: đối soát dòng (§8 bước 10) — không có dòng nào bị "bốc hơi"
    dropped = n_aoi - len(out)
    if strict and dropped < 0:
        raise SystemExit("[covered0] đối soát dòng FAIL (n_covered0 > n_aoi)")
    return out


def _write_geojson(covered0, report, path, generated_for):
    """GeoJSON điểm baseline (cùng chuẩn với candidate_sites / demand proxy)."""
    feats = []
    for r in covered0.itertuples():
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(r.lng, 6), round(r.lat, 6)]},
            "properties": {
                "station_id": r.station_id, "h3_r8": r.h3_r8, "op_status": r.op_status,
                "access": r.access, "operator": r.operator,
                "max_power_kw": None if pd.isna(r.max_power_kw) else float(r.max_power_kw),
                # E-DQ4: tầng LIVE (đang báo cáo) vs tầng ASSET (lắp đặt) đi cạnh nhau
                "num_connectors": None if pd.isna(r.num_connectors) else int(r.num_connectors),
                "n_guns_installed": None if pd.isna(r.n_guns_installed) else int(r.n_guns_installed),
                "site_power_kw": None if pd.isna(r.site_power_kw) else float(r.site_power_kw),
                "current_type_asset": r.current_type_asset,
                "config_src": r.config_src,
            },
        })
    fc = {"type": "FeatureCollection",
          "properties": {"generated_for": generated_for, "report": report},
          "features": feats}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"[covered0] -> {path}  ({len(feats)} điểm)")


def run(args=None):
    ap = argparse.ArgumentParser(
        description="Sinh covered0 — baseline coverage trạm operational+public+primary (P8/E-DQ2)")
    add_aoi_args(ap)
    a = ap.parse_args(args)
    build(aoi_from_args(a))


if __name__ == "__main__":
    run()
