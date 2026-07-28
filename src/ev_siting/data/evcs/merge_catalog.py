#!/usr/bin/env python3
"""Gộp 3 lần quét /search (cs/other/bss) -> 1 catalog trạm + 1 file mã tổng."""
import csv
import os
from collections import Counter

from .paths import ALL_CODES, CATALOG_CSV, CATALOG_DIR as CAT

SRC = [("cs", os.path.join(CAT, "evcs_stations.csv")),
       ("other", os.path.join(CAT, "evcs_other.csv")),
       ("bss", os.path.join(CAT, "evcs_bss.csv"))]
OUT_CSV = str(CATALOG_CSV)
OUT_CODES = str(ALL_CODES)

rows = {}   # code -> record (+ tab)
# P6 — kiểm soát trùng PK: đếm rõ số dòng bị dedup (KHÔNG bao giờ gộp/cộng
# công suất giữa các bản trùng — chỉ giữ lần gặp đầu). Tách trong-tab vs chéo-tab
# để mọi trùng station_code đều quan sát được (không dedup ngầm). Xem known-issues P6.
dup_within = 0            # cùng code lặp trong cùng 1 tab (enumerate lưới chồng lấn)
dup_cross = {}            # code -> (tab_giữ, tab_bỏ) khi 1 trạm xuất hiện ở >1 tab
for tab, path in SRC:
    if not os.path.exists(path):
        print(f"  (bỏ qua, chưa có {path})"); continue
    n = 0
    seen_in_tab = set()
    for r in csv.DictReader(open(path, encoding="utf-8")):
        code = r.get("code")
        if not code:
            continue
        r["tab"] = tab
        if code in rows:                       # đã có từ tab trước / lần trước
            if code in seen_in_tab:
                dup_within += 1
            else:
                dup_cross[code] = (rows[code]["tab"], tab)
        else:
            rows[code] = r                     # ưu tiên lần gặp đầu (cs > other > bss theo thứ tự SRC)
        seen_in_tab.add(code)
        n += 1
    print(f"  {tab:6} {path}: {n} dòng")

n_dup = dup_within + len(dup_cross)
print(f"  dedup PK: {n_dup} dòng trùng bị bỏ "
      f"(trong-tab {dup_within} · chéo-tab {len(dup_cross)}) — giữ first-wins, KHÔNG cộng công suất")
if dup_cross:
    ex = list(dup_cross.items())[:5]
    print(f"    vd chéo-tab: {[(c, '%s<-%s' % kv) for c, kv in ex]}")

fields = ["code", "tab", "name", "addr", "lat", "lng", "evse", "tot",
          "verified", "depot", "evse_powers", "working_time", "is_public",
          "is_free_parking", "n_battery", "n_battery_avail"]
os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for code in sorted(rows):
        w.writerow(rows[code])
with open(OUT_CODES, "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(rows)) + "\n")

by_tab = Counter(r["tab"] for r in rows.values())
print(f"\nTỔNG: {len(rows)} mã duy nhất  {dict(by_tab)}")
print(f"  -> {OUT_CSV} , {OUT_CODES}")
