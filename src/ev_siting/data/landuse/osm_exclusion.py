#!/usr/bin/env python3
"""osm_exclusion.py — Vùng cấm + trạm biến áp từ OSM (bổ sung cho WorldCover).

WorldCover bắt được nước/núi/rừng nhưng **không** biết ranh giới pháp lý (quân sự,
khu bảo tồn, sân bay). Lấy các polygon đó từ Overpass rồi rasterize sang ô H3:
một ô bị loại cứng nếu **tâm ô** rơi trong bất kỳ vùng cấm nào.

Đồng thời lấy `power=substation` làm proxy ràng buộc lưới điện (phạt mềm — ô càng
xa trạm biến áp thì chi phí đấu nối DC nhanh càng cao; problem-analysis Nhóm 2 #3).

Quy mô:
  - **city:** 1 query bbox nhỏ là đủ.
  - **national:** bbox VN quá lớn cho 1 query → **quadtree** như overpass_poi; và test
    tâm-ô-trong-vùng-cấm cho 268k ô dùng **STRtree** (bulk, không lặp Python O(cell×poly)).

Output:
  - data/interim/landuse/exclusion_zones.parquet : h3_r8, excl_flags (list)
  - data/interim/landuse/osm_substations.parquet : lat, lng (điểm trạm biến áp)

Chạy:
    PYTHONPATH=src python -m ev_siting.data.landuse.osm_exclusion --city hanoi
    PYTHONPATH=src python -m ev_siting.data.landuse.osm_exclusion --national
"""
import argparse
import json
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd
import requests
from shapely import STRtree
from shapely.geometry import Point, Polygon

import h3

from ev_siting.aoi import NationalAOI, add_aoi_args, aoi_from_args
from .paths import (EXCLUSION_ZONES, OSM_EXCL_DIR, OSM_SUBSTATION_TAGS,
                    SUBSTATIONS, ensure_dirs)

ENDPOINT = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "vgreen-charging-siting/0.1 (land-use exclusion; contact: giangnt306w@gmail.com)"}
OVERPASS_TIMEOUT = 180
HTTP_TIMEOUT = 300
SPLIT_CAP = 20000      # >= ngần này phần tử -> nghi bị cắt -> chia 4
MIN_TILE_DEG = 0.1     # không tách nhỏ hơn cạnh này
PAUSE_S = 1.0

# selector vùng cấm -> nhãn cờ (way + relation cho mỗi loại polygon)
_EXCL_SELECTORS = [
    ('["landuse"="military"]', "MILITARY"),
    ('["boundary"="protected_area"]', "PROTECTED"),
    ('["leisure"="nature_reserve"]', "PROTECTED"),
    ('["aeroway"="aerodrome"]', "AIRPORT"),
    ('["natural"="water"]', "WATER_OSM"),
    ('["landuse"="reservoir"]', "WATER_OSM"),
]


def _post(query, tries=4):
    for attempt in range(tries):
        try:
            r = requests.post(ENDPOINT, data={"data": query}, headers=HEADERS,
                              timeout=HTTP_TIMEOUT)
        except requests.RequestException as e:
            wait = 5 * (attempt + 1)
            print(f"  ! network {type(e).__name__}; chờ {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 502, 503, 504):
            wait = 10 * (attempt + 1)
            print(f"  ! HTTP {r.status_code}; chờ {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(f"Overpass HTTP {r.status_code}: {r.text[:200]}")
    raise RuntimeError("Overpass thất bại sau nhiều lần thử")


def _quadrants(bbox):
    s, w, n, e = bbox
    mlat, mlon = (s + n) / 2, (w + e) / 2
    return [(s, w, mlat, mlon), (s, mlon, mlat, e),
            (mlat, w, n, mlon), (mlat, mlon, n, e)]


def _fetch_quadtree(body_selectors, out_clause, bbox, depth=0):
    """Đệ quy quadtree: gộp phần tử từ mọi ô con. `body_selectors` là list câu
    `nwr[...]` (không có bbox); `out_clause` ví dụ 'out geom tags;'."""
    s, w, n, e = bbox
    body = "".join(f"  {sel}({s},{w},{n},{e});\n" for sel in body_selectors)
    query = f"[out:json][timeout:{OVERPASS_TIMEOUT}];\n(\n{body});\n{out_clause}"
    try:
        els = _post(query).get("elements", [])
    except RuntimeError as e:
        els = None
        print(f"{'  '*(depth+1)}! {e} -> thử tách", file=sys.stderr)
    too_big = els is None or len(els) >= SPLIT_CAP
    can_split = (n - s) / 2 >= MIN_TILE_DEG
    if too_big and can_split:
        acc = {}
        for q in _quadrants(bbox):
            acc.update(_fetch_quadtree(body_selectors, out_clause, q, depth + 1))
        return acc
    if els is None:
        print(f"{'  '*(depth+1)}!! bỏ ô {tuple(round(x,2) for x in bbox)}", file=sys.stderr)
        return {}
    time.sleep(PAUSE_S)
    return {(el["type"], el["id"]): el for el in els}


def _load_or_fetch(cache_name, selectors, out_clause, bbox, refetch=False):
    """Đọc phần tử Overpass từ snapshot ĐÃ FREEZE, chỉ crawl lại khi được yêu cầu.

    E-DQ10: `data/raw/` là **bất biến** (freeze khoá read-only) và mọi bước phía sau là
    **dẫn xuất** trên nó. Bản trước luôn crawl lại rồi ghi đè chính file thô — vừa phá
    snapshot vừa làm bước này không tái lập được (Overpass trả khác nhau theo thời
    điểm). Nay: có cache thì DÙNG cache; muốn nguồn mới thì `--refetch` **và** phải
    `make freeze` lại một cách tường minh.
    """
    path = OSM_EXCL_DIR / cache_name
    if path.exists() and not refetch:
        els = json.loads(path.read_text(encoding="utf-8"))
        print(f"[excl] dùng snapshot đã freeze {cache_name} ({len(els)} phần tử) "
              f"— không crawl lại (E-DQ10)")
        return {(el.get("type"), el.get("id")): el for el in els}
    els = _fetch_quadtree(selectors, out_clause, bbox)
    path.write_text(json.dumps(list(els.values()), ensure_ascii=False), encoding="utf-8")
    return els


def _poly_of(el):
    """Polygon shapely từ 1 phần tử Overpass `out geom` (way/relation), hoặc None."""
    if el.get("type") == "way" and el.get("geometry"):
        pts = [(p["lon"], p["lat"]) for p in el["geometry"]]
        if len(pts) >= 4:
            return Polygon(pts)
    if el.get("type") == "relation" and el.get("members"):
        outers = []
        for m in el["members"]:
            if m.get("role") == "outer" and m.get("geometry"):
                pts = [(p["lon"], p["lat"]) for p in m["geometry"]]
                if len(pts) >= 4:
                    outers.append(Polygon(pts))
        if outers:
            return max(outers, key=lambda p: p.area)
    return None


def _flag_of(tags):
    if tags.get("landuse") == "military":
        return "MILITARY"
    if tags.get("boundary") == "protected_area" or tags.get("leisure") == "nature_reserve":
        return "PROTECTED"
    if tags.get("aeroway") == "aerodrome":
        return "AIRPORT"
    if tags.get("natural") == "water" or tags.get("landuse") == "reservoir":
        return "WATER_OSM"
    return None


def build_exclusion(aoi, skip_water=False, refetch=False):
    """Lấy polygon cấm -> đánh cờ ô H3 có tâm rơi trong vùng cấm (STRtree bulk).

    `skip_water=True` (national): bỏ `natural=water`/`reservoir` — WorldCover đã phủ
    mặt nước rất tốt (`frac_water`), còn kéo mọi polygon nước toàn VN thì Overpass
    cực nặng/chậm. Vẫn giữ ranh giới pháp lý (military/protected/airport) vì raster
    không có.
    """
    selectors = []
    for sel, flag in _EXCL_SELECTORS:
        if skip_water and flag == "WATER_OSM":
            continue
        selectors += [f"way{sel}", f"relation{sel}"]
    els = _load_or_fetch("exclusion.json", selectors, "out geom tags;", aoi.bbox(),
                         refetch=refetch)
    print(f"[excl] {len(els)} phần tử vùng cấm")

    polys, flags = [], []
    for el in els.values():
        poly = _poly_of(el)
        if poly is None:
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly is None or poly.is_empty:
            continue
        flag = _flag_of(el.get("tags", {}))
        if flag:
            polys.append(poly)
            flags.append(flag)

    cells = aoi.cells()
    cell_flags: dict[str, set] = {}
    if polys:
        flags = np.array(flags)
        tree = STRtree(polys)
        latlng = np.array([h3.cell_to_latlng(c) for c in cells])
        points = np.array([Point(lo, la) for la, lo in latlng], dtype=object)
        # bulk: cặp (chỉ số điểm, chỉ số polygon). Lưu ý shapely áp predicate theo
        # chiều input.predicate(tree) -> dùng "within" (point.within(poly)), KHÔNG
        # phải "contains" (point.contains(poly) luôn False).
        pt_idx, poly_idx = tree.query(points, predicate="within")
        for pi, gi in zip(pt_idx, poly_idx):
            cell_flags.setdefault(cells[pi], set()).add(str(flags[gi]))

    rows = [{"h3_r8": c, "excl_flags": sorted(fl)} for c, fl in cell_flags.items()]
    df = pd.DataFrame(rows, columns=["h3_r8", "excl_flags"])
    df.to_parquet(EXCLUSION_ZONES, index=False)
    print(f"[excl] -> {EXCLUSION_ZONES}  ({len(df)} ô bị cấm)")
    if len(df):
        print("  theo cờ:", dict(Counter(f for fl in df.excl_flags for f in fl)))
    return df


def build_substations(aoi, refetch=False):
    """Lấy điểm power=substation (proxy đấu nối lưới) trong AOI."""
    els = _load_or_fetch("substations.json", list(OSM_SUBSTATION_TAGS),
                         "out center tags;", aoi.bbox(), refetch=refetch)
    rows = []
    for el in els.values():
        if el.get("type") == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            lat, lng = c.get("lat"), c.get("lon")
        if lat is None or lng is None:
            continue
        if bool(np.asarray(aoi.contains(lat, lng))):
            rows.append({"lat": lat, "lng": lng})
    df = pd.DataFrame(rows, columns=["lat", "lng"]).drop_duplicates().reset_index(drop=True)
    df.to_parquet(SUBSTATIONS, index=False)
    print(f"[subs] -> {SUBSTATIONS}  ({len(df)} trạm biến áp)")
    return df


def run(args=None):
    ap = argparse.ArgumentParser(description="OSM vùng cấm + trạm biến áp theo AOI")
    add_aoi_args(ap)
    ap.add_argument("--refetch", action="store_true",
                    help="crawl lại Overpass và GHI ĐÈ snapshot thô (phá E-DQ10 — "
                         "phải `make freeze` lại sau đó)")
    a = ap.parse_args(args)
    aoi = aoi_from_args(a)
    ensure_dirs()
    national = isinstance(aoi, NationalAOI)
    print(f"[osm-excl] {aoi}  (national={national})")
    build_exclusion(aoi, skip_water=national, refetch=a.refetch)
    build_substations(aoi, refetch=a.refetch)


if __name__ == "__main__":
    run()
