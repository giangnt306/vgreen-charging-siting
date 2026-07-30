#!/usr/bin/env python3
"""
Dựng bảng master ĐỘC LẬP từ dữ liệu tự crawl (evcs.vn), KHÔNG phụ thuộc dataset của Kỳ,
KÈM các cột chất lượng dữ liệu (QA) tính ngay trong 1 lượt quét time-series.

Khóa chính = station_code (mã evcs.vn). Ghép trực tiếp 1-1 với time-series của mình
(data/interim/evcs_timeseries/<station_code>.csv) theo tên file -> KHÔNG có orphan.

QA cho mỗi trạm (quét khi đọc file): số dòng, min/max thời gian, min/max giá trị,
số điểm null/không phải số, số timestamp trùng, cờ đơn điệu, và cột `quality_flag`
tổng hợp (NO_TS / DUP_TS / NONMONOTONIC / NEG_VALUE / NONNUMERIC / ALL_ZERO /
SPARSE / COORD_INVALID). Báo cáo toàn tập ở ev_siting.data.evcs.validate.

- Input : data/raw/evcs/catalog/evcs_catalog.csv , data/interim/evcs_timeseries/<code>.csv
- Output: data/interim/stations_master_evcs.csv
"""
import csv
import json
import os
import re
from datetime import datetime, timedelta, timezone

from .paths import CATALOG_CSV as CATALOG
from .paths import MASTER_CSV as OUT
from .paths import PROJECT_ROOT, TS_DIR

VN_TZ = timezone(timedelta(hours=7))
TAB_LABEL = {"cs": "VINFAST_CS", "bss": "BATTERY_SWAP", "other": "OTHER"}
VN_BBOX = (8.0, 23.6, 102.0, 110.0)   # lat_min, lat_max, lng_min, lng_max
SPARSE_MIN = 24                        # < 24 điểm/7 ngày coi là thưa


def derive_power(evse_powers_json):
    """evsePowers thô (JSON) -> cột schema cung.

    evsePowers = [{type:<W>, totalEvse:<số súng lắp đặt>, numberOfAvailableEvse:<đang trống>}].
    `totalEvse` là số súng THẬT (khác `totalCharging`= số xe đang sạc — biến động).
    Trả về (num_connectors, connector_types, max_power_kw, total_power_kw, current_type).
    connector_types = nhãn công suất (`POWER-3.5kW|POWER-120kW`). evcs.vn KHÔNG
    lộ chuẩn cắm hay AC/DC, nên không suy `current_type` từ ngưỡng kW.
    """
    try:
        groups = json.loads(evse_powers_json) if evse_powers_json else []
    except (ValueError, TypeError):
        groups = []
    if not isinstance(groups, list) or not groups:
        return "", "", "", "", ""
    n_conn = total_w = max_w = 0
    labels = []                              # giữ thứ tự, khử trùng
    for g in groups:
        if not isinstance(g, dict):
            continue
        try:
            w = int(g.get("type") or 0)
            n = int(g.get("totalEvse") or 0)
        except (ValueError, TypeError):
            continue
        if w <= 0 and n <= 0:
            continue
        if w > 0:
            max_w = max(max_w, w)
        n = max(n, 0)
        n_conn += n
        total_w += w * n
        lbl = f"POWER-{w / 1000:g}kW"
        if lbl not in labels:
            labels.append(lbl)
    return (n_conn or "", "|".join(labels),
            round(max_w / 1000, 1) if max_w else "",
            round(total_w / 1000, 1) if total_w else "", "")

def iso(ms):
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000, VN_TZ).strftime("%Y-%m-%d %H:%M:%S")

def province_code(code):
    m = re.match(r"C\.([A-Z]+)\d", code or "")
    return m.group(1) if m else ""

def scan_ts(path):
    """1 lượt đọc file time-series -> dict thống kê QA."""
    n = n_null = n_neg = n_nonnum = n_dup = 0
    tmin = tmax = vmin = vmax = None
    prev_t = None
    monotonic = True
    seen = set()
    with open(path) as f:
        next(f, None)  # header
        for line in f:
            i = line.find(",")
            if i < 0:
                continue
            ts_s, val_s = line[:i], line[i + 1:].strip()
            try:
                t = int(ts_s)
            except ValueError:
                n_nonnum += 1
                continue
            if prev_t is not None and t < prev_t:
                monotonic = False
            if t in seen:
                n_dup += 1
            else:
                seen.add(t)
            prev_t = t
            if tmin is None or t < tmin: tmin = t
            if tmax is None or t > tmax: tmax = t
            # giá trị
            if val_s == "":
                n_null += 1
            else:
                try:
                    v = int(val_s)
                    if v < 0:
                        n_neg += 1
                    if vmin is None or v < vmin: vmin = v
                    if vmax is None or v > vmax: vmax = v
                except ValueError:
                    n_nonnum += 1
            n += 1
    return dict(n=n, tmin=tmin, tmax=tmax, vmin=vmin, vmax=vmax,
                n_null=n_null, n_neg=n_neg, n_nonnum=n_nonnum,
                n_dup=n_dup, monotonic=monotonic)

def coord_ok(lat_s, lng_s):
    try:
        lat, lng = float(lat_s), float(lng_s)
    except (TypeError, ValueError):
        return False
    return (VN_BBOX[0] <= lat <= VN_BBOX[1]) and (VN_BBOX[2] <= lng <= VN_BBOX[3])

def quality_flag(has_ts, st, lat_ok):
    flags = []
    if not lat_ok:
        flags.append("COORD_INVALID")
    if not has_ts:
        flags.append("NO_TS")
        return ";".join(flags)
    if st["n_dup"]:            flags.append("DUP_TS")
    if not st["monotonic"]:   flags.append("NONMONOTONIC")
    if st["n_neg"]:           flags.append("NEG_VALUE")
    if st["n_nonnum"] or st["n_null"]: flags.append("NONNUMERIC")
    if st["vmax"] == 0:       flags.append("ALL_ZERO")
    if st["n"] < SPARSE_MIN:  flags.append("SPARSE")
    return ";".join(flags)

# ---------------------------------------------------------------------------
# 1) Quét time-series -> QA per trạm
# ---------------------------------------------------------------------------
print("[1/3] Quét + QA time-series trong data/interim/evcs_timeseries/ ...", flush=True)
ts_stats = {}
n_files = n_lines = 0
for fn in os.listdir(TS_DIR):
    if not fn.endswith(".csv"):
        continue
    code = fn[:-4]
    st = scan_ts(os.path.join(TS_DIR, fn))
    ts_stats[code] = st
    n_files += 1
    n_lines += st["n"]
    if n_files % 3000 == 0:
        print(f"    ...{n_files:,} file, {n_lines:,} dòng", flush=True)
print(f"    Xong: {n_files:,} file, {n_lines:,} dòng.", flush=True)

# ---------------------------------------------------------------------------
# 2) Ghép catalog của mình + QA (1-1 theo station_code)
# ---------------------------------------------------------------------------
print("[2/3] Ghép catalog tự crawl + QA ...", flush=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)

OUT_FIELDS = [
    "station_code", "station_type", "network", "name", "address",
    "lat", "lng", "province_code",
    # --- cấu hình cung (dẫn xuất từ evsePowers, khớp SCHEMA_CONTRACT) ---
    "num_connectors", "connector_types", "current_type",
    "max_power_kw", "total_power_kw",
    "n_charging_snapshot", "verified", "status", "working_time", "is_public", "evse_powers",
    "has_timeseries", "ts_n_rows",
    "ts_time_start_ms", "ts_time_end_ms", "ts_time_start", "ts_time_end",
    "ts_val_min", "ts_val_max", "ts_n_null", "ts_n_dup", "ts_monotonic",
    "quality_flag",
    "xref_gold_station_id", "xref_gold_dist_m",
]

n_out = n_ts = n_flagged = 0
by_type = {}
flag_counter = {}
with open(CATALOG, newline="", encoding="utf-8") as fin, \
     open(OUT, "w", newline="", encoding="utf-8") as fout:
    r = csv.DictReader(fin)
    w = csv.DictWriter(fout, fieldnames=OUT_FIELDS)
    w.writeheader()
    for row in r:
        code = row["code"]
        st = ts_stats.get(code)
        has_ts = st is not None
        tab = row.get("tab", "")
        by_type[tab] = by_type.get(tab, 0) + 1
        lat_ok = coord_ok(row.get("lat"), row.get("lng"))
        flag = quality_flag(has_ts, st, lat_ok)
        if has_ts:
            n_ts += 1
        if flag and flag != "NO_TS":
            n_flagged += 1
        for fl in filter(None, flag.split(";")):
            flag_counter[fl] = flag_counter.get(fl, 0) + 1
        num_conn, conn_types, max_kw, total_kw, cur_type = derive_power(row.get("evse_powers"))
        w.writerow({
            "station_code": code,
            "station_type": TAB_LABEL.get(tab, tab.upper()),
            "network": row.get("evse", ""),
            "name": row.get("name", ""),
            "address": row.get("addr", ""),
            "lat": row.get("lat", ""),
            "lng": row.get("lng", ""),
            "province_code": province_code(code),
            "num_connectors": num_conn,
            "connector_types": conn_types,
            "current_type": cur_type,
            "max_power_kw": max_kw,
            "total_power_kw": total_kw,
            "n_charging_snapshot": row.get("tot", ""),
            "verified": row.get("verified", ""),
            "status": row.get("depot", ""),
            "working_time": row.get("working_time", ""),
            "is_public": row.get("is_public", ""),
            "evse_powers": row.get("evse_powers", ""),
            "has_timeseries": has_ts,
            "ts_n_rows": st["n"] if has_ts else "",
            "ts_time_start_ms": st["tmin"] if has_ts else "",
            "ts_time_end_ms": st["tmax"] if has_ts else "",
            "ts_time_start": iso(st["tmin"]) if has_ts else "",
            "ts_time_end": iso(st["tmax"]) if has_ts else "",
            "ts_val_min": st["vmin"] if has_ts and st["vmin"] is not None else "",
            "ts_val_max": st["vmax"] if has_ts and st["vmax"] is not None else "",
            "ts_n_null": st["n_null"] if has_ts else "",
            "ts_n_dup": st["n_dup"] if has_ts else "",
            "ts_monotonic": st["monotonic"] if has_ts else "",
            "quality_flag": flag,
            "xref_gold_station_id": row.get("gold_station_id", "") or "",
            "xref_gold_dist_m": row.get("gold_dist_m", "") or "",
        })
        n_out += 1

ts_not_in_cat = set(ts_stats) - {
    row["code"] for row in csv.DictReader(open(CATALOG, encoding="utf-8"))
}

# ---------------------------------------------------------------------------
# 3) Báo cáo
# ---------------------------------------------------------------------------
print("[3/3] Xong.\n", flush=True)
print("================ BÁO CÁO (dataset ĐỘC LẬP) ================")
print(f"Trạm trong master (catalog tự crawl) : {n_out:,}")
for tab in ("cs", "bss", "other"):
    print(f"   - {TAB_LABEL.get(tab,tab):12} : {by_type.get(tab,0):,}")
print(f"Trạm có time-series                  : {n_ts:,}  ({n_ts/n_out*100:.1f}%)")
print(f"Tổng dòng time-series                : {n_lines:,}")
print(f"Trạm CÓ time-series nhưng bị gắn cờ QA: {n_flagged:,}")
if flag_counter:
    print("Phân bố cờ QA:")
    for fl, c in sorted(flag_counter.items(), key=lambda x: -x[1]):
        print(f"   - {fl:14} : {c:,}")
print(f"File TS không nằm trong catalog       : {len(ts_not_in_cat)}  {sorted(ts_not_in_cat)[:5]}")
print(f"Output: {os.path.relpath(OUT, PROJECT_ROOT)}")
print("Bước tiếp theo: python -m ev_siting.data.evcs.validate")
print("==========================================================")
