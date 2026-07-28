#!/usr/bin/env python3
"""roads_pbf.py — Mạng lưới đường (trắc địa) VN từ Geofabrik .pbf -> km theo LỚP × ô H3.

Vì cả nước có hàng triệu `way` đường -> Overpass không kham nổi. Ta tải dump
`vietnam-latest.osm.pbf` (Geofabrik) rồi **stream** bằng osmium (C++), gom trực
tiếp chiều dài đường về ô H3 res 8 — không giữ toàn bộ segment trong RAM.

Với mỗi `way` có tag `highway` (loại lái xe được):
  - Tính chiều dài từng đoạn giữa 2 node (haversine).
  - Lấy mẫu dọc polyline mỗi ~SAMPLE_M mét, cộng chiều dài đoạn con vào ô H3
    của điểm giữa -> phân bổ chiều dài theo ô khá sát ở res 8 (cạnh 0,56 km; 0,46 km
    ghi ở bản trước là bán kính nội tiếp, không phải cạnh — xem P4).

**E-DQ7b/R1 — bảng ra là bảng LỚP, không phải bảng chính sách.** Bản trước ghi đúng 2
số (`road_len_m`, `road_len_mt_m`) với `_EXCLUDE`/`_MAJOR` hard-code ngay trong vòng
lặp: đổi định nghĩa "đường" = stream lại 325 MB (~7 phút) và không hoàn tác được. Nay
mỗi ô giữ **km + lane-mét + lane-mét-có-tag của TỪNG LỚP** (`road_semantics.TIERS`)
cộng km cầu/hầm; mọi cột vô hướng do `road_semantics.derive()` suy ra ở bước sau.

Output — `osm_roads_h3.parquet`, 1 dòng/ô H3 res 8:
  h3_r8
  m_<TIER>          : chiều dài tim đường (m) của lớp trong ô
  lane_m_<TIER>     : lane-mét (chiều dài × số làn) — sửa double-count đường đôi (R3)
  lane_obs_m_<TIER> : phần lane-mét đến từ way CÓ tag `lanes` (đo cổng QA)
  bridge_m          : chiều dài cầu/hầm (TẬP CON của Σ m_<TIER>)

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
from .road_semantics import (BRIDGE_COL, NON_DRIVABLE, TIER_COLUMNS, TIER_OF,
                             TIERS, derive, is_oneway, lane_col, lane_obs_col,
                             lanes_for, m_col)
import h3

SAMPLE_M = 150.0          # bước lấy mẫu dọc đường (m)
_EARTH_R = 6_371_000.0    # bán kính Trái Đất (m)

# layout accumulator = ĐÚNG thứ tự `TIER_COLUMNS` (3 ô nhớ/lớp: m, lane_m, lane_obs_m;
# rồi cầu/hầm). Chỉ số tra thẳng từ tên cột nên không thể lệch nhãn khi ghi ra frame.
_TIER_IDX = {t: TIER_COLUMNS.index(m_col(t)) for t in TIERS}
_BRIDGE_SLOT = TIER_COLUMNS.index(BRIDGE_COL)
_N_SLOTS = len(TIER_COLUMNS)


def _haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_R * math.asin(math.sqrt(a))


class RoadHandler(osmium.SimpleHandler):
    """Gom km/lane-mét theo (lớp, ô H3) khi stream .pbf (không giữ segment)."""

    def __init__(self):
        super().__init__()
        self.cells = {}          # h3_r8 -> list[_N_SLOTS] float
        self.n_ways = 0
        self.n_ways_kept = 0

    def way(self, w):
        hwy = w.tags.get("highway")
        if hwy is None:
            return
        self.n_ways += 1
        if hwy in NON_DRIVABLE:
            return
        pts = [(n.location.lat, n.location.lon) for n in w.nodes if n.location.valid()]
        if len(pts) < 2:
            return
        self.n_ways_kept += 1

        tier = TIER_OF.get(hwy, "OTHER")
        base = _TIER_IDX[tier]
        oneway = is_oneway(w.tags.get("oneway"))
        lanes, lanes_tagged = lanes_for(tier, w.tags.get("lanes"), oneway)
        # cầu/hầm: không xây được trạm trên mặt cầu, nhưng vẫn là "có đường" hôm nay
        is_span = bool(w.tags.get("bridge") or w.tags.get("tunnel"))

        for (la1, lo1), (la2, lo2) in zip(pts, pts[1:]):
            seg = _haversine(la1, lo1, la2, lo2)
            if seg == 0:
                continue
            n = max(1, int(seg // SAMPLE_M))    # số đoạn con
            sub = seg / n
            for k in range(n):
                # điểm giữa đoạn con thứ k
                t = (k + 0.5) / n
                mlat = la1 + (la2 - la1) * t
                mlon = lo1 + (lo2 - lo1) * t
                cell = h3.latlng_to_cell(mlat, mlon, H3_RES_R8)
                acc = self.cells.get(cell)
                if acc is None:
                    acc = [0.0] * _N_SLOTS
                    self.cells[cell] = acc
                acc[base] += sub
                acc[base + 1] += sub * lanes
                if lanes_tagged:
                    acc[base + 2] += sub * lanes
                if is_span:
                    acc[_BRIDGE_SLOT] += sub

    def to_frame(self):
        return pd.DataFrame(
            [[c] + v for c, v in self.cells.items()],
            columns=["h3_r8"] + TIER_COLUMNS,
        )


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

    df = h.to_frame()
    # bất biến bắt LỆCH NHÃN CỘT (chế độ lỗi im lặng khi accumulator và TIER_COLUMNS
    # không cùng thứ tự): mọi way có >=1 làn ⇒ lane_m >= m; lane quan sát ⊆ lane.
    bad = [t for t in TIERS
           if bool((df[lane_col(t)] + 1e-6 < df[m_col(t)]).any())
           or bool((df[lane_obs_col(t)] > df[lane_col(t)] + 1e-6).any())]
    if bad:
        raise SystemExit(f"[roads] bất biến lane-mét gãy ở lớp {bad} — cột bị lệch nhãn")

    df = derive(df).sort_values("road_access_m", ascending=False).reset_index(drop=True)
    df[["h3_r8"] + TIER_COLUMNS].to_parquet(ROADS_H3, index=False)

    print(f"[roads] -> {ROADS_H3}  ({len(df)} ô)")
    print("[roads] km theo lớp (E-DQ7b):")
    total_km = df["road_access_m"].sum() / 1e3
    for t in TIERS:
        km = df[f"m_{t}"].sum() / 1e3
        lane_km = df[f"lane_m_{t}"].sum() / 1e3
        obs = df[f"lane_obs_m_{t}"].sum() / max(df[f"lane_m_{t}"].sum(), 1e-9)
        print(f"    {t:10s} {km:10,.0f} km ({km/max(total_km,1e-9):5.1%})  "
              f"lane {lane_km:10,.0f} km  (lanes có tag {obs:5.1%})")
    print(f"[roads] road_access_m {total_km:,.0f} km · "
          f"road_len_m {df.road_len_m.sum()/1e3:,.0f} km · "
          f"lane cao tốc {df.road_lane_mw_m.sum()/1e3:,.0f} km · "
          f"lane trục đô thị {df.road_lane_ar_m.sum()/1e3:,.0f} km · "
          f"cầu/hầm {df.road_bridge_m.sum()/1e3:,.0f} km")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-download", action="store_true",
                    help="Tải lại .pbf kể cả khi đã có")
    args = ap.parse_args()
    run(force_download=args.force_download)
