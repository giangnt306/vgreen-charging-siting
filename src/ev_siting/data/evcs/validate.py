#!/usr/bin/env python3
"""
validate.py — Cổng QA cho dataset EVCS độc lập.

Kiểm tra toàn vẹn (CRITICAL) + chất lượng (WARN) trên bảng master + thư mục
time-series, in báo cáo và GHI run-manifest JSON (data/interim/quality_report.json)
để phục vụ lineage/audit. Thoát mã != 0 nếu có lỗi CRITICAL -> dùng làm cổng
chặn trong pipeline (run_pipeline.sh dừng nếu QA fail).

Kiểm tra:
  CRITICAL (toàn vẹn) — pipeline SAI nếu vi phạm:
    - master đọc được, không rỗng, không thiếu cột.
    - station_code là DUY NHẤT (không trùng khóa).
    - has_timeseries==True  <=>  tồn tại file data/interim/evcs_timeseries/<code>.csv.
    - mọi file time-series đều có 1 dòng trong master (không mồ côi).
  WARN (chất lượng) — cần lưu ý, không chặn:
    - cờ QA: DUP_TS / NONMONOTONIC / NEG_VALUE / NONNUMERIC / ALL_ZERO / SPARSE / COORD_INVALID.
    - phân bố loại trạm, % có telemetry, cửa sổ thời gian, tổng số điểm.

Chạy: PYTHONPATH=src python -m ev_siting.data.evcs.validate
"""
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

from .paths import MASTER_CSV as MASTER
from .paths import PROJECT_ROOT, TS_DIR
from .paths import QUALITY_REPORT as REPORT

REQUIRED_COLS = [
    "station_code", "station_type", "has_timeseries", "ts_n_rows",
    "ts_time_start_ms", "ts_time_end_ms", "quality_flag",
]

def main():
    crit, warn = [], []          # danh sách thông điệp
    if not os.path.exists(MASTER):
        print(f"CRITICAL: không thấy master {MASTER}", file=sys.stderr)
        sys.exit(2)

    # ---- đọc master ----
    rows = []
    with open(MASTER, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        cols = r.fieldnames or []
        missing = [c for c in REQUIRED_COLS if c not in cols]
        if missing:
            crit.append(f"master thiếu cột: {missing}")
        for row in r:
            rows.append(row)

    if not rows:
        crit.append("master rỗng (0 dòng)")
        _emit(crit, warn, {}, {})
        sys.exit(2)

    # ---- toàn vẹn khóa ----
    codes = [row["station_code"] for row in rows]
    dup_codes = [c for c, n in Counter(codes).items() if n > 1]
    if dup_codes:
        crit.append(f"station_code TRÙNG: {len(dup_codes)} mã (vd {dup_codes[:5]})")

    master_has_ts = {row["station_code"] for row in rows
                     if str(row.get("has_timeseries")).lower() == "true"}
    master_codes = set(codes)

    # ---- đối chiếu với file trên đĩa ----
    ts_files = {fn[:-4] for fn in os.listdir(TS_DIR) if fn.endswith(".csv")}
    ts_missing_file = master_has_ts - ts_files          # master bảo có TS nhưng thiếu file
    ts_orphan_file  = ts_files - master_codes           # file TS không có dòng master
    file_but_flag_false = ts_files - master_has_ts       # có file nhưng master ghi False/không có

    if ts_missing_file:
        crit.append(f"has_timeseries=True nhưng THIẾU file: {len(ts_missing_file)} "
                    f"(vd {sorted(ts_missing_file)[:5]})")
    if ts_orphan_file:
        crit.append(f"file time-series MỒ CÔI (không có dòng master): {len(ts_orphan_file)} "
                    f"(vd {sorted(ts_orphan_file)[:5]})")
    if file_but_flag_false:
        # file tồn tại nhưng master không đánh dấu True -> lệch cờ
        crit.append(f"có file TS nhưng has_timeseries!=True: {len(file_but_flag_false)} "
                    f"(vd {sorted(file_but_flag_false)[:5]})")

    # ---- thống kê chất lượng (WARN) ----
    by_type = Counter(row["station_type"] for row in rows)
    flag_counter = Counter()
    for row in rows:
        for fl in filter(None, (row.get("quality_flag") or "").split(";")):
            flag_counter[fl] += 1

    n_total = len(rows)
    n_ts = len(master_has_ts)
    n_rows_total = sum(int(row["ts_n_rows"]) for row in rows
                       if (row.get("ts_n_rows") or "").isdigit())
    starts = [int(row["ts_time_start_ms"]) for row in rows
              if (row.get("ts_time_start_ms") or "").isdigit()]
    ends = [int(row["ts_time_end_ms"]) for row in rows
            if (row.get("ts_time_end_ms") or "").isdigit()]
    win_start = min(starts) if starts else None
    win_end = max(ends) if ends else None

    for fl in ("DUP_TS", "NONMONOTONIC", "NEG_VALUE", "NONNUMERIC",
               "COORD_INVALID", "ALL_ZERO", "SPARSE"):
        if flag_counter.get(fl):
            warn.append(f"{fl}: {flag_counter[fl]:,} trạm")

    # ---- E-DQ10: cổng provenance — đối chiếu snapshot input đã đóng băng ----
    # Chưa freeze -> WARN (không chặn pipeline cũ). Đã freeze mà input lệch -> CRITICAL
    # (bước làm sạch phía sau giả định input bất biến — drift làm audit vô nghĩa).
    snapshot_id, snap_status, snap_issues = None, "NOT_FROZEN", []
    try:
        from ..provenance import manifest as SNAP
        snap = SNAP.load_manifest()
        if snap is None:
            warn.append("SNAPSHOT: chưa freeze (data/raw/MANIFEST.json) — E-DQ10 mở")
        else:
            snapshot_id = snap.get("snapshot_id")
            snap_issues = SNAP.verify_manifest(snap, full=False)
            snap_status = "FAIL" if snap_issues else "PASS"
            if snap_issues:
                crit.append(f"SNAPSHOT drift: {len(snap_issues)} input lệch khỏi manifest "
                            f"(vd {snap_issues[0]})")
    except Exception as e:  # thiếu module / manifest hỏng -> cảnh báo, không chặn
        snap_status = "ERROR"
        warn.append(f"SNAPSHOT: không đối chiếu được manifest ({e})")

    def ms_iso(ms):
        if ms is None:
            return None
        return datetime.fromtimestamp(ms / 1000, timezone.utc).astimezone().isoformat()

    manifest = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "snapshot_id": snapshot_id,
        "snapshot_integrity": snap_status,
        "snapshot_issues": snap_issues,
        "master_path": os.path.relpath(MASTER, PROJECT_ROOT),
        "n_stations": n_total,
        "n_with_timeseries": n_ts,
        "pct_with_timeseries": round(n_ts / n_total * 100, 2),
        "n_timeseries_files": len(ts_files),
        "n_timeseries_rows": n_rows_total,
        "time_window_start_ms": win_start,
        "time_window_end_ms": win_end,
        "time_window_start": ms_iso(win_start),
        "time_window_end": ms_iso(win_end),
        "by_station_type": dict(by_type),
        "quality_flags": dict(flag_counter),
        "critical": crit,
        "warnings": warn,
        "status": "FAIL" if crit else ("WARN" if warn else "PASS"),
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    _emit(crit, warn, manifest, flag_counter)
    sys.exit(1 if crit else 0)


def _emit(crit, warn, manifest, flag_counter):
    print("================= QA VALIDATION =================")
    if manifest:
        print(f"Trạm master            : {manifest['n_stations']:,}")
        print(f"  có time-series       : {manifest['n_with_timeseries']:,} "
              f"({manifest['pct_with_timeseries']}%)")
        print(f"File time-series        : {manifest['n_timeseries_files']:,}")
        print(f"Tổng điểm time-series   : {manifest['n_timeseries_rows']:,}")
        print(f"Cửa sổ thời gian        : {manifest.get('time_window_start')} "
              f"-> {manifest.get('time_window_end')}")
        print(f"Loại trạm               : {manifest['by_station_type']}")
        print(f"Snapshot (E-DQ10)       : {manifest.get('snapshot_id')} "
              f"[{manifest.get('snapshot_integrity')}]")
    print("-------------------------------------------------")
    if crit:
        print(f"CRITICAL ({len(crit)}):")
        for m in crit:
            print(f"  ✗ {m}")
    else:
        print("CRITICAL: 0  ✓ toàn vẹn OK")
    if warn:
        print(f"WARN ({len(warn)}):")
        for m in warn:
            print(f"  ! {m}")
    else:
        print("WARN: 0")
    status = "FAIL" if crit else ("WARN" if warn else "PASS")
    print("-------------------------------------------------")
    print(f"KẾT QUẢ: {status}   (manifest -> {os.path.relpath(REPORT, PROJECT_ROOT)})")
    print("=================================================")


if __name__ == "__main__":
    main()
