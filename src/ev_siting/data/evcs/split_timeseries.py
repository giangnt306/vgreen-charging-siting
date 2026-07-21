#!/usr/bin/env python3
"""
Tách load_ts.csv thành từng file CSV time-series theo evcs_code.

Có KHỬ TRÙNG LẶP + SẮP XẾP để bền vững:
  - khử trùng timestamp trong cùng 1 trạm (last-wins) -> miễn nhiễm với rows bị
    nhân đôi khi evcs_scrape.py crash giữa batch rồi resume (ghi rows xong nhưng
    chưa kịp đánh dấu .done -> lần sau emit lại trạm đó);
  - sắp xếp timestamp tăng dần -> mỗi file đã sort sẵn cho bước build_master.

Vẫn streaming: load_ts.csv nhóm sẵn theo station_code nên mỗi lúc chỉ giữ dữ liệu
của MỘT trạm trong RAM (vài nghìn dòng), không nạp cả file.

- Input : data/raw/evcs/load_ts.csv (station_code, timestamp, n_cars_charging)
- Output: data/interim/evcs_timeseries/<evcs_code>.csv  (timestamp, n_cars_charging), unique + sorted
Bước tiếp theo: python -m ev_siting.data.evcs.build_master_evcs
"""
import csv, os

from .paths import LOAD_TS, TS_DIR, PROJECT_ROOT


def flush(code, rows):
    """Ghi 1 trạm ra file: unique theo timestamp, sort tăng dần."""
    safe = code.replace("/", "_")
    with open(os.path.join(TS_DIR, f"{safe}.csv"), "w", newline="") as fh:
        fh.write("timestamp,n_cars_charging\n")
        for ts in sorted(rows):
            fh.write(f"{ts},{rows[ts]}\n")


def main():
    os.makedirs(TS_DIR, exist_ok=True)
    prev = None
    buf = {}                      # timestamp(int) -> n_cars_charging(str), last-wins
    n_lines = n_files = n_dup = n_bad = 0

    print("[1/1] Tách + khử trùng + sort time-series theo evcs_code ...", flush=True)
    with open(LOAD_TS, newline="") as f:
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
                    flush(prev, buf); n_files += 1
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
            flush(prev, buf); n_files += 1

    print(f"    Xong: {n_lines:,} dòng -> {n_files:,} file trong "
          f"{os.path.relpath(TS_DIR, PROJECT_ROOT)}/", flush=True)
    print(f"    Timestamp trùng đã gộp : {n_dup:,}", flush=True)
    print(f"    Dòng hỏng bỏ qua       : {n_bad:,}", flush=True)
    print("Bước tiếp theo: python -m ev_siting.data.evcs.build_master_evcs", flush=True)


if __name__ == "__main__":
    main()
