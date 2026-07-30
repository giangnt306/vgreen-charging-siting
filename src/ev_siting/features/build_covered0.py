#!/usr/bin/env python3
"""build_covered0.py — Baseline coverage của mạng trạm hiện có (`covered0`).

`covered0` = tập **trạm hiện có ĐANG hoạt động & công cộng** — điểm xuất phát
(subscript 0) cho bài toán tối ưu: MCLP đo coverage tăng thêm *trên nền* baseline
này, và so sánh "mạng hiện tại vs. vị trí model đề xuất" (problem-analysis §4).

Đóng **P8** (lọc trạng thái vận hành & access private/public). Ràng buộc:
  1. Giữ trạm **active** (đang phục vụ) **và** **public**; loại phần còn lại.
  2. Export kèm thuộc tính không gian: `lat`, `lng`, `h3_r8` (lưới res 8 cho
     phân tích coverage theo ô — đồng bộ candidate_sites / demand_h3).

Định nghĩa "active" (`ACTIVE_STATUSES`):
  Cột `status` (evcs) không có giá trị "active" nguyên văn; trạng thái **vận hành**
  gồm `Available` (rảnh) và `AllBusy` (đang bận nhưng vẫn phục vụ). Với **coverage**,
  một trạm `AllBusy` vẫn phủ vùng của nó (bận vì đang được dùng) -> tính là active.
  `Maintaining` / `OutOfService` = không phục vụ -> loại. Đổi tập này ở hằng số
  `ACTIVE_STATUSES` nếu muốn chỉ tính `Available`.

Null → quyết tường minh (§7 #5, KHÔNG default ngầm): `status` null hoặc `is_public`
null bị loại khỏi baseline (không xác nhận được là active/public), và **được đếm +
ghi log** theo lý do (nguyên tắc "flag, không xoá ngầm").

Toạ độ bẩn (`DUP_COORD` / `COORD_ADDR_MISMATCH`, §7 #1) bị loại: placeholder coords
tạo **coverage ảo** — cùng cách xử lý với anchor T0 ở build_candidates.

**E-DQ4 (30/07)** — export kèm tầng **TÀI SẢN** (`n_guns_installed`/`site_power_kw`/
`current_type_asset`, xem `resolve_config.py`) BÊN CẠNH tầng trạng thái sống
(`num_connectors`/`total_power_kw`), và áp CHÍNH SÁCH DƯ: mọi con số CÓ TRỌNG SỐ
CÔNG SUẤT chỉ cộng trên `config_resolved`, phần dư (`CONFIG_UNKNOWN`) **được công bố
tường minh** trong report chứ không đọng thành mẫu số im lặng (khuôn E-DQ8c).

⚠️ **Nợ đã biết, KHÔNG sửa ở đây** (cần dòng register riêng): bộ lọc dưới vẫn đọc
`status`/`is_public` THÔ thay vì `op_status`/`access`/`is_operational` của **P8**, và
`_DIRTY_COORD_FLAGS` vẫn tìm cờ `DUP_COORD` mà **E-DQ1** đã thay bằng
`COORD_PLACEHOLDER`/`coord_resolved`. Vì vậy `n_covered0` ở đây KHÔNG bằng 19.015 của
tập cung canonical, và các tổng công suất bên dưới mang đúng cái sai lệch đó.

Output: data/processed/covered0.{parquet,geojson}
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
from .paths import COVERED0_GEOJSON, COVERED0_SITES, ensure_dirs

#: Trạng thái coi là "đang hoạt động" (phục vụ được) cho baseline coverage.
#: `AllBusy` = bận nhưng vẫn là trạm sống -> vẫn phủ vùng. Bỏ nếu muốn chỉ `Available`.
ACTIVE_STATUSES = frozenset({"Available", "AllBusy"})

#: cờ toạ độ bẩn -> loại (coverage ảo, §7 #1).
_DIRTY_COORD_FLAGS = frozenset({"DUP_COORD", "COORD_ADDR_MISMATCH"})

#: cột export (điểm trạm + thuộc tính không gian + provenance vận hành).
#: Hai tầng cấu hình đi CẠNH nhau (E-DQ4): LIVE = đang báo cáo, ASSET = lắp đặt.
_OUT_COLS = ["station_id", "lat", "lng", "h3_r8", "province_code", "status",
             "is_public", "operator", "current_type", "max_power_kw",
             "total_power_kw", "num_connectors", "verified",
             # E-DQ4 — tầng TÀI SẢN + provenance cấu hình
             "n_guns_installed", "site_power_kw", "nameplate_power_kw",
             "current_type_asset", "config_src", "config_resolved"]

#: cờ E-DQ4 đánh dấu dòng KHÔNG có cấu hình lắp đặt từ bất kỳ nguồn nào.
_CONFIG_UNKNOWN_FLAG = "CONFIG_UNKNOWN"


def _has_dirty_coord(flags):
    return bool(_DIRTY_COORD_FLAGS & set(flags)) if flags is not None else False


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
    """Lọc trạm active+public trong AOI -> covered0.{parquet,geojson}."""
    ensure_dirs()
    print(f"[covered0] {aoi}")
    cols = _OUT_COLS + ["quality_flags"]
    df = pd.read_parquet(STATIONS_DIR, columns=cols)
    n_total = len(df)

    # --- lọc theo AOI (đồng bộ candidate_sites) ---
    in_aoi = np.asarray(aoi.contains(df["lat"].to_numpy(), df["lng"].to_numpy()))
    df = df[in_aoi].copy()
    n_aoi = len(df)

    # --- bộ đếm lý do loại (flag, không xoá ngầm — §7 #5) ---
    active = df["status"].isin(ACTIVE_STATUSES)
    public = df["is_public"].eq(True)          # strict True: loại cả False lẫn null
    clean = ~df["quality_flags"].apply(_has_dirty_coord)

    reasons = {
        "status_null": int(df["status"].isna().sum()),
        "status_not_active": int((~active & df["status"].notna()).sum()),
        "is_public_null": int(df["is_public"].isna().sum()),
        "is_public_false": int(df["is_public"].eq(False).sum()),
        "dirty_coord": int((~clean).sum()),
    }

    covered0 = df[active & public & clean].copy()
    out = covered0[_OUT_COLS].reset_index(drop=True)

    # --- report ---
    report = {
        "aoi": aoi.to_dict(),
        "active_statuses": sorted(ACTIVE_STATUSES),
        "n_stations_total": n_total,
        "n_stations_in_aoi": n_aoi,
        "n_covered0": len(out),
        "dropped_by_reason": reasons,
        "status_breakdown": {str(k): int(v) for k, v in
                             covered0["status"].value_counts().items()},
        "config_capacity": _capacity_accounting(out),
    }

    out.to_parquet(COVERED0_SITES, index=False)
    _write_geojson(out, report)
    with open(str(COVERED0_SITES).replace(".parquet", "_report.json"), "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[covered0] trong AOI: {n_aoi}/{n_total} trạm")
    print(f"[covered0] loại: {reasons}")
    print(f"[covered0] -> {COVERED0_SITES}  ({len(out)} trạm active+public)")
    print("  theo status:", report["status_breakdown"])
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


def _write_geojson(covered0, report):
    """GeoJSON điểm baseline (cùng chuẩn với candidate_sites / demand proxy)."""
    feats = []
    for r in covered0.itertuples():
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(r.lng, 6), round(r.lat, 6)]},
            "properties": {
                "station_id": r.station_id, "h3_r8": r.h3_r8, "status": r.status,
                "is_public": bool(r.is_public), "operator": r.operator,
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
          "properties": {"generated_for": "covered0 — active baseline coverage (P8)",
                         "report": report},
          "features": feats}
    with open(COVERED0_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"[covered0] -> {COVERED0_GEOJSON}  ({len(feats)} điểm)")


def run(args=None):
    ap = argparse.ArgumentParser(
        description="Sinh covered0 — baseline coverage trạm active+public (P8)")
    add_aoi_args(ap)
    a = ap.parse_args(args)
    build(aoi_from_args(a))


if __name__ == "__main__":
    run()
