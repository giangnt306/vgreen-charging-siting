#!/usr/bin/env python3
"""roads_pbf.py — Mạng lưới đường (trắc địa) VN từ Geofabrik .pbf -> road_len theo H3.

Vì cả nước có hàng triệu `way` đường -> Overpass không kham nổi. Ta tải dump
`vietnam-latest.osm.pbf` (Geofabrik) rồi **stream** bằng osmium (C++), gom trực
tiếp chiều dài đường về ô H3 res 8 — không giữ toàn bộ segment trong RAM.

Với mỗi `way` có tag `highway` (loại lái xe được):
  - Tính chiều dài từng đoạn giữa 2 node (haversine).
  - Lấy mẫu dọc polyline mỗi ~SAMPLE_M mét, cộng chiều dài đoạn con vào ô H3
    của điểm giữa -> phân bổ chiều dài theo ô khá sát ở res 8 (cạnh ~0,46 km).

Output:
  road_len_m    : tổng chiều dài đường (mọi loại lái xe được) trong ô
  road_len_mt_m : chiều dài đường trục lớn (cao tốc/quốc lộ) trong ô

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.roads_pbf            # tải nếu thiếu + build
    PYTHONPATH=src python -m ev_siting.data.osm.roads_pbf --force-download
"""
import argparse
import math
import sys

import osmium
import pandas as pd

from .paths import (GEOFABRIK_URL, H3_RES_R8, PBF_PATH, ROADS_H3, ensure_dirs)
import h3

# Loại highway KHÔNG tính là "đường" (hạ tầng đi bộ/xe đạp/đặc thù).
_EXCLUDE = {
    "footway", "path", "pedestrian", "steps", "cycleway", "bridleway",
    "corridor", "construction", "proposed", "raceway", "elevator", "platform",
}
# Đường trục lớn = cao tốc (motorway) + quốc lộ (trunk/primary) + nhánh nối.
_MAJOR = {
    "motorway", "trunk", "primary",
    "motorway_link", "trunk_link", "primary_link",
}
SAMPLE_M = 150.0          # bước lấy mẫu dọc đường (m)
_EARTH_R = 6_371_000.0    # bán kính Trái Đất (m)


def _haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_R * math.asin(math.sqrt(a))


class RoadHandler(osmium.SimpleHandler):
    """Gom road_len theo ô H3 khi stream .pbf (không giữ segment)."""

    def __init__(self):
        super().__init__()
        # h3_r8 -> [road_len_m, road_len_mt_m]
        self.cells = {}
        self.n_ways = 0
        self.n_ways_kept = 0

    def way(self, w):
        hwy = w.tags.get("highway")
        if hwy is None:
            return
        self.n_ways += 1
        if hwy in _EXCLUDE:
            return
        pts = [(n.location.lat, n.location.lon) for n in w.nodes if n.location.valid()]
        if len(pts) < 2:
            return
        self.n_ways_kept += 1
        is_major = hwy in _MAJOR
        for (la1, lo1), (la2, lo2) in zip(pts, pts[1:]):
            seg = _haversine(la1, lo1, la2, lo2)
            if seg == 0:
                continue
            n = max(1, int(seg // SAMPLE_M))    # số đoạn con
            for k in range(n):
                # điểm giữa đoạn con thứ k
                t = (k + 0.5) / n
                mlat = la1 + (la2 - la1) * t
                mlon = lo1 + (lo2 - lo1) * t
                sub = seg / n
                cell = h3.latlng_to_cell(mlat, mlon, H3_RES_R8)
                acc = self.cells.get(cell)
                if acc is None:
                    acc = [0.0, 0.0]
                    self.cells[cell] = acc
                acc[0] += sub
                if is_major:
                    acc[1] += sub


def download_pbf(force=False):
    import requests
    if PBF_PATH.exists() and PBF_PATH.stat().st_size > 0 and not force:
        mb = PBF_PATH.stat().st_size / 1e6
        print(f"[pbf] đã có {PBF_PATH.name} ({mb:.0f} MB) — bỏ qua tải "
              f"(dùng --force-download để tải lại)")
        return
    print(f"[pbf] tải {GEOFABRIK_URL} ...")
    with requests.get(GEOFABRIK_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        got = 0
        tmp = PBF_PATH.with_suffix(".pbf.part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB
                f.write(chunk)
                got += len(chunk)
                if total:
                    print(f"\r      {got/1e6:6.0f}/{total/1e6:.0f} MB "
                          f"({100*got/total:4.1f}%)", end="", file=sys.stderr)
        print("", file=sys.stderr)
        tmp.replace(PBF_PATH)
    print(f"[pbf] xong -> {PBF_PATH} ({PBF_PATH.stat().st_size/1e6:.0f} MB)")


def run(force_download=False):
    ensure_dirs()
    download_pbf(force=force_download)
    print("[roads] stream .pbf bằng osmium (locations=True)...")
    h = RoadHandler()
    # locations=True: nạp cache toạ độ node để way có hình học.
    h.apply_file(str(PBF_PATH), locations=True)
    print(f"[roads] {h.n_ways} way có highway; giữ {h.n_ways_kept} (loại lái xe được); "
          f"{len(h.cells)} ô H3 có đường.")
    df = pd.DataFrame(
        [(c, v[0], v[1]) for c, v in h.cells.items()],
        columns=["h3_r8", "road_len_m", "road_len_mt_m"],
    )
    df = df.sort_values("road_len_m", ascending=False).reset_index(drop=True)
    df.to_parquet(ROADS_H3, index=False)
    print(f"[roads] -> {ROADS_H3}  ({len(df)} ô, "
          f"tổng {df.road_len_m.sum()/1e3:,.0f} km đường, "
          f"{df.road_len_mt_m.sum()/1e3:,.0f} km trục lớn)")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-download", action="store_true",
                    help="Tải lại .pbf kể cả khi đã có")
    args = ap.parse_args()
    run(force_download=args.force_download)
