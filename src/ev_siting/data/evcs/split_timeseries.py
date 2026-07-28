#!/usr/bin/env python3
"""
Gộp một raw run time-series vào từng file canonical theo evcs_code.

Có KHỬ TRÙNG LẶP + SẮP XẾP để bền vững:
  - khử trùng timestamp trong cùng 1 trạm (run mới thắng) -> miễn nhiễm với rows
    bị nhân đôi khi evcs_scrape.py crash giữa batch rồi resume;
  - union với file canonical cũ trước khi ghi, nên cùng một station xuất hiện lại
    ở block sau hoặc ở raw run mới sẽ không thể ghi đè mất telemetry cũ (F2);
  - ghi atomically bằng ``os.replace`` để crash không để lại file dở dang;
  - sắp xếp timestamp tăng dần -> mỗi file đã sort sẵn cho bước build_master.

Vẫn streaming: mỗi lúc chỉ giữ một block station trong RAM. Nếu một station xuất
hiện lại ở block sau, block đó được merge với canonical vừa ghi thay vì ghi đè.

- Input : một raw run CSV (station_code, timestamp, n_cars_charging)
- Output: data/interim/evcs_timeseries/<evcs_code>.csv  (timestamp, n_cars_charging), unique + sorted
Bước tiếp theo: python -m ev_siting.data.evcs.build_master_evcs
"""
import csv
import os
from pathlib import Path

from .paths import LOAD_TS, PROJECT_ROOT, TS_DIR


def _read_canonical(path):
    """Đọc canonical cũ; timestamp lỗi bị bỏ để một dòng hỏng không phá merge."""
    rows = {}
    n_bad = 0
    if not path.exists():
        return rows, n_bad
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                rows[int(row["timestamp"])] = row["n_cars_charging"]
            except (KeyError, TypeError, ValueError):
                n_bad += 1
    return rows, n_bad


def flush(code, rows, ts_dir=TS_DIR):
    """Merge một block station vào canonical, rồi thay file atomically.

    Giá trị của raw run đang xử lý thắng giá trị cũ ở cùng timestamp. Raw input vẫn
    được giữ bất biến theo run, vì vậy mọi conflict đều có thể audit lại.
    """
    safe = code.replace("/", "_")
    target = Path(ts_dir) / f"{safe}.csv"
    existing, n_bad_existing = _read_canonical(target)
    n_overlap = len(set(existing) & set(rows))
    existing.update(rows)  # raw run mới thắng ở timestamp trùng

    tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        fh.write("timestamp,n_cars_charging\n")
        for ts in sorted(existing):
            fh.write(f"{ts},{existing[ts]}\n")
    os.replace(tmp, target)
    return {"existing": len(existing) - len(rows) + n_overlap,
            "overlap": n_overlap, "bad_existing": n_bad_existing}


def main(input_path=LOAD_TS):
    os.makedirs(TS_DIR, exist_ok=True)
    prev = None
    buf = {}                      # timestamp(int) -> n_cars_charging(str), last-wins
    n_lines = n_files = n_dup = n_bad = n_overlap = n_bad_existing = 0

    print(f"[1/1] Merge + khử trùng + sort time-series từ {input_path} ...", flush=True)
    with open(input_path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)          # station_code,timestamp,n_cars_charging
        assert header[0] == "station_code", f"header lạ: {header}"
        for row in r:
            if len(row) < 3:
                n_bad += 1
                continue
            code, ts, n = row[0], row[1], row[2]
            if code != prev:
                if prev is not None:
                    stats = flush(prev, buf)
                    n_files += 1
                    n_overlap += stats["overlap"]
                    n_bad_existing += stats["bad_existing"]
                buf = {}
                prev = code
            try:
                t = int(ts)
            except ValueError:
                n_bad += 1
                continue
            if t in buf:
                n_dup += 1        # trùng timestamp -> last-wins
            buf[t] = n
            n_lines += 1
            if n_lines % 2_000_000 == 0:
                print(f"    ...{n_lines:,} dòng, {n_files:,} trạm, dup gộp={n_dup:,}", flush=True)
        if prev is not None:
            stats = flush(prev, buf)
            n_files += 1
            n_overlap += stats["overlap"]
            n_bad_existing += stats["bad_existing"]

    print(f"    Xong: {n_lines:,} dòng -> {n_files:,} file trong "
          f"{os.path.relpath(TS_DIR, PROJECT_ROOT)}/", flush=True)
    print(f"    Timestamp trùng đã gộp : {n_dup:,}", flush=True)
    print(f"    Timestamp trùng với canonical cũ (raw mới thắng): {n_overlap:,}", flush=True)
    print(f"    Dòng hỏng bỏ qua       : {n_bad:,}", flush=True)
    print(f"    Dòng hỏng trong canonical cũ bỏ qua: {n_bad_existing:,}", flush=True)
    print("Bước tiếp theo: python -m ev_siting.data.evcs.build_master_evcs", flush=True)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Merge một raw EVCS time-series run vào canonical theo station_code")
    ap.add_argument("--input", default=str(LOAD_TS), help="raw run CSV cần merge")
    args = ap.parse_args()
    main(args.input)
