#!/usr/bin/env python3
"""compare_runs.py — đối chiếu một raw run MỚI với canonical time-series ĐANG CÓ.

Vì sao cần: `split_timeseries` merge-union và **run mới thắng** ở timestamp trùng,
nên nếu chạy merge trước khi so sánh thì mọi bất đồng bị ghi đè im lặng. Module này
chạy TRƯỚC merge, trên **vùng chồng lấn thời gian của từng trạm**, để trả lời ba
câu hỏi mà register F đang để ngỏ:

* **F3 (gán nhầm danh tính).** Payload `history_data` không mang stationId nên
  không hậu kiểm được bằng nội dung. Nhưng nếu run cũ từng gán chuỗi của trạm A
  sang trạm B, thì cùng một timestamp sẽ cho **giá trị khác nhau** giữa hai lần
  crawl độc lập. `n_val_mismatch > 0` là dấu hiệu trực tiếp.
* **F2 (ghi đè khi resume).** Trạm bị mất khối dữ liệu sẽ có `n_ts_new_only` lớn
  bất thường trong khi các trạm khác gần 0.
* **Ổn định của nguồn.** `n_ts_old_only` lớn đồng loạt ⇒ server *đã* rút gọn/lấy
  mẫu thưa dữ liệu cũ khi phục vụ cửa sổ 720h — điều này đổi cách diễn giải mật độ
  mẫu (liên quan trực tiếp F19 duration-weighting), chứ không phải lỗi crawl.

Chạy::

    python -m ev_siting.data.evcs.compare_runs \\
        --run data/raw/evcs/timeseries_runs/load_ts_2026-07-29-full.csv

Xuất `*_compare.csv` (1 dòng/trạm) + `*_compare.json` (tóm tắt) cạnh file run.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from .paths import TS_DIR

VN = timezone(timedelta(hours=7))
csv.field_size_limit(sys.maxsize)

FIELDS = [
    "station_code",
    "n_old_total",
    "n_new_total",
    "old_min",
    "old_max",
    "new_min",
    "new_max",
    "win_start",
    "win_end",
    "n_old_win",
    "n_new_win",
    "n_ts_common",
    "n_ts_old_only",
    "n_ts_new_only",
    "n_val_mismatch",
    "verdict",
]


def _read_old(code, ts_dir=TS_DIR):
    """canonical cũ -> {timestamp: value}; trả None nếu trạm chưa từng có file."""
    path = os.path.join(str(ts_dir), f"{code.replace('/', '_')}.csv")
    if not os.path.exists(path):
        return None
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                out[int(row["timestamp"])] = str(row["n_cars_charging"])
            except (KeyError, TypeError, ValueError):
                continue
    return out


def _compare_one(code, new_pts, ts_dir):
    """new_pts: {timestamp: value}. Trả dict theo FIELDS."""
    old = _read_old(code, ts_dir)
    r = dict.fromkeys(FIELDS)
    r["station_code"] = code
    r["n_new_total"] = len(new_pts)
    r["new_min"] = min(new_pts) if new_pts else None
    r["new_max"] = max(new_pts) if new_pts else None
    if old is None:
        r.update(n_old_total=0, verdict="NEW_STATION")
        return r
    r["n_old_total"] = len(old)
    r["old_min"] = min(old) if old else None
    r["old_max"] = max(old) if old else None
    if not old or not new_pts:
        r["verdict"] = "EMPTY_SIDE"
        return r

    # Vùng chồng lấn tính RIÊNG cho từng trạm — span mỗi trạm mỗi khác.
    lo, hi = max(r["old_min"], r["new_min"]), min(r["old_max"], r["new_max"])
    r["win_start"], r["win_end"] = lo, hi
    if lo > hi:
        r["verdict"] = "NO_OVERLAP"
        return r
    o = {t: v for t, v in old.items() if lo <= t <= hi}
    n = {t: v for t, v in new_pts.items() if lo <= t <= hi}
    common = o.keys() & n.keys()
    r["n_old_win"], r["n_new_win"] = len(o), len(n)
    r["n_ts_common"] = len(common)
    r["n_ts_old_only"] = len(o) - len(common)
    r["n_ts_new_only"] = len(n) - len(common)
    mism = sum(1 for t in common if o[t] != n[t])
    r["n_val_mismatch"] = mism
    if mism:
        r["verdict"] = "VALUE_MISMATCH"
    elif r["n_ts_old_only"] or r["n_ts_new_only"]:
        r["verdict"] = "TS_SET_DIFF"
    else:
        r["verdict"] = "IDENTICAL"
    return r


def _iter_run(run_path):
    """Stream raw run, gom theo station_code (file ghi tuần tự theo mã)."""
    with open(run_path, newline="", encoding="utf-8") as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        assert header[0] == "station_code", f"header lạ: {header}"
        cur, buf = None, {}
        for row in rdr:
            if len(row) < 3:
                continue
            code, ts, val = row[0], row[1], row[2]
            if code != cur:
                if cur is not None:
                    yield cur, buf
                cur, buf = code, {}
            try:
                buf[int(ts)] = val
            except ValueError:
                continue
        if cur is not None:
            yield cur, buf


def _fmt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=VN).isoformat(timespec="seconds") if ms else None


def main(run_path, ts_dir=TS_DIR, out_prefix=None):
    out_prefix = out_prefix or os.path.splitext(run_path)[0]
    rows_out = f"{out_prefix}_compare.csv"
    summary_out = f"{out_prefix}_compare.json"

    tally, n = {}, 0
    worst = []  # (n_val_mismatch, code) — giữ top để soi tay
    agg = dict(n_old_win=0, n_new_win=0, n_ts_common=0, n_ts_old_only=0, n_ts_new_only=0, n_val_mismatch=0)
    with open(rows_out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for code, pts in _iter_run(run_path):
            r = _compare_one(code, pts, ts_dir)
            w.writerow(r)
            n += 1
            tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
            for k in agg:
                agg[k] += r.get(k) or 0
            if r.get("n_val_mismatch"):
                worst.append((r["n_val_mismatch"], code, r["n_ts_common"]))
            if n % 2000 == 0:
                print(f"    ...{n:,} trạm", flush=True)
    worst.sort(reverse=True)

    summary = dict(
        run=os.path.relpath(run_path),
        n_stations=n,
        verdicts=tally,
        totals=agg,
        pct_val_mismatch=round(100 * agg["n_val_mismatch"] / max(1, agg["n_ts_common"]), 4),
        top_mismatch=[dict(station_code=c, n_val_mismatch=m, n_ts_common=k) for m, c, k in worst[:25]],
        generated_at=datetime.now(VN).isoformat(timespec="seconds"),
    )
    with open(summary_out, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"\n[compare] {n:,} trạm", flush=True)
    for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"    {k:16} {v:7,}  ({100 * v / max(1, n):5.1f}%)", flush=True)
    print(
        f"    điểm chung {agg['n_ts_common']:,} | lệch giá trị {agg['n_val_mismatch']:,} "
        f"({summary['pct_val_mismatch']}%)",
        flush=True,
    )
    print(f"    chỉ-có-ở-cũ {agg['n_ts_old_only']:,} | chỉ-có-ở-mới {agg['n_ts_new_only']:,}", flush=True)
    print(f"-> {rows_out}\n-> {summary_out}", flush=True)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Đối chiếu raw run mới với canonical time-series hiện có")
    ap.add_argument("--run", required=True, help="raw run CSV mới (chưa merge)")
    ap.add_argument("--ts-dir", default=str(TS_DIR), help="thư mục canonical cũ")
    ap.add_argument("--out-prefix", help="tiền tố file xuất (mặc định cạnh file run)")
    a = ap.parse_args()
    main(a.run, a.ts_dir, a.out_prefix)
