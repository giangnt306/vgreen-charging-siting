#!/usr/bin/env python3
"""Gộp 3 lần quét /search (cs/other/bss) -> 1 catalog trạm + 1 file mã tổng."""
import csv
import glob
import os

from .paths import CATALOG_DIR as CAT
SRC = [("cs", os.path.join(CAT, "evcs_stations.csv")),
       ("other", os.path.join(CAT, "evcs_other.csv")),
       ("bss", os.path.join(CAT, "evcs_bss.csv"))]
OUT_CSV = os.path.join(CAT, "evcs_catalog.csv")
OUT_CODES = os.path.join(CAT, "evcs_all_codes.txt")

rows = {}   # code -> record (+ tab)
for tab, path in SRC:
    if not os.path.exists(path):
        print(f"  (bỏ qua, chưa có {path})"); continue
    n = 0
    for r in csv.DictReader(open(path, encoding="utf-8")):
        code = r.get("code")
        if not code:
            continue
        r["tab"] = tab
        rows.setdefault(code, r)   # ưu tiên lần gặp đầu (cs > other > bss theo thứ tự SRC)
        n += 1
    print(f"  {tab:6} {path}: {n} dòng")

fields = ["code", "tab", "name", "addr", "lat", "lng", "evse", "tot",
          "verified", "depot", "evse_powers", "working_time", "is_public",
          "is_free_parking", "n_battery", "n_battery_avail"]
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for code in sorted(rows):
        w.writerow(rows[code])
with open(OUT_CODES, "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(rows)) + "\n")

from collections import Counter
by_tab = Counter(r["tab"] for r in rows.values())
print(f"\nTỔNG: {len(rows)} mã duy nhất  {dict(by_tab)}")
print(f"  -> {OUT_CSV} , {OUT_CODES}")
